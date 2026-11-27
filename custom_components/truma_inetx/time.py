"""Time platform: the start and end of each heating timer."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import TrumaConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrumaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the heating timers' start and end times."""
    timers = getattr(entry.runtime_data, "heating_timers", None)
    if timers is not None:
        async_add_entities(timers.entities(Platform.TIME))
