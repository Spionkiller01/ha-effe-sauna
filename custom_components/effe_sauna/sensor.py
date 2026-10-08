"""Sensors: setpoints, timer and diagnostics."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EffeConfigEntry
from .entity import HAMMAM, SAUNA, EffeEntity, active_alarms, cabins


@dataclass(frozen=True, kw_only=True)
class EffeSensorDescription(SensorEntityDescription):
    cabins: tuple[str, ...] = (HAMMAM, SAUNA)
    value: Callable[[EffeEntity], Any]
    # Only one instance per module, attached to its first cabin.
    per_module: bool = False


def _timestamp(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(value) / 1000, UTC)
    except (TypeError, ValueError):
        return None


SENSORS = (
    EffeSensorDescription(
        key="steam_setpoint",
        cabins=(HAMMAM,),
        device_class=SensorDeviceClass.TEMPERATURE,
        value=lambda e: e.state_data.get("setpointHammam") or None,
    ),
    EffeSensorDescription(
        key="sauna_setpoint",
        cabins=(SAUNA,),
        device_class=SensorDeviceClass.TEMPERATURE,
        value=lambda e: e.state_data.get("setpointSauna") or None,
    ),
    EffeSensorDescription(
        key="humidity_setpoint",
        cabins=(SAUNA,),
        native_unit_of_measurement=PERCENTAGE,
        value=lambda e: e.state_data.get("setpointRelativeHumidity"),
    ),
    # Raw value as configured on the panel; its unit is not documented.
    EffeSensorDescription(
        key="timer",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda e: e.ro("Timer"),
    ),
    EffeSensorDescription(
        key="alarms",
        per_module=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda e: ", ".join(active_alarms(e.device)) or "none",
    ),
    EffeSensorDescription(
        key="last_seen",
        per_module=True,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda e: _timestamp(e.device.get("lastSeenAt")),
    ),
    EffeSensorDescription(
        key="ip_address",
        per_module=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value=lambda e: (e.device.get("network") or {}).get("ipv4"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EffeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        EffeSensor(coordinator, ecc_id, cabin, description)
        for ecc_id, device in coordinator.data.items()
        for index, cabin in enumerate(cabins(device))
        for description in SENSORS
        if cabin in description.cabins and (index == 0 or not description.per_module)
    )


class EffeSensor(EffeEntity, SensorEntity):
    entity_description: EffeSensorDescription

    def __init__(self, coordinator, ecc_id: str, cabin: str, description: EffeSensorDescription) -> None:
        super().__init__(coordinator, ecc_id, cabin, description.key)
        self.entity_description = description
        if description.per_module:
            self._attr_unique_id = f"{ecc_id}_{description.key}"

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.device_class is SensorDeviceClass.TEMPERATURE:
            if self.device.get("temperatureMeasureUnit") == "fahrenheit":
                return UnitOfTemperature.FAHRENHEIT
            return UnitOfTemperature.CELSIUS
        return self.entity_description.native_unit_of_measurement

    @property
    def native_value(self) -> Any:
        return self.entity_description.value(self)
