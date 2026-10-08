"""Diagnostics: current cloud state plus the last raw messages."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .coordinator import EffeConfigEntry

TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    "email",
    "users",
    "userId",
    "_id",
    "ssid",
    "bssid",
    "deviceToken",
    "mobileDevices",
    "Authorization",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EffeConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return async_redact_data(
        {
            "entry": dict(entry.data),
            "push_connected": coordinator.push_connected,
            "last_update_success": coordinator.last_update_success,
            "devices": coordinator.data,
            "messages": list(coordinator.client.messages),
        },
        TO_REDACT,
    )
