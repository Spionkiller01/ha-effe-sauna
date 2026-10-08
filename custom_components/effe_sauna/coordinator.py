"""Data coordinator: AppSync push with REST polling as fallback."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EffeAuthError, EffeClient, EffeError
from .const import (
    DOMAIN,
    FN_INFO,
    POLL_INTERVAL_NO_PUSH,
    POLL_INTERVAL_PUSH,
    TARGET_ALL,
)

_LOGGER = logging.getLogger(__name__)

type EffeConfigEntry = ConfigEntry[EffeCoordinator]


def _merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge a push update; the subscription reports unknown values as null."""
    result = dict(base)
    for key, value in update.items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


class EffeCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Holds the state of all ECC modules of one account, keyed by eccId."""

    config_entry: EffeConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EffeConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=POLL_INTERVAL_NO_PUSH,
        )
        self.client = EffeClient(
            async_get_clientsession(hass), entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD]
        )
        self.push_connected = False
        self._push_task: asyncio.Task | None = None

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            devices = await self.client.async_get_devices()
        except EffeAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except EffeError as err:
            raise UpdateFailed(str(err)) from err
        return {device["eccId"]: device for device in devices}

    def async_start_push(self) -> None:
        """Start the push listener for the devices known right now."""
        self._push_task = self.config_entry.async_create_background_task(
            self.hass,
            self.client.async_listen(
                list(self.data), self._handle_push, self._handle_push_connection
            ),
            name=f"{DOMAIN}_push",
        )

    @callback
    def _handle_push(self, update: dict[str, Any]) -> None:
        ecc_id = update.get("eccId")
        if self.data is None or ecc_id not in self.data:
            return
        self.async_set_updated_data(
            {**self.data, ecc_id: _merge(self.data[ecc_id], update)}
        )

    @callback
    def _handle_push_connection(self, connected: bool) -> None:
        if connected == self.push_connected:
            return
        self.push_connected = connected
        self.update_interval = POLL_INTERVAL_PUSH if connected else POLL_INTERVAL_NO_PUSH
        if connected:
            # Updates may have been missed while the socket was down: have the
            # modules report in and re-read the cloud copy.
            self.config_entry.async_create_background_task(
                self.hass, self._async_resync(), name=f"{DOMAIN}_resync"
            )
        elif self.data is not None:
            self.async_set_updated_data(self.data)  # reschedule with the short interval

    async def _async_resync(self) -> None:
        for device in list((self.data or {}).values()):
            try:
                await self.client.async_send_command(device, FN_INFO, TARGET_ALL, "")
            except EffeError as err:
                _LOGGER.debug("INFO request failed: %s", err)
        await self.async_request_refresh()

    async def async_command(
        self, ecc_id: str, function: str, target: str, value: str
    ) -> None:
        """Send a command; the resulting state arrives through push."""
        try:
            await self.client.async_send_command(self.data[ecc_id], function, target, value)
        except EffeError as err:
            raise HomeAssistantError(f"Effe command {function} failed: {err}") from err
        if not self.push_connected:
            await asyncio.sleep(2)
            await self.async_request_refresh()
