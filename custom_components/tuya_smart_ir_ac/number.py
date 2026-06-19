import logging
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    RestoreNumber
)
from homeassistant.components.number.const import (
    NumberDeviceClass,
    NumberMode
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HVAC_PRESETS,
    CONF_OPTIONAL_ENTITIES,
    DEVICE_TYPE_CLIMATES,
    SUPPORTED_TEMP_HVAC_MODES,
    PRESET_TEMP_HVAC_MODE,
    ENTITY_TEMPERATURE_SETPOINT,
    TRANSLATION_KEY_HVAC_MODE
)
from .helpers import (
    valid_number_data,
    clamp_to_boundaries
)
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
    """Set up Tuya number entities from a config entry."""
    active_entities = []
    climates_data = config_entry.options.get(DEVICE_TYPE_CLIMATES, [])
    runtime_data = config_entry.runtime_data

    for config_data in climates_data:
        hvac_presets = config_data.get(CONF_HVAC_PRESETS, [])
        if PRESET_TEMP_HVAC_MODE in hvac_presets:
            for mode in SUPPORTED_TEMP_HVAC_MODES:  
                entity = TuyaPresetTemperatureNumber(config_data, runtime_data, mode)
                active_entities.append(entity)

        optional_entities = config_data.get(CONF_OPTIONAL_ENTITIES, [])    
        if optional_entities:
            if ENTITY_TEMPERATURE_SETPOINT in optional_entities:
                entity = TuyaTemperatureSetPointNumber(config_data, runtime_data)
                active_entities.append(entity)

    if active_entities:
        _LOGGER.debug(
            "[%s] Initialized %d number platform entities", 
            config_entry.title, 
            len(active_entities)
        )
        async_add_entities(active_entities)


class TuyaPresetTemperatureNumber(RestoreNumber, TuyaClimateEntity):
    """Representation of a Tuya preset temperature configuration entity."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData, temp_hvac_mode: str) -> None:
        """Initialize the preset temperature entity."""
        TuyaClimateEntity.__init__(self, config_data, runtime_data, f"{PRESET_TEMP_HVAC_MODE}_{temp_hvac_mode}")
        RestoreNumber.__init__(self)
        self._temp_hvac_mode = temp_hvac_mode

        self._attr_has_entity_name = True
        self. _attr_translation_key= f"{TRANSLATION_KEY_HVAC_MODE}_{temp_hvac_mode}"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_min_value = self._min_temp
        self._attr_native_max_value = self._max_temp
        self._attr_native_step = self._temp_step
        self._attr_native_unit_of_measurement = self._temperature_unit

    async def async_added_to_hass(self) -> None:
        """Handle entity data restoration and sync with central hvac_presets."""
        last_number = await self.async_get_last_number_data()
        
        if valid_number_data(last_number):
            restored_value = last_number.native_value
            self._attr_native_value = clamp_to_boundaries(restored_value, self._min_temp, self._max_temp)
        else:
            calculated_fallback = (self._min_temp + self._max_temp) / 2
            self._attr_native_value = clamp_to_boundaries(calculated_fallback, self._min_temp, self._max_temp)

        self.set_hvac_preset_temperature(self._temp_hvac_mode, self._attr_native_value)

    async def async_set_native_value(self, value: float) -> None:
        """Set new local preset temperature and commit the state change to RuntimeData."""
        self._attr_native_value = value
        self.set_hvac_preset_temperature(self._temp_hvac_mode, value)
        self.async_write_ha_state()


class TuyaTemperatureSetPointNumber(NumberEntity, CoordinatorEntity, TuyaClimateEntity):
    """Representation of a Tuya temperature setpoint dynamic entity linked to the coordinator."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData) -> None:
        """Initialize the temperature setpoint entity."""
        TuyaClimateEntity.__init__(self, config_data, runtime_data, ENTITY_TEMPERATURE_SETPOINT)
        super().__init__(runtime_data.climate_coordinator)

        self._attr_has_entity_name = True
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_mode = NumberMode.BOX
        self._attr_native_min_value = self._min_temp
        self._attr_native_max_value = self._max_temp
        self._attr_native_step = self._temp_step
        self._attr_native_unit_of_measurement = self._temperature_unit

    @property
    def native_value(self) -> float | None:
        """Return target climate temperature setpoint value fetched from coordinator cache data."""
        return self._current_target_temperature

    async def async_set_native_value(self, value: float) -> None:
        """Transmit new target temperature setpoint using central execution logic."""
        await self.async_handle_set_temperature(value)