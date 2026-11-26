#!/usr/bin/env python3
"""Offline checks for the "Only create entities for detected hardware" option.

What it pins:

1. on (the default), a row nothing publishes gets no entity at all,
2. off, every row nothing publishes gets one, on the placeholder device,
   never available, and only once discovery is over,
3. off, a row the bus does publish is built once, on its real device,
4. off, hardware that turns up later gets its real entity and the
   placeholder is removed from the entity registry,
5. off, timer slots the panel marks unavailable are built anyway.

Run: ``python3 tests/test_show_all_entities.py``
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stubs  # noqa: E402

PANEL = 0x0101
HEATER = 0x0201

stubs.install_homeassistant()
BUS = stubs.load("bus")
CONST = stubs.load("const")
stubs.mod("truma_pkg.coordinator", TrumaCoordinator=object, TrumaConfigEntry=object)
PROFILES = stubs.load("profiles")
stubs.load("entity")
SENSOR = stubs.load("sensor")
SWITCH = stubs.load("switch")

NOT_DETECTED = CONST.DEV_NOT_DETECTED


class _Registry:
    """Entity registry double: every placeholder is registered, and removals are kept."""

    def __init__(self) -> None:
        self.removed: list[str] = []

    def async_get_entity_id(self, platform, domain, unique_id):
        return f"{platform}.{unique_id}"

    def async_remove(self, entity_id: str) -> None:
        self.removed.append(entity_id)


REGISTRY = _Registry()
sys.modules["homeassistant.helpers.entity_registry"].async_get = lambda _h: REGISTRY


def _coordinator(show_all: bool) -> stubs.FakeCoordinator:
    coordinator = stubs.FakeCoordinator(BUS.Bus())
    coordinator.detected_only = not show_all
    return coordinator


def _keys(entities, addr: int) -> set[str]:
    return {f"{e._topic}.{e._param}" for e in entities if e._addr == addr}


def test_default_builds_only_what_is_published() -> None:
    coordinator = _coordinator(show_all=False)
    sensors = stubs.setup_platform(SENSOR, coordinator)
    coordinator.report("AirHeating", "Temp", 215, HEATER)
    assert not _keys(sensors, NOT_DETECTED), "placeholders built with the option on"
    assert _keys(sensors, HEATER) == {"AirHeating.Temp"}


def test_off_builds_every_unpublished_row_as_a_placeholder() -> None:
    coordinator = _coordinator(show_all=True)
    # Published before the platform is set up, as it is in use: discovery is
    # over by then, or the bus was restored from the last session.
    coordinator.data.update("AirHeating", "Temp", 215, HEATER)
    sensors = stubs.setup_platform(SENSOR, coordinator)

    mapped = {
        f"{topic}.{param}"
        for (topic, param), rows in PROFILES.ROWS.items()
        if any(row.platform == "sensor" for row in rows)
    }
    placeholders = _keys(sensors, NOT_DETECTED)
    assert "FreshWater.Level" in placeholders
    assert "AirHeating.Temp" not in placeholders, "a published row was listed twice"
    assert placeholders | {"AirHeating.Temp"} >= mapped - {"AirHeating.Temp"}
    for entity in sensors:
        if entity._addr == NOT_DETECTED:
            assert entity.available is False


def test_off_waits_for_discovery() -> None:
    coordinator = _coordinator(show_all=True)
    coordinator.data.discovered = False
    sensors = stubs.setup_platform(SENSOR, coordinator)
    coordinator.report("Panel", "Intst", 80, PANEL)
    assert not _keys(sensors, NOT_DETECTED), "absence was assumed before discovery"


def test_hardware_that_turns_up_replaces_its_placeholder() -> None:
    REGISTRY.removed.clear()
    coordinator = _coordinator(show_all=True)
    sensors = stubs.setup_platform(SENSOR, coordinator)
    coordinator.report("AirHeating", "Temp", 215, HEATER)
    assert "FreshWater.Level" in _keys(sensors, NOT_DETECTED)

    coordinator.report("FreshWater", "Level", 50, 0x0402)
    assert "FreshWater.Level" in _keys(sensors, 0x0402)
    assert any("FFFE_FreshWater.Level_sensor" in e for e in REGISTRY.removed), (
        "the placeholder outlived the hardware it stood in for"
    )


def test_off_builds_empty_timer_slots() -> None:
    coordinator = _coordinator(show_all=True)
    switches = stubs.setup_platform(SWITCH, coordinator)
    for slot in range(1, 7):
        coordinator.describe(
            "TimerConfig", f"Timer{slot}State", PANEL, type=119,
            avail=1 if slot == 1 else 0, v=1 if slot == 1 else 0,
        )
    timers = sorted(e._param for e in switches if e._addr == PANEL)
    assert timers == [f"Timer{n}State" for n in range(1, 7)], timers


if __name__ == "__main__":
    stubs.run_tests(globals(), "show all mapped entities")
