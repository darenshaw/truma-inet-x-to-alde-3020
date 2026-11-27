"""Which heating timer is running at a given moment.

Kept apart from ``heating_timers`` and free of Home Assistant imports so the
rules can be tested on a bare interpreter, the way every other test here runs.

The rules, in full:

* A timer runs from its start time up to, but not including, its end time.
  An end earlier than the start runs past midnight (21:00 to 09:00 ends at
  09:00 the next morning). A start equal to the end never runs.
* Its days are the days it *starts* on, so a weekend timer from 22:00 to
  06:00 still runs at 03:00 on Monday morning, having started on Sunday.
* Where timers overlap, the one that started most recently wins, so a short
  boost inside a long timer takes over for its duration and hands back when
  it ends.
* Each timer controls the room heating, the hot water, or both, and the two
  are worked out separately: a hot water timer never ends a heating one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, time

TIMER_SLOTS = range(1, 7)

DAYS_EVERY_DAY = "every_day"
DAYS_WEEKDAYS = "weekdays"
DAYS_WEEKENDS = "weekends"
DAYS_OPTIONS = [DAYS_EVERY_DAY, DAYS_WEEKDAYS, DAYS_WEEKENDS]

CONTROLS_HEATING = "heating"
CONTROLS_HOT_WATER = "hot_water"
CONTROLS_BOTH = "heating_and_hot_water"
CONTROLS_OPTIONS = [CONTROLS_HEATING, CONTROLS_HOT_WATER, CONTROLS_BOTH]

# What each controlled thing is, and which timer settings reach it.
TARGET_HEATING = "heating"
TARGET_HOT_WATER = "hot_water"
_CONTROLS_FOR = {
    TARGET_HEATING: {CONTROLS_HEATING, CONTROLS_BOTH},
    TARGET_HOT_WATER: {CONTROLS_HOT_WATER, CONTROLS_BOTH},
}

MIN_TEMP = 5.0
MAX_TEMP = 30.0
DEFAULT_TEMP = 20.0


@dataclass
class TimerSettings:
    """What one timer is set to."""

    enabled: bool = False
    start: time = field(default_factory=lambda: time(0, 0))
    end: time = field(default_factory=lambda: time(0, 0))
    temperature: float = DEFAULT_TEMP
    days: str = DAYS_EVERY_DAY
    controls: str = CONTROLS_HEATING


def runs_on(days: str, weekday: int) -> bool:
    """Whether a timer with these days starts on ``weekday`` (Monday is 0)."""
    if days == DAYS_WEEKDAYS:
        return weekday < 5
    if days == DAYS_WEEKENDS:
        return weekday >= 5
    return True


def active_timer(
    timers: Mapping[int, TimerSettings],
    now: datetime,
    target: str = TARGET_HEATING,
) -> tuple[int, float] | None:
    """The slot running ``target`` at ``now`` and its temperature, or None."""
    controls = _CONTROLS_FOR[target]
    mins = now.hour * 60 + now.minute
    weekday = now.weekday()
    best: tuple[int, float] | None = None
    best_age: int | None = None
    for slot, timer in sorted(timers.items()):
        if not timer.enabled or timer.controls not in controls:
            continue
        start = timer.start.hour * 60 + timer.start.minute
        end = timer.end.hour * 60 + timer.end.minute
        if start == end:
            continue
        if start < end:
            running = start <= mins < end
            started_on = weekday
        else:
            running = mins >= start or mins < end
            started_on = weekday if mins >= start else (weekday - 1) % 7
        if not running or not runs_on(timer.days, started_on):
            continue
        age = (mins - start) % 1440
        if best_age is None or age < best_age:
            best = (slot, float(timer.temperature))
            best_age = age
    return best
