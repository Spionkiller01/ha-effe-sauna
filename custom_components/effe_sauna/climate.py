"""Climate entities: steam generator (hammam) and sauna heater."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    FN_SAUNA,
    FN_STEAM,
    FN_STEAM_SETPOINT,
    STEAM_LEVELS,
    STEAM_LEVELS_TOUCHNSTEAM,
    TOUCHNSTEAM_TYPES,
)
from .coordinator import EffeConfigEntry
from .entity import HAMMAM, SAUNA, EffeEntity, cabins


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EffeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[ClimateEntity] = []
    for ecc_id, device in coordinator.data.items():
        if HAMMAM in cabins(device):
            entities.append(EffeHammamClimate(coordinator, ecc_id, HAMMAM, "steam"))
        if SAUNA in cabins(device):
            entities.append(EffeSaunaClimate(coordinator, ecc_id, SAUNA, "sauna"))
    async_add_entities(entities)


class _EffeClimate(EffeEntity, ClimateEntity):
    _attr_name = None
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _on_key: str
    _setpoint_key: str
    _function: str

    @property
    def temperature_unit(self) -> str:
        if self.device.get("temperatureMeasureUnit") == "fahrenheit":
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.HEAT if self.state_data.get(self._on_key) else HVACMode.OFF

    @property
    def target_temperature(self) -> float | None:
        return self.state_data.get(self._setpoint_key) or None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.HEAT:
            self.check_safe_to_heat()
            await self.async_command(self._function, "1")
        else:
            await self.async_command(self._function, "0")

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)


class EffeHammamClimate(_EffeClimate):
    """Steam bath. The app only offers three steam levels, exposed as presets."""

    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _on_key = "steamOn"
    _setpoint_key = "setpointHammam"
    _function = FN_STEAM

    @property
    def _levels(self) -> dict[str, int]:
        if self.device.get("systemType") in TOUCHNSTEAM_TYPES:
            return STEAM_LEVELS_TOUCHNSTEAM
        return STEAM_LEVELS

    @property
    def min_temp(self) -> float:
        return min(self._levels.values())

    @property
    def max_temp(self) -> float:
        return max(self._levels.values())

    @property
    def preset_modes(self) -> list[str]:
        return list(self._levels)

    @property
    def preset_mode(self) -> str | None:
        setpoint = self.state_data.get(self._setpoint_key)
        return next((name for name, value in self._levels.items() if value == setpoint), None)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        # The app sends the level without a separate "steam on"; the controller
        # may start steaming on its own, so apply the same safety check.
        self.check_safe_to_heat()
        await self.async_command(FN_STEAM_SETPOINT, str(self._levels[preset_mode]))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"ready": self.ro("Ready"), "paused": self.state_data.get("pauseOn")}


class EffeSaunaClimate(_EffeClimate):
    """Sauna heater. The app cannot change the setpoint remotely, so it is read-only."""

    _attr_supported_features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
    _on_key = "saunaOn"
    _setpoint_key = "setpointSauna"
    _function = FN_SAUNA

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"ready": self.ro("Ready")}
