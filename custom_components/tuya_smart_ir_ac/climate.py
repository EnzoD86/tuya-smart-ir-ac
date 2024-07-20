import voluptuous as vol

import logging

from pprint import pformat

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate.const import (
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


class TuyaClimate(ClimateEntity):
    def __init__(self, hass, config):
        self._api = TuyaAPI(
            hass,
            config[CONF_ACCESS_ID],
            config[CONF_ACCESS_SECRET],
            config[CONF_CLIMATE_ID],
            config[CONF_INFRARED_ID],
            TUYA_API_URLS.get(config[CONF_TUYA_COUNTRY])
        )
        self._name = config.get(CONF_NAME)
        self._unique_id = config.get(CONF_UNIQUE_ID, None)
        self._temperature_sensor = config.get(CONF_TEMPERATURE_SENSOR, None)
        self._humidity_sensor = config.get(CONF_HUMIDITY_SENSOR, None)
        self._min_temp = config.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP)
        self._max_temp = config.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP)
        self._temp_step = config.get(CONF_TEMP_STEP, DEFAULT_PRECISION)

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
        _LOGGER.info("TEMPERATURE SENSOR STATE ", sensor_state)
        return float(sensor_state.state) if sensor_state and sensor_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE] else None

    @property
    def current_humidity(self):
        sensor_state = self.hass.states.get(self._humidity_sensor) if self._humidity_sensor is not None else None
        _LOGGER.info("HUMIDITY SENSOR STATE ", sensor_state)
        return float(sensor_state.state) if sensor_state and sensor_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE] else None

    @property
    def target_temperature(self):
        return float(self._api._temperature) if self._api._temperature else None

    @property
    def hvac_mode(self):
        if self._api._power == "0":
            return HVACMode.OFF
        return TUYA_HVAC_MODES.get(str(self._api._mode), None)

    @property
    def hvac_modes(self):
        return list(TUYA_HVAC_MODES.values())

    @property
    def fan_mode(self):
        return TUYA_FAN_MODES.get(str(self._api._wind), None) 

    @property
    def fan_modes(self):
        return list(TUYA_FAN_MODES.values())

    async def async_update(self):
        await self._api.async_update()
        self.async_write_ha_state()

    async def async_turn_on(self):
        _LOGGER.info("TURN ON")
        await self._api.async_turn_on()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is not None:
            _LOGGER.info("SETTING TEMPERATURE TO " + str(temperature))
            await self._api.async_set_temperature(float(temperature))

    async def async_set_fan_mode(self, fan_mode):
        _LOGGER.info("SETTING FAN MODE TO " + fan_mode)
        for mode, mode_name in TUYA_FAN_MODES.items():
            if fan_mode == mode_name:
                await self._api.async_set_fan_speed(mode)
                break

    async def async_set_hvac_mode(self, hvac_mode):
        _LOGGER.info("SETTING HVAC MODE TO " + hvac_mode)
        for mode, mode_name in TUYA_HVAC_MODES.items():
            if hvac_mode == mode_name:
                if mode == "5":
                    await self._api.async_turn_off()
                else:
                    await self._api.async_set_multiple(power = "1", mode = mode, temp = self._api._temperature, wind = "0")
                break
