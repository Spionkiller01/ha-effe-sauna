"""Switches: control panel, mood light, infrared, biosauna."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import FN_BIOSAUNA, FN_IR, FN_MOOD, FN_POWER
from .coordinator import EffeConfigEntry
from .entity import HAMMAM, SAUNA, EffeEntity, cabins, has_function


@dataclass(frozen=True, kw_only=True)
class EffeSwitchDescription(SwitchEntityDescription):
    cabins: tuple[str, ...]
    state_key: str
    function: str
    # Capability flag suffix (e.g. "Mood" -> hammamMood); None = always present.
    capability: str | None = None
    # readOnlyState suffix that must not be False (e.g. "MoodEn" -> hMoodEn).
    enabled_flag: str | None = None
    heats: bool = False


SWITCHES = (
    EffeSwitchDescription(
        key="panel", cabins=(HAMMAM,), state_key="panelOn", function=FN_POWER
    ),
    EffeSwitchDescription(
        key="mood",
        cabins=(HAMMAM, SAUNA),
        state_key="moodOn",
        function=FN_MOOD,
        capability="Mood",
        enabled_flag="MoodEn",
    ),
    EffeSwitchDescription(
        key="infrared",
        cabins=(SAUNA,),
        state_key="irOn",
        function=FN_IR,
        capability="Ir",
        heats=True,
    ),
    EffeSwitchDescription(
        key="biosauna",
        cabins=(SAUNA,),
        state_key="biosaunaOn",
        function=FN_BIOSAUNA,
        heats=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EffeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities = []
    for ecc_id, device in coordinator.data.items():
        for cabin in cabins(device):
            for description in SWITCHES:
                if cabin not in description.cabins:
                    continue
                if description.capability and not has_function(
                    device, cabin, description.capability
                ):
                    continue
                entity = EffeSwitch(coordinator, ecc_id, cabin, description)
                if description.enabled_flag and entity.ro(description.enabled_flag) is False:
                    continue
                entities.append(entity)
    async_add_entities(entities)


class EffeSwitch(EffeEntity, SwitchEntity):
    entity_description: EffeSwitchDescription

    def __init__(self, coordinator, ecc_id: str, cabin: str, description: EffeSwitchDescription) -> None:
        super().__init__(coordinator, ecc_id, cabin, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return bool(self.state_data.get(self.entity_description.state_key))

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.entity_description.heats:
            self.check_safe_to_heat()
        await self.async_command(self.entity_description.function, "1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_command(self.entity_description.function, "0")
