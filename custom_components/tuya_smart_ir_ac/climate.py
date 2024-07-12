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
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_FAN_MODE,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP
)
from homeassistant.const import (
    UnitOfTemperature, 
    STATE_UNKNOWN, 
    STATE_UNAVAILABLE,
    CONF_UNIQUE_ID
)
from homeassistant.components.climate import ClimateEntity

from .const import TUYA_HVAC_MODES, TUYA_FAN_MODES
from .api import TuyaAPI

_LOGGER = logging.getLogger(__package__)

CONF_ACCESS_ID = "access_id"
CONF_ACCESS_SECRET = "access_secret"
CONF_REMOTE_ID = "remote_id"
CONF_AC_ID = "ac_id"
CONF_NAME = "name"
CONF_SENSOR = "sensor"
CONF_TEMP_MIN = "min_temp"
CONF_TEMP_MAX = "max_temp"
CONF_TEMP_STEP = "temp_step"

DEFAULT_PRECISION = 1.0

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ACCESS_ID): cv.string,
        vol.Required(CONF_ACCESS_SECRET): cv.string,
        vol.Required(CONF_REMOTE_ID): cv.string,
        vol.Required(CONF_AC_ID): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_SENSOR): cv.string,
        vol.Optional(CONF_TEMP_MIN, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_TEMP_MAX, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_TEMP_STEP, default=DEFAULT_PRECISION): vol.Coerce(float),
        vol.Optional(CONF_UNIQUE_ID): cv.string
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    climate = {
        "access_id": config[CONF_ACCESS_ID],
        "access_secret": config[CONF_ACCESS_SECRET],
        "remote_id": config[CONF_REMOTE_ID],
        "ac_id": config[CONF_AC_ID],
        "name": config[CONF_NAME],
        "sensor": config[CONF_SENSOR],
        "min_temp": config.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP),
        "max_temp": config.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP),
        "temp_step": config.get(CONF_TEMP_STEP, DEFAULT_PRECISION),
        "unique_id": config.get(CONF_UNIQUE_ID, None)
    }

    add_entities([TuyaThermostat(climate, hass)])


class TuyaThermostat(ClimateEntity):
    def __init__(self, climate, hass):
        #_LOGGER.debug(pformat(climate))
        self._api = TuyaAPI(
            hass,
            climate[CONF_ACCESS_ID],
            climate[CONF_ACCESS_SECRET],
            climate[CONF_AC_ID],
            climate[CONF_REMOTE_ID],
        )
        self._sensor_name = climate[CONF_SENSOR]
        self._name = climate[CONF_NAME]
        self._min_temp = climate.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP)
        self._max_temp = climate.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP)
        self._temp_step = climate.get(CONF_TEMP_STEP, DEFAULT_PRECISION)
        self._unique_id = climate.get(CONF_UNIQUE_ID, None)

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
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

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
        sensor_state = self.hass.states.get(self._sensor_name)
        _LOGGER.info("SENSOR STATE ", sensor_state)
        if sensor_state and sensor_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
            return float(sensor_state.state)
        return float(self._api._temperature) if self._api._temperature else None

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
                    await self._api.async_init(power = "1", mode = mode, temp = self._api._temperature, wind = "0")
                break
