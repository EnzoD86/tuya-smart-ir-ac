import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPE_CLIMATES
from .helpers import valid_sensor_state
from .entity import TuyaClimateEntity
from .models import HubConfigEntry, RuntimeData

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


class TuyaClimate(ClimateEntity, RestoreEntity, CoordinatorEntity, TuyaClimateEntity):
    """Representation of a Tuya climate entity managed via IR."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData) -> None:
        """Initialize the climate entity and assign central shared boundaries."""
        self._runtime_data = runtime_data
        TuyaClimateEntity.__init__(self, config_data, runtime_data)
        super().__init__(runtime_data.climate_coordinator)

        self._attr_has_entity_name = True
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:air-conditioner"
        self._attr_min_temp = self._min_temp
        self._attr_max_temp = self._max_temp
        self._attr_target_temperature_step = self._temp_step
        self._attr_hvac_modes = self._hvac_modes
        self._attr_fan_modes = self._fan_modes
        self._attr_supported_features = (
            ClimateEntityFeature.TURN_OFF 
            | ClimateEntityFeature.TURN_ON 
            | ClimateEntityFeature.TARGET_TEMPERATURE 
            | ClimateEntityFeature.FAN_MODE
        )

        self._fallback_hvac_mode = HVACMode.OFF
        self._fallback_target_temperature = 25.0
        self._fallback_fan_mode = FAN_AUTO

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
        if self._device_climate_data:
            return self._current_hvac_mode
        return self._fallback_hvac_mode

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if data := self._device_climate_data:
            return data.temperature
        return self._fallback_target_temperature

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        if data := self._device_climate_data:
            return data.fan_mode
        return self._fallback_fan_mode

    async def async_added_to_hass(self) -> None:
        """Restore previous entity state and track source sensors."""
        await super().async_added_to_hass()
        self.async_track_sensor_states([self._temperature_sensor, self._humidity_sensor])

        last_state = await self.async_get_last_state()
        if valid_sensor_state(last_state):
            if last_state.state in [mode.value for mode in HVACMode]:
                self._fallback_hvac_mode = HVACMode(last_state.state)
            self._fallback_target_temperature = last_state.attributes.get("temperature", 25.0)
            self._fallback_fan_mode = last_state.attributes.get("fan_mode", FAN_AUTO)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle state changes notified by the Hub coordinator."""
        super()._handle_coordinator_update()
        
    @callback
    def _handle_sensor_state_change(self, event) -> None:
        """Trigger an internal state update when a monitored external sensor changes value."""
        if event.data.get("new_state") is not None: 
            self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn on the climate."""
        await self.async_execute_turn_on()

    async def async_turn_off(self) -> None:
        """Turn off the climate."""
        await self.async_execute_turn_off()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set hvac mode for the climate."""
        await self.async_execute_set_hvac_mode(hvac_mode=hvac_mode)
        self.async_write_ha_state()
        
    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature for the climate."""
        temperature = kwargs.get("temperature", None)
        hvac_mode = kwargs.get("hvac_mode", None)
        
        if temperature is not None:
            await self.async_execute_set_temperature(temperature, hvac_mode)
        elif hvac_mode is not None:
            await self.async_execute_set_hvac_mode(hvac_mode)

        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode for the climate."""
        await self.async_execute_set_fan_mode(fan_mode)
        self.async_write_ha_state()