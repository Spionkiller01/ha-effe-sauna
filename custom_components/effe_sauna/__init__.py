"""Effe ECC (My Effe cloud) integration."""
from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import EffeConfigEntry, EffeCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: EffeConfigEntry) -> bool:
    """Set up one My Effe account."""
    coordinator = EffeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start_push()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EffeConfigEntry) -> bool:
    """Unload; the push task is a config-entry background task and stops itself."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
