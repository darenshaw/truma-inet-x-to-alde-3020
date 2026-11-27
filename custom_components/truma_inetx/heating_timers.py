"""Timers run by Home Assistant, one device per timer, for heating or hot water.

The panel's own timers cannot be set from here: it describes each
``TimerConfig.TimerN`` structure as read-only (``perm`` 0), and the structure
holds a start, an end and weekdays but no temperature -- its ``name`` ("20 °C")
is a label. So these are Home Assistant's own timers. All six live on one
"iNet X Timers" device that hangs off the panel -- one device rather than six,
so the device list stays short -- and each has its own Enabled switch, Start
and End times, Temperature, Days and Controls ("Timer 3 Start", ...).
A timer controls the room heating (the climate entity, set to its
temperature), the hot water (the appliance's hot water switch, on while it
runs), or both.

Settings are kept by Home Assistant's restore-state machinery, so they survive
restarts without a store of their own. The timers act only when the running
timer changes -- at a start, at an end, or when an edit changes which timer
is running or its temperature -- so a manual change to the heating in the
middle of a timer stands until the next change. A command that fails (the
panel out of reach, say) is retried every minute until it lands.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, time
from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.time import TimeEntity
from homeassistant.const import Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER
from .timer_logic import (
    CONTROLS_OPTIONS,
    DAYS_OPTIONS,
    TARGET_HEATING,
    TARGET_HOT_WATER,
    MAX_TEMP,
    MIN_TEMP,
    TIMER_SLOTS,
    TimerSettings,
    active_timer,
)


class HeatingTimers:
    """The six timers' settings and the clock that acts on them."""

    def __init__(self, hass: HomeAssistant, entry_id: str, coordinator: Any) -> None:
        """Hold settings for every slot; nothing runs until ``async_start``."""
        self.hass = hass
        self._entry_id = entry_id
        self._coordinator = coordinator
        self.timers: dict[int, TimerSettings] = {
            slot: TimerSettings() for slot in TIMER_SLOTS
        }
        # What was last applied to each target: (slot, temperature) or None.
        self._applied: dict[str, tuple[int, float] | None] = {
            TARGET_HEATING: None,
            TARGET_HOT_WATER: None,
        }
        self._failing: set[str] = set()
        self._lock = asyncio.Lock()
        self._unsub = None
        self.parent_device_id: str | None = None

    @property
    def parent_identifier(self) -> tuple[str, str]:
        """The "iNet X Timers" device every timer hangs off."""
        return (DOMAIN, f"{self._coordinator.unique_id}_timers")

    def parent_device_info(self) -> DeviceInfo:
        """The device that bundles the timers, under the panel."""
        info = DeviceInfo(
            identifiers={self.parent_identifier},
            name="iNet X Timers",
            manufacturer="Home Assistant",
            model="Timers",
        )
        _hang_off(info, getattr(self._coordinator, "hub_device_id", None),
                  (DOMAIN, self._coordinator.unique_id))
        return info

    def legacy_device_identifiers(self) -> list[tuple[str, str]]:
        """The per-timer devices of 0.9.0b25+alde3020.8, removed at setup."""
        uid = self._coordinator.unique_id
        return [(DOMAIN, f"{uid}_heating_timer_{slot}") for slot in TIMER_SLOTS]

    def entities(self, platform: Platform) -> list[Entity]:
        """The timer entities a platform should add."""
        build = {
            Platform.SWITCH: lambda s: [TimerEnabledSwitch(self, s)],
            Platform.TIME: lambda s: [
                TimerTime(self, s, "start"),
                TimerTime(self, s, "end"),
            ],
            Platform.NUMBER: lambda s: [TimerTemperature(self, s)],
            Platform.SELECT: lambda s: [TimerDays(self, s), TimerControls(self, s)],
        }.get(platform)
        if build is None:
            return []
        return [entity for slot in TIMER_SLOTS for entity in build(slot)]

    @callback
    def async_start(self) -> None:
        """Check the timers at the top of every minute."""
        self._unsub = async_track_time_change(self.hass, self._async_tick, second=0)

    @callback
    def async_stop(self) -> None:
        """Stop the clock."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    async def _async_tick(self, _now: datetime) -> None:
        await self.async_evaluate()

    @callback
    def async_settings_changed(self) -> None:
        """Re-check straight away after an edit."""
        if self._unsub is not None:
            self.hass.async_create_task(self.async_evaluate())

    def _entity_id(self, target: str) -> str | None:
        """This integration's entity that a target is driven through.

        Heating is the climate entity that can heat; hot water is the
        appliance's WaterHeating.Active switch. Looked up each time, so an
        appliance that appears later is picked up without a reload.
        """
        registry = er.async_get(self.hass)
        for item in er.async_entries_for_config_entry(registry, self._entry_id):
            if item.disabled:
                continue
            if target == TARGET_HOT_WATER:
                if item.domain == "switch" and item.unique_id.endswith(
                    "_WaterHeating.Active_switch"
                ):
                    return item.entity_id
                continue
            if item.domain != "climate":
                continue
            state = self.hass.states.get(item.entity_id)
            modes = state.attributes.get("hvac_modes", []) if state else []
            if HVACMode.HEAT in modes:
                return item.entity_id
        return None

    async def async_evaluate(self) -> None:
        """Apply whatever timer is running, for each target, if it changed."""
        async with self._lock:
            now = dt_util.now()
            await self._async_apply(
                TARGET_HEATING, active_timer(self.timers, now, TARGET_HEATING)
            )
            # Hot water is on or off; a temperature on a hot water timer
            # means nothing, so editing it must not send the switch again.
            water = active_timer(self.timers, now, TARGET_HOT_WATER)
            await self._async_apply(
                TARGET_HOT_WATER, None if water is None else (water[0], 0.0)
            )

    async def _async_apply(
        self, target: str, running: tuple[int, float] | None
    ) -> None:
        """Send one target its command, remembering it only once it lands."""
        if running == self._applied[target]:
            return
        entity_id = self._entity_id(target)
        if entity_id is None:
            return
        if target == TARGET_HEATING:
            if running is not None:
                call = ("climate", "set_temperature", {
                    "hvac_mode": HVACMode.HEAT, "temperature": running[1]})
            else:
                call = ("climate", "set_hvac_mode", {"hvac_mode": HVACMode.OFF})
        else:
            call = ("switch", "turn_on" if running is not None else "turn_off", {})
        try:
            await self.hass.services.async_call(
                call[0], call[1], {"entity_id": entity_id, **call[2]}, blocking=True
            )
        except HomeAssistantError as err:
            if target not in self._failing:
                LOGGER.warning(
                    "Timers could not set %s (will retry each minute): %s",
                    entity_id,
                    err,
                )
            self._failing.add(target)
            return
        LOGGER.info(
            "Timers: %s %s (timer %s)",
            entity_id,
            call[1] if running is None or target != TARGET_HEATING
            else f"heat to {running[1]} °C",
            running[0] if running else "none",
        )
        self._failing.discard(target)
        self._applied[target] = running


def _hang_off(info: DeviceInfo, parent_id: str | None, parent: tuple[str, str]) -> None:
    """Hang a device off its parent, by whichever key this Home Assistant takes."""
    if parent_id is not None and "via_device_id" in DeviceInfo.__annotations__:
        info["via_device_id"] = parent_id
    else:
        info["via_device"] = parent


class _TimerEntity(RestoreEntity):
    """One setting of one timer, on that timer's device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, timers: HeatingTimers, slot: int, key: str) -> None:
        self._timers = timers
        self._slot = slot
        uid = timers._coordinator.unique_id
        self._attr_unique_id = f"{uid}_heating_timer_{slot}_{key}"
        self._attr_translation_key = f"heating_timer_{key}"
        self._attr_translation_placeholders = {"slot": str(slot)}
        self._attr_device_info = timers.parent_device_info()

    @property
    def settings(self) -> TimerSettings:
        return self._timers.timers[self._slot]

    async def async_added_to_hass(self) -> None:
        """Take back the setting this entity had before the restart."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state not in ("unknown", "unavailable"):
            try:
                self._restore(last.state)
            except (TypeError, ValueError):
                LOGGER.debug("%s: could not restore %r", self.entity_id, last.state)

    def _restore(self, state: str) -> None:
        raise NotImplementedError

    def _changed(self) -> None:
        self.async_write_ha_state()
        self._timers.async_settings_changed()


class TimerEnabledSwitch(_TimerEntity, SwitchEntity):
    """Whether the timer runs."""

    def __init__(self, timers: HeatingTimers, slot: int) -> None:
        super().__init__(timers, slot, "enabled")

    def _restore(self, state: str) -> None:
        self.settings.enabled = state == "on"

    @property
    def is_on(self) -> bool:
        return self.settings.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.settings.enabled = True
        self._changed()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.settings.enabled = False
        self._changed()


class TimerTime(_TimerEntity, TimeEntity):
    """When the timer starts, or ends."""

    def __init__(self, timers: HeatingTimers, slot: int, which: str) -> None:
        super().__init__(timers, slot, which)
        self._which = which

    def _restore(self, state: str) -> None:
        setattr(self.settings, self._which, time.fromisoformat(state))

    @property
    def native_value(self) -> time:
        return getattr(self.settings, self._which)

    async def async_set_value(self, value: time) -> None:
        setattr(self.settings, self._which, value.replace(second=0, microsecond=0))
        self._changed()


class TimerTemperature(_TimerEntity, NumberEntity):
    """What the heating is set to while the timer runs."""

    _attr_native_min_value = MIN_TEMP
    _attr_native_max_value = MAX_TEMP
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX

    def __init__(self, timers: HeatingTimers, slot: int) -> None:
        super().__init__(timers, slot, "temperature")

    def _restore(self, state: str) -> None:
        self.settings.temperature = min(MAX_TEMP, max(MIN_TEMP, float(state)))

    @property
    def native_value(self) -> float:
        return self.settings.temperature

    async def async_set_native_value(self, value: float) -> None:
        self.settings.temperature = float(value)
        self._changed()


class TimerDays(_TimerEntity, SelectEntity):
    """Which days the timer starts on."""

    _attr_options = DAYS_OPTIONS

    def __init__(self, timers: HeatingTimers, slot: int) -> None:
        super().__init__(timers, slot, "days")

    def _restore(self, state: str) -> None:
        if state in DAYS_OPTIONS:
            self.settings.days = state

    @property
    def current_option(self) -> str:
        return self.settings.days

    async def async_select_option(self, option: str) -> None:
        self.settings.days = option
        self._changed()


class TimerControls(_TimerEntity, SelectEntity):
    """Whether the timer runs the heating, the hot water, or both."""

    _attr_options = CONTROLS_OPTIONS

    def __init__(self, timers: HeatingTimers, slot: int) -> None:
        super().__init__(timers, slot, "controls")

    def _restore(self, state: str) -> None:
        if state in CONTROLS_OPTIONS:
            self.settings.controls = state

    @property
    def current_option(self) -> str:
        return self.settings.controls

    async def async_select_option(self, option: str) -> None:
        self.settings.controls = option
        self._changed()
