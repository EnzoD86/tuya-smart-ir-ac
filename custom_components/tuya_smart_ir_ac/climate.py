import logging
from homeassistant.core import callback
from homeassistant.helpers import entity_registry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    HVACMode,
    ClimateEntityFeature
)
from homeassistant.const import (
    EVENT_STATE_CHANGED,
    UnitOfTemperature
)
from .const import (
    DOMAIN,
    COORDINATOR
)
from .helpers import valid_sensor_state
from .entity import TuyaEntity

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data.get(DOMAIN).get(COORDINATOR)
    registry = entity_registry.async_get(hass)
    async_add_entities([TuyaClimate(config_entry.data, coordinator, registry)])


class TuyaClimate(ClimateEntity, RestoreEntity, CoordinatorEntity, TuyaEntity):
    def __init__(self, config, coordinator, registry):
        TuyaEntity.__init__(self, config, registry)
        super().__init__(coordinator, context=self._climate_id)

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self.climate_unique_id()

    @property
    def device_info(self):
        return self.tuya_device_info()

    @property
    def available(self):
        return self.coordinator.is_available(self._climate_id)

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def supported_features(self):
        return ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property
    def min_temp(self):
        return self._min_temp

    @property
    def max_temp(self):
        return self._max_temp

    @property
    def target_temperature_step(self):
        return self._temp_step

    @property
    def current_temperature(self):
        sensor_state = self.hass.states.get(self._temperature_sensor) if self._temperature_sensor is not None else None
        return float(sensor_state.state) if valid_sensor_state(sensor_state) else None

    @property
    def current_humidity(self):
        sensor_state = self.hass.states.get(self._humidity_sensor) if self._humidity_sensor is not None else None
        return float(sensor_state.state) if valid_sensor_state(sensor_state) else None

    @property
    def hvac_modes(self):
        return self._hvac_modes

    @property
    def fan_modes(self):
        return self._fan_modes

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.load_optional_entities()
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._async_handle_event)
        last_state = await self.async_get_last_state()
        if valid_sensor_state(last_state):
            self._attr_hvac_mode = last_state.state
            self._attr_target_temperature = last_state.attributes.get("temperature")
            self._attr_fan_mode = last_state.attributes.get("fan_mode")
        else:
            self._attr_hvac_mode = HVACMode.OFF
            self._attr_target_temperature = 0
            self._attr_fan_mode = FAN_AUTO

    @callback
    async def _async_handle_event(self, event):
        if event.data.get("entity_id") in [self._temperature_sensor, self._humidity_sensor]:
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self):
        data = self.coordinator.data.get(self._climate_id)
        if data:
            self._attr_hvac_mode = data.hvac_mode if data.power else HVACMode.OFF
            self._attr_target_temperature = data.temperature
            self._attr_fan_mode = data.fan_mode
            self.async_write_ha_state()

    async def async_turn_on(self):
        _LOGGER.info(f"{self.entity_id} turn on")
        await self.coordinator.async_turn_on(self._infrared_id, self._climate_id)
        self._handle_coordinator_update()

    async def async_turn_off(self):
        _LOGGER.info(f"{self.entity_id} turn off")
        await self.coordinator.async_turn_off(self._infrared_id, self._climate_id)
        self._handle_coordinator_update()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is not None:
            _LOGGER.info(f"{self.entity_id} setting temperature to {temperature}")
            await self.coordinator.async_set_temperature(self._infrared_id, self._climate_id, temperature)
            self._handle_coordinator_update()

    async def async_set_fan_mode(self, fan_mode):
        _LOGGER.info(f"{self.entity_id} setting fan mode to {fan_mode}")
        await self.coordinator.async_set_fan_mode(self._infrared_id, self._climate_id, fan_mode)
        self._handle_coordinator_update()

    async def async_set_hvac_mode(self, hvac_mode):
        _LOGGER.info(f"{self.entity_id} setting hvac mode to {hvac_mode}")
        temperature = self.get_hvac_temperature(hvac_mode)
        fan_mode = self.get_hvac_fan_mode(hvac_mode)
        if hvac_mode is HVACMode.OFF:
            await self.coordinator.async_turn_off(self._infrared_id, self._climate_id)
        else:
            if self.get_hvac_power_on(self._attr_hvac_mode):
                await self.coordinator.async_turn_on(self._infrared_id, self._climate_id)
            await self.coordinator.async_set_hvac_mode(self._infrared_id, self._climate_id, hvac_mode, temperature, fan_mode)
        self._handle_coordinator_update()