"""Shared entity base and helpers."""
from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TARGET_HAMMAM, TARGET_SAUNA
from .coordinator import EffeCoordinator

HAMMAM = "hammam"
SAUNA = "sauna"
TARGETS = {HAMMAM: TARGET_HAMMAM, SAUNA: TARGET_SAUNA}
# Prefix of the cabin's fields in readOnlyState (hDoor, sDoor, ...).
RO_PREFIX = {HAMMAM: "h", SAUNA: "s"}


def cabins(device: dict[str, Any]) -> list[str]:
    """Return the cabins (hammam and/or sauna) this module controls."""
    equipments = device.get("equipments") or {}
    return [
        cabin
        for cabin, flag in ((HAMMAM, "hasHammam"), (SAUNA, "hasSauna"))
        if equipments.get(flag)
    ]


def has_function(device: dict[str, Any], cabin: str, name: str) -> bool:
    """Check the module's capability flags, e.g. hammamRgb."""
    return bool((device.get("functionalities") or {}).get(f"{cabin}{name}"))


def active_alarms(device: dict[str, Any]) -> list[str]:
    """Return all raised alarm flags as "group.name"."""
    return sorted(
        f"{group}.{name}"
        for group, flags in (device.get("alarm") or {}).items()
        if isinstance(flags, dict)
        for name, value in flags.items()
        if name != "timestamp" and value is True
    )


class EffeEntity(CoordinatorEntity[EffeCoordinator]):
    """Base entity bound to one cabin of one ECC module."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EffeCoordinator, ecc_id: str, cabin: str, key: str) -> None:
        super().__init__(coordinator)
        self._ecc_id = ecc_id
        self._cabin = cabin
        self._attr_translation_key = key
        self._attr_unique_id = f"{ecc_id}_{cabin}_{key}"
        device = self.device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, ecc_id)},
            manufacturer="Effe (Effegibi)",
            model=f"ECC {device.get('systemType') or ''}".strip(),
            name=f"Effe {' / '.join(c.capitalize() for c in cabins(device)) or 'ECC'}",
            serial_number=ecc_id,
            sw_version=device.get("firmwareVersion"),
        )

    @property
    def device(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._ecc_id, {})

    @property
    def state_data(self) -> dict[str, Any]:
        return (self.device.get("state") or {}).get(self._cabin) or {}

    @property
    def read_only(self) -> dict[str, Any]:
        return self.device.get("readOnlyState") or {}

    def ro(self, name: str) -> Any:
        """Read a cabin field from readOnlyState, e.g. ro("Door") -> hDoor."""
        return self.read_only.get(f"{RO_PREFIX[self._cabin]}{name}")

    @property
    def available(self) -> bool:
        return super().available and self._ecc_id in self.coordinator.data

    async def async_command(self, function: str, value: str) -> None:
        await self.coordinator.async_command(
            self._ecc_id, function, TARGETS[self._cabin], value
        )

    def check_safe_to_heat(self) -> None:
        """Refuse a remote heating start while the module reports a door or alarm.

        The cloud and the controller apply their own interlocks on top of this;
        this check only makes sure Home Assistant never asks for heat in a
        state the module itself flags as unsafe.
        """
        if self.ro("Door"):
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="door_open"
            )
        if alarms := active_alarms(self.device):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="alarm_active",
                translation_placeholders={"alarms": ", ".join(alarms)},
            )
