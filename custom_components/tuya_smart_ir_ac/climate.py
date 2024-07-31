import voluptuous as vol
import logging
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    HVACMode,
    ClimateEntityFeature,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP
)
from homeassistant.const import (
    UnitOfTemperature, 
    STATE_UNKNOWN, 
    STATE_UNAVAILABLE,
    CONF_NAME,
    CONF_UNIQUE_ID
)
from .const import (
    CONF_INFRARED_ID,
    CONF_CLIMATE_ID,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_TEMP_MIN,
    CONF_TEMP_MAX,
    CONF_TEMP_STEP,
    CONF_HVAC_MODES,
    CONF_FAN_MODES,
    DEFAULT_PRECISION,
    DEFAULT_HVAC_MODES,
    DEFAULT_FAN_MODES
)
from .service import TuyaService


_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    infrared_id = config_entry.data.get(CONF_INFRARED_ID)
    climate_id = config_entry.data.get(CONF_CLIMATE_ID)
    service = TuyaService(hass, infrared_id, climate_id)

    async_add_entities([TuyaClimate(hass, config_entry.data, service)])


class TuyaClimate(ClimateEntity, RestoreEntity):
    def __init__(self, hass, config, service):
        self._service = service
        self._name = config.get(CONF_NAME)
        self._temperature_sensor = config.get(CONF_TEMPERATURE_SENSOR, None)
        self._humidity_sensor = config.get(CONF_HUMIDITY_SENSOR, None)
        self._min_temp = config.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP)
        self._max_temp = config.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP)
        self._temp_step = config.get(CONF_TEMP_STEP, DEFAULT_PRECISION)
        self._hvac_modes = config.get(CONF_HVAC_MODES, DEFAULT_HVAC_MODES)
        self._fan_modes = config.get(CONF_FAN_MODES, DEFAULT_FAN_MODES)

        self._hvac_mode = HVACMode.OFF
        self._fan_mode = FAN_AUTO
        self._target_temperature = 0

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._name

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
        return float(sensor_state.state) if sensor_state and sensor_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE] else None

    @property
    def current_humidity(self):
        sensor_state = self.hass.states.get(self._humidity_sensor) if self._humidity_sensor is not None else None
        return float(sensor_state.state) if sensor_state and sensor_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE] else None

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return self._hvac_modes

    @property
    def fan_mode(self):
        return self._fan_mode

    @property
    def fan_modes(self):
        return self._fan_modes

    async def async_added_to_hass(self):
        last_state = await self.async_get_last_state()
        if last_state:
            self._hvac_mode = last_state.state
            self._fan_mode = last_state.attributes.get("fan_mode")
            self._target_temperature = last_state.attributes.get("temperature")

    async def async_update(self):
        status = await self._service.async_fetch_status()
        if (status and 
        (self._hvac_mode != status.hvac_mode 
        or self._fan_mode != status.fan_mode 
        or self._target_temperature != status.temperature)):
            self._hvac_mode = status.hvac_mode
            self._fan_mode = status.fan_mode
            self._target_temperature = status.temperature
            self.async_write_ha_state()

    async def async_turn_on(self):
        _LOGGER.info(f"{self.entity_id} turn on")
        await self._service.async_turn_on()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is not None:
            _LOGGER.info(f"{self.entity_id} setting temperature to {temperature}")
            await self._service.async_set_temperature(temperature)

    async def async_set_fan_mode(self, fan_mode):
        _LOGGER.info(f"{self.entity_id} setting fan mode to {fan_mode}")
        await self._service.async_set_fan_mode(fan_mode)

    async def async_set_hvac_mode(self, hvac_mode):
        _LOGGER.info(f"{self.entity_id} setting hvac mode to {hvac_mode}")
        await self._service.async_set_hvac_mode(hvac_mode, self._target_temperature, FAN_AUTO)