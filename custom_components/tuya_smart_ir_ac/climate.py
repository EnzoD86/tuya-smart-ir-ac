import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    PRESET_NONE
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPE_CLIMATES
from .entity import TuyaClimateEntity
from .models import (
    HubConfigEntry,
    RuntimeData,
)

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: HubConfigEntry, 
    async_add_entities
) -> None:
    """Set up Tuya climate entities from a config entry."""
    climates_data = config_entry.options.get(DEVICE_TYPE_CLIMATES, [])
    runtime_data = config_entry.runtime_data
    
    active_entities = []
    for data in climates_data:
        entity = TuyaClimate(data, runtime_data)
        active_entities.append(entity)

    if active_entities:
        _LOGGER.debug(
            "[%s] Initialized %d climate platform entities", 
            config_entry.title, 
            len(active_entities)
        )
        async_add_entities(active_entities)


class TuyaClimate(ClimateEntity, CoordinatorEntity, TuyaClimateEntity):
    """Representation of a Tuya climate entity managed via IR."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData) -> None:
        """Initialize the climate entity and assign central shared boundaries."""
        self._runtime_data = runtime_data
        TuyaClimateEntity.__init__(self, config_data, runtime_data)
        super().__init__(runtime_data.climate_coordinator)

        self._attr_has_entity_name = True
        self._attr_temperature_unit = self._temperature_unit
        self._attr_icon = "mdi:air-conditioner"
        self._attr_min_temp = self._min_temp
        self._attr_max_temp = self._max_temp
        self._attr_target_temperature_step = self._temp_step
        self._attr_hvac_modes = self._hvac_modes
        self._attr_fan_modes = self._fan_modes
        self._attr_preset_modes = self._preset_modes

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features dynamically."""
        features = (
            ClimateEntityFeature.TURN_OFF 
            | ClimateEntityFeature.TURN_ON 
            | ClimateEntityFeature.TARGET_TEMPERATURE 
            | ClimateEntityFeature.FAN_MODE
        )
        
        if self._preset_modes:
            features |= ClimateEntityFeature.PRESET_MODE
            
        return features

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature value from the linked tracking sensor."""
        return self.get_temperature_value(convert=True)
    
    @property
    def current_humidity(self) -> float | None:
        """Return the current humidity value from the linked tracking sensor."""
        return self.get_humidity_value()

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current hvac operation mode."""
        return self._current_hvac_mode

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._current_target_temperature

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        return self._current_fan_mode

    @property
    def preset_modes(self) -> list[str] | None:
        """Return the list of available preset modes based on current HVAC mode."""
        return self.get_preset_modes()

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return self.get_preset_mode()

    async def async_added_to_hass(self) -> None:
        """Restore previous entity state and track source sensors."""
        await super().async_added_to_hass()
        self.async_track_sensor_states([self._temperature_sensor, self._humidity_sensor])
        self.update_preset_history()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle state changes notified by the Hub coordinator."""
        self.update_preset_history()
        self.async_write_ha_state()

    @callback
    def _handle_sensor_state_change(self, event) -> None:
        """Trigger an internal state update when a monitored external sensor changes value."""
        if event.data.get("new_state") is not None: 
            self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn on the climate."""
        await self.async_handle_turn_on()

    async def async_turn_off(self) -> None:
        """Turn off the climate."""
        await self.async_handle_turn_off()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set hvac mode for the climate."""
        await self.async_handle_set_hvac_mode(hvac_mode=hvac_mode)
        
    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature for the climate."""
        temperature = kwargs.get("temperature", None)
        hvac_mode = kwargs.get("hvac_mode", None)
        
        if temperature is not None:
            await self.async_handle_set_temperature(temperature, hvac_mode)
        elif hvac_mode is not None:
            await self.async_handle_set_hvac_mode(hvac_mode)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode for the climate."""
        await self.async_handle_set_fan_mode(fan_mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode for the climate."""
        await self.async_handle_set_preset_mode(preset_mode)
        self.async_write_ha_state()