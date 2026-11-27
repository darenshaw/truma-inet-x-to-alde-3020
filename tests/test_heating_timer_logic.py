#!/usr/bin/env python3
"""Offline checks for which heating timer is running.

Pins the rules in ``timer_logic``: a window runs from start up to its end, an
end before the start runs past midnight, a start equal to the end never runs,
days are the days a timer starts on, and the latest start wins an overlap.

Run: ``python3 tests/test_heating_timer_logic.py``
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, time
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "custom_components" / "truma_inetx"
_spec = importlib.util.spec_from_file_location("timer_logic", SRC / "timer_logic.py")
logic = importlib.util.module_from_spec(_spec)
sys.modules["timer_logic"] = logic
_spec.loader.exec_module(logic)

T = logic.TimerSettings
# 2026-11-23 is a Monday.
MON, SAT, SUN = 23, 28, 29


def at(day: int, hh: int, mm: int) -> datetime:
    return datetime(2026, 11, day, hh, mm)


def van() -> dict:
    """The van's two timers: 20 °C by day, 11 °C overnight."""
    return {
        1: T(True, time(9, 0), time(21, 0), 20.0),
        5: T(True, time(21, 0), time(9, 0), 11.0),
        2: T(),
    }


def test_day_and_night_hand_over() -> None:
    timers = van()
    assert logic.active_timer(timers, at(MON, 8, 59)) == (5, 11.0)
    assert logic.active_timer(timers, at(MON, 9, 0)) == (1, 20.0)
    assert logic.active_timer(timers, at(MON, 20, 59)) == (1, 20.0)
    assert logic.active_timer(timers, at(MON, 21, 0)) == (5, 11.0)
    assert logic.active_timer(timers, at(MON, 3, 0)) == (5, 11.0)


def test_end_is_exclusive_and_nothing_running_is_none() -> None:
    timers = {1: T(True, time(9, 0), time(10, 0), 20.0)}
    assert logic.active_timer(timers, at(MON, 10, 0)) is None
    assert logic.active_timer(timers, at(MON, 8, 0)) is None


def test_disabled_and_empty_timers_never_run() -> None:
    timers = {1: T(False, time(9, 0), time(21, 0), 20.0), 2: T(True)}
    assert logic.active_timer(timers, at(MON, 12, 0)) is None


def test_latest_start_wins_an_overlap() -> None:
    timers = van()
    timers[2] = T(True, time(17, 0), time(19, 0), 23.0)
    assert logic.active_timer(timers, at(MON, 16, 59)) == (1, 20.0)
    assert logic.active_timer(timers, at(MON, 18, 0)) == (2, 23.0)
    assert logic.active_timer(timers, at(MON, 19, 0)) == (1, 20.0)


def test_days_are_the_day_a_timer_starts() -> None:
    weekend_night = {1: T(True, time(22, 0), time(6, 0), 18.0, logic.DAYS_WEEKENDS)}
    # Started Sunday 22:00, still running Monday 03:00.
    assert logic.active_timer(weekend_night, at(MON, 3, 0)) == (1, 18.0)
    # Monday 22:00 is a weekday start.
    assert logic.active_timer(weekend_night, at(MON, 23, 0)) is None
    # Saturday 03:00 started on Friday night.
    assert logic.active_timer(weekend_night, at(SAT, 3, 0)) is None
    assert logic.active_timer(weekend_night, at(SAT, 23, 0)) == (1, 18.0)
    weekdays = {1: T(True, time(7, 0), time(9, 0), 21.0, logic.DAYS_WEEKDAYS)}
    assert logic.active_timer(weekdays, at(MON, 8, 0)) == (1, 21.0)
    assert logic.active_timer(weekdays, at(SUN, 8, 0)) is None


def test_heating_and_hot_water_are_worked_out_separately() -> None:
    timers = van()
    timers[2] = T(True, time(7, 0), time(8, 0), 20.0, controls=logic.CONTROLS_HOT_WATER)
    timers[3] = T(True, time(18, 0), time(19, 0), 22.0, controls=logic.CONTROLS_BOTH)
    heat, water = logic.TARGET_HEATING, logic.TARGET_HOT_WATER
    # A hot water timer does not interrupt the overnight heating.
    assert logic.active_timer(timers, at(MON, 7, 30), heat) == (5, 11.0)
    assert logic.active_timer(timers, at(MON, 7, 30), water) == (2, 20.0)
    assert logic.active_timer(timers, at(MON, 8, 0), water) is None
    # Heating-only timers never run the hot water.
    assert logic.active_timer(timers, at(MON, 12, 0), water) is None
    # "Both" runs each.
    assert logic.active_timer(timers, at(MON, 18, 30), heat) == (3, 22.0)
    assert logic.active_timer(timers, at(MON, 18, 30), water) == (3, 22.0)
    # The default target is heating, and the default timer controls heating.
    assert logic.TimerSettings().controls == logic.CONTROLS_HEATING
    assert logic.active_timer(timers, at(MON, 7, 30)) == (5, 11.0)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
