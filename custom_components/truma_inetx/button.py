"""Button platform: the one bus parameter that is an action, not a state."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import TrumaConfigEntry
from .entity import TrumaParamEntity, async_add_rows

# Entities are coordinator-driven and have no update() method, so Home
# Assistant would create no semaphore anyway; stated explicitly.
PARALLEL_UPDATES = 0

# The topic the reset belongs to, and the parameter within it that says what
# the appliance is currently raising. Named here rather than reached for
# through the row, because the button's whole behaviour is about the *other*
# parameter in its own topic.
_ERROR_PARAM = "ErrCode"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrumaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Truma buttons, on the devices that publish them."""
    coordinator = entry.runtime_data
    async_add_rows(
        coordinator,
        async_add_entities,
        Platform.BUTTON,
        lambda addr, topic, param, row: TrumaResetButton(
            coordinator, addr, topic, param, row
        ),
    )


class TrumaResetButton(TrumaParamEntity, ButtonEntity):
    """Clear a fault the appliance says can be cleared.

    Pressing writes ``ErrorReset.Req`` to the device raising the fault, which
    is what the panel's own reset does. It is not a bus-wide action: a fault
    belongs to the appliance that raised it, and on the van the heater held
    one while the panel's own list stayed empty.

    Available only while that appliance is raising something it calls
    resettable *and* describes the reset parameter as writable. Both are
    gates on the device's own word, not on a guess, and an appliance can
    fail either one.

    Each entry in ``ErrCode`` carries its own ``resettable`` flag, and
    measured on the van a window opened above the heater gives::

        [{"sev": 1, "code": 412, "resettable": 0}]

    which is a fault to go and fix rather than to acknowledge.

    The second gate is there because a Combi 6 E said both things at once
    (#36). It raised a fault it called clearable and described the parameter
    that clears it as read-only::

        ErrCode         [{"sev": 2, "code": 517, "resettable": 1}]
        ErrorReset.Req  {"type": 104, "perm": 0, "avail": 1}

    so the button appeared, and the press was refused by the write
    validation quoting the panel's own ``perm`` -- correctly, and only after
    the user had pressed it. The appliance contradicts itself; the button
    believes the stricter half.

    Offering a button that the appliance has said will not work is worse
    than not offering one: it is a control that silently does nothing.
    """

    @property
    def available(self) -> bool:
        """Whether this appliance has a fault it says it can clear."""
        if not super().available:
            return False
        # Asked of the device that would receive the press, and by the same
        # question the write validation asks, so the button cannot be offered
        # for a write that is already known to be refused. Only an explicit
        # ``perm: 0`` withholds it: a parameter the device never described
        # reads ``None`` here and keeps its button, because withholding a
        # control on silence is the failure this repo has paid for twice.
        dest = self.bus.write_authority(self._addr, self._topic, self._param)
        if dest is not None and dest.writable(self._topic, self._param) is False:
            return False
        errors = self.device.get(self._topic, _ERROR_PARAM)
        if not isinstance(errors, list):
            return False
        return any(
            isinstance(entry, dict) and entry.get("resettable")
            for entry in errors
        )

    async def async_press(self) -> None:
        """Ask the appliance to clear its fault."""
        await self.async_write(self._param, 1)
