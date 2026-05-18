import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.climate import HVACMode

from .const import (
    DEVICE_TYPE_CLIMATES,
    CONF_HVAC_PRESETS,
    CONF_OPTIONAL_ENTITIES,
    ENTITY_HVAC_MODE,
    ENTITY_FAN_MODE,
    PRESET_FAN_HVAC_MODE
)
from .helpers import valid_sensor_state
from .entity import TuyaClimateEntity
from .models import HubConfigEntry, RuntimeData

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: HubConfigEntry, 
    async_add_entities
) -> None:
    """Set up Tuya select entities from a config entry."""
    active_entities = []
    climates_data = config_entry.options.get(DEVICE_TYPE_CLIMATES, [])
    runtime_data = config_entry.runtime_data

    for data in climates_data:
        hvac_presets = data.get(CONF_HVAC_PRESETS, [])
        if PRESET_FAN_HVAC_MODE in hvac_presets:
            entity = TuyaPresetFanSelect(data, runtime_data)
            active_entities.append(entity)

        optional_entities = data.get(CONF_OPTIONAL_ENTITIES, [])
        if optional_entities:
            if ENTITY_HVAC_MODE in optional_entities:
                entity = TuyaHvacModeSelect(data, runtime_data)
                active_entities.append(entity)

            if ENTITY_FAN_MODE in optional_entities:   
                entity = TuyaFanModeSelect(data, runtime_data)
                active_entities.append(entity)

    if active_entities:
        async_add_entities(active_entities)


class TuyaPresetFanSelect(SelectEntity, RestoreEntity, TuyaClimateEntity):
    """Representation of a Tuya preset fan configuration entity."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData) -> None:
        """Initialize the preset fan select entity."""
        TuyaClimateEntity.__init__(self, config_data, runtime_data, PRESET_FAN_HVAC_MODE)

        self._attr_has_entity_name = True
        self._attr_translation_key = f"{PRESET_FAN_HVAC_MODE}"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:fan"
        self._attr_options = self._fan_modes

    async def async_added_to_hass(self) -> None:
        """Handle entity registry and restore previous state."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        
        if valid_sensor_state(last_state):
            self._attr_current_option = last_state.state
        else:
            self._attr_current_option = self._attr_options[0] if self._attr_options else None
            _LOGGER.debug(
                "No restored state for preset fan memory on device %s, using fallback option: %s", 
                self._name, self._attr_current_option
            )

        if self._attr_current_option:
            self.set_hvac_preset_fan_mode(self._attr_current_option)

    async def async_select_option(self, option: str) -> None:
        """Change the selected preset option."""
        _LOGGER.debug("Updating preset fan speed to %s for device %s", option, self._name)
        self._attr_current_option = option
        self.set_hvac_preset_fan_mode(option)
        self.async_write_ha_state()


class TuyaHvacModeSelect(SelectEntity, CoordinatorEntity, TuyaClimateEntity):
    """Representation of a select entity linked dynamically to the climate hvac state."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData) -> None:
        """Initialize the hvac mode select entity."""
        TuyaClimateEntity.__init__(self, config_data, runtime_data, ENTITY_HVAC_MODE)
        super().__init__(runtime_data.climate_coordinator)

        self._attr_has_entity_name = True
        self._attr_translation_key = f"{ENTITY_HVAC_MODE}"
        self._attr_icon = "mdi:hvac"
        self._attr_options = self._hvac_modes

    @property
    def current_option(self) -> str | None:
        """Return the current HVAC mode option directly from the coordinator cache data."""
        if self.coordinator.data and (data := self.coordinator.data.get(self._climate_id)):
            if not data.power:
                return HVACMode.OFF.value
            
            if data.hvac_mode:
                return data.hvac_mode.value if isinstance(data.hvac_mode, HVACMode) else data.hvac_mode
                
        return HVACMode.OFF.value

    async def async_select_option(self, option: str) -> None:
        """Forward the selected option to the central execution logic."""
        _LOGGER.debug("Sending operational mode override to %s for device %s", option, self._name)
        await self.async_execute_set_hvac_mode(HVACMode(option))
        self.async_write_ha_state()


class TuyaFanModeSelect(SelectEntity, CoordinatorEntity, TuyaClimateEntity):
    """Representation of a select entity linked dynamically to the climate fan state."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData) -> None:
        """Initialize the fan mode select entity."""
        TuyaClimateEntity.__init__(self, config_data, runtime_data, ENTITY_FAN_MODE)
        super().__init__(runtime_data.climate_coordinator)

        self._attr_has_entity_name = True
        self._attr_translation_key = f"{ENTITY_FAN_MODE}"
        self._attr_icon = "mdi:fan"
        self._attr_options = self._fan_modes

    @property
    def current_option(self) -> str | None:
        """Return the current fan mode option directly from the coordinator cache data."""
        if self.coordinator.data and (data := self.coordinator.data.get(self._climate_id)):
            return data.fan_mode
        return None

    async def async_select_option(self, option: str) -> None:
        """Forward the selected option to the central execution logic."""
        _LOGGER.debug("Sending fan speed override to %s for device %s", option, self._name)
        await self.async_execute_set_fan_mode(option)
        self.async_write_ha_state()