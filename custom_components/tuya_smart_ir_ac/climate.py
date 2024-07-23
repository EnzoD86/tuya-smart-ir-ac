import voluptuous as vol

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
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
from homeassistant.components.climate import ClimateEntity

from .const import TUYA_HVAC_MODES, TUYA_FAN_MODES, TUYA_API_URLS
from .api import TuyaAPI

_LOGGER = logging.getLogger(__package__)

CONF_ACCESS_ID = "access_id"
CONF_ACCESS_SECRET = "access_secret"
CONF_INFRARED_ID = "infrared_id"
CONF_CLIMATE_ID = "climate_id"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_TEMP_MIN = "min_temp"
CONF_TEMP_MAX = "max_temp"
CONF_TEMP_STEP = "temp_step"
CONF_TUYA_COUNTRY = "country"

DEFAULT_PRECISION = 1.0
DEFAULT_TUYA_COUNTRY = "EU"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ACCESS_ID): cv.string,
        vol.Required(CONF_ACCESS_SECRET): cv.string,
        vol.Required(CONF_INFRARED_ID): cv.string,
        vol.Required(CONF_CLIMATE_ID): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_TEMPERATURE_SENSOR): cv.entity_id,
        vol.Optional(CONF_HUMIDITY_SENSOR): cv.entity_id,
        vol.Optional(CONF_TEMP_MIN, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_TEMP_MAX, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_TEMP_STEP, default=DEFAULT_PRECISION): vol.Coerce(float),
        vol.Optional(CONF_TUYA_COUNTRY, default=DEFAULT_TUYA_COUNTRY): vol.In(TUYA_API_URLS.keys())
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:

    add_entities([TuyaClimate(hass, config)])


class TuyaClimate(ClimateEntity, RestoreEntity):
    def __init__(self, hass, config):
        self._api = TuyaAPI(
            hass,
            TUYA_API_URLS.get(config.get(CONF_TUYA_COUNTRY)),
            config.get(CONF_ACCESS_ID),
            config.get(CONF_ACCESS_SECRET),
            config.get(CONF_CLIMATE_ID),
            config.get(CONF_INFRARED_ID)
        )
        
        self._name = config.get(CONF_NAME)
        self._unique_id = config.get(CONF_UNIQUE_ID, None)
        self._temperature_sensor = config.get(CONF_TEMPERATURE_SENSOR, None)
        self._humidity_sensor = config.get(CONF_HUMIDITY_SENSOR, None)
        self._min_temp = config.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP)
        self._max_temp = config.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP)
        self._temp_step = config.get(CONF_TEMP_STEP, DEFAULT_PRECISION)
        
        self._hvac_mode = HVACMode.OFF
        self._fan_mode = FAN_AUTO
        self._target_temperature = 0

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

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
        return list(TUYA_HVAC_MODES.values())

    @property
    def fan_mode(self):
        return self._fan_mode

    @property
    def fan_modes(self):
        return list(TUYA_FAN_MODES.values())

    async def async_added_to_hass(self):
        last_state = await self.async_get_last_state()
        if last_state:
            self._hvac_mode = last_state.state
            self._fan_mode = last_state.attributes.get("fan_mode")
            self._target_temperature = last_state.attributes.get("temperature")

    async def async_update(self):
        status = await self._api.async_get_status()
        if status: 
            self._hvac_mode = HVACMode.OFF if status.power == "0" else TUYA_HVAC_MODES.get(str(status.mode), None)
            self._fan_mode = TUYA_FAN_MODES.get(str(status.wind), None)
            self._target_temperature = float(status.temperature)
            self.async_write_ha_state()

    async def async_turn_on(self):
        _LOGGER.info(f"{self.entity_id} turn on")
        await self._api.async_turn_on()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is not None:
            _LOGGER.info(f"{self.entity_id} setting temperature to {temperature}")
            await self._api.async_set_temperature(float(temperature))

    async def async_set_fan_mode(self, fan_mode):
        _LOGGER.info(f"{self.entity_id} setting fan mode to {fan_mode}")
        for mode, mode_name in TUYA_FAN_MODES.items():
            if fan_mode == mode_name:
                await self._api.async_set_fan_speed(mode)
                break

    async def async_set_hvac_mode(self, hvac_mode):
        _LOGGER.info(f"{self.entity_id} setting hvac mode to {hvac_mode}")
        for mode, mode_name in TUYA_HVAC_MODES.items():
            if hvac_mode == mode_name:
                if mode == "5":
                    await self._api.async_turn_off()
                else:
                    await self._api.async_set_multiple("1", mode, self._target_temperature, "0")
                break
