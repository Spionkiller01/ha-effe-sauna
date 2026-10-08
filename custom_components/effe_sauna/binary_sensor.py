"""Binary sensors: door, ready, heating, alarms, cloud push."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EffeConfigEntry
from .entity import HAMMAM, SAUNA, EffeEntity, active_alarms, cabins


@dataclass(frozen=True, kw_only=True)
class EffeBinarySensorDescription(BinarySensorEntityDescription):
    cabins: tuple[str, ...] = (HAMMAM, SAUNA)
    value: Callable[[EffeEntity], Any]
    per_module: bool = False


BINARY_SENSORS = (
    EffeBinarySensorDescription(
        key="door",
        device_class=BinarySensorDeviceClass.DOOR,
        value=lambda e: e.ro("Door"),
    ),
    EffeBinarySensorDescription(key="ready", value=lambda e: e.ro("Ready")),
    EffeBinarySensorDescription(
        key="steam",
        cabins=(HAMMAM,),
        device_class=BinarySensorDeviceClass.RUNNING,
        value=lambda e: e.state_data.get("steamOn"),
    ),
    EffeBinarySensorDescription(
        key="paused", cabins=(HAMMAM,), value=lambda e: e.state_data.get("pauseOn")
    ),
    EffeBinarySensorDescription(
        key="warm",
        cabins=(HAMMAM,),
        device_class=BinarySensorDeviceClass.HEAT,
        value=lambda e: e.state_data.get("warmOn"),
    ),
    EffeBinarySensorDescription(
        key="heating",
        cabins=(SAUNA,),
        device_class=BinarySensorDeviceClass.HEAT,
        value=lambda e: e.state_data.get("saunaOn"),
    ),
    EffeBinarySensorDescription(
        key="service",
        cabins=(HAMMAM,),
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda e: e.ro("Service"),
    ),
    EffeBinarySensorDescription(
        key="alarm",
        per_module=True,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value=lambda e: bool(active_alarms(e.device)),
    ),
    EffeBinarySensorDescription(
        key="push",
        per_module=True,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda e: e.coordinator.push_connected,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EffeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        EffeBinarySensor(coordinator, ecc_id, cabin, description)
        for ecc_id, device in coordinator.data.items()
        for index, cabin in enumerate(cabins(device))
        for description in BINARY_SENSORS
        if cabin in description.cabins and (index == 0 or not description.per_module)
    )


class EffeBinarySensor(EffeEntity, BinarySensorEntity):
    entity_description: EffeBinarySensorDescription

    def __init__(self, coordinator, ecc_id: str, cabin: str, description: EffeBinarySensorDescription) -> None:
        super().__init__(coordinator, ecc_id, cabin, description.key)
        self.entity_description = description
        if description.per_module:
            self._attr_unique_id = f"{ecc_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        value = self.entity_description.value(self)
        return None if value is None else bool(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key == "alarm":
            return {"alarms": active_alarms(self.device)}
        return None
