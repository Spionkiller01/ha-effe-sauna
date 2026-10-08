"""Lights: cabin light and chromotherapy (colour programmes as effects)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CHROMO_SHOWS, FN_CHROMO, FN_CHROMO_SHOW, FN_LIGHT
from .coordinator import EffeConfigEntry
from .entity import EffeEntity, cabins, has_function


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EffeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[LightEntity] = []
    for ecc_id, device in coordinator.data.items():
        for cabin in cabins(device):
            if has_function(device, cabin, "Light"):
                entities.append(EffeLight(coordinator, ecc_id, cabin, "light"))
            if has_function(device, cabin, "Rgb"):
                entities.append(EffeChromoLight(coordinator, ecc_id, cabin, "chromo"))
    async_add_entities(entities)


class EffeLight(EffeEntity, LightEntity):
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> bool:
        return bool(self.state_data.get("lightOn"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.async_command(FN_LIGHT, "1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_command(FN_LIGHT, "0")


class EffeChromoLight(EffeEntity, LightEntity):
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = list(CHROMO_SHOWS)

    @property
    def is_on(self) -> bool:
        return bool(self.state_data.get("chromoOn"))

    @property
    def effect(self) -> str | None:
        show = self.state_data.get("chromoShow")
        return next((name for name, value in CHROMO_SHOWS.items() if value == show), None)

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self.is_on:
            await self.async_command(FN_CHROMO, "1")
        if effect := kwargs.get(ATTR_EFFECT):
            await self.async_command(FN_CHROMO_SHOW, str(CHROMO_SHOWS[effect]))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_command(FN_CHROMO, "0")
