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
)
from homeassistant.const import UnitOfTemperature, STATE_UNKNOWN, STATE_UNAVAILABLE
from homeassistant.components.climate import ClimateEntity

from .const import VALID_MODES
from .api import TuyaAPI

_LOGGER = logging.getLogger(__package__)

ACCESS_ID = "access_id"
ACCESS_SECRET = "access_secret"
REMOTE_ID = "remote_id"
AC_ID = "ac_id"
NAME = "name"
SENSOR = "sensor"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(ACCESS_ID): cv.string,
        vol.Required(ACCESS_SECRET): cv.string,
        vol.Required(REMOTE_ID): cv.string,
        vol.Required(AC_ID): cv.string,
        vol.Required(NAME): cv.string,
        vol.Required(SENSOR): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    climate = {
        "access_id": config[ACCESS_ID],
        "access_secret": config[ACCESS_SECRET],
        "remote_id": config[REMOTE_ID],
        "ac_id": config[AC_ID],
        "name": config[NAME],
        "sensor": config[SENSOR]
    }

    add_entities([TuyaThermostat(climate, hass)])


class TuyaThermostat(ClimateEntity):
    def __init__(self, climate, hass):
        #_LOGGER.debug(pformat(climate))
        self._api = TuyaAPI(
            hass,
            climate[ACCESS_ID],
            climate[ACCESS_SECRET],
            climate[AC_ID],
            climate[REMOTE_ID],
        )
        self._sensor_name = climate[SENSOR]
        self._name = climate[NAME]

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return "tuya_hack_01"

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

    @property
    def min_temp(self):
        return 18

    @property
    def max_temp(self):
        return 30

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
        return VALID_MODES.get(str(self._api._mode), None)

    @property
    def hvac_modes(self):
        return list(VALID_MODES.values())

    @property
    def fan_mode(self):
        return (
            "Low"
            if self._api._wind == "1"
            else "Medium"
            if self._api._wind == "2"
            else "High"
            if self._api._wind == "3"
            else "Automatic"
            if self._api._wind == "0"
            else None
        )

    @property
    def fan_modes(self):
        return list(["Low", "Medium", "High", "Automatic"])

    async def async_set_fan_mode(self, fan_mode):
        if fan_mode == "Low":
            await self._api.send_command("wind", "1")
        elif fan_mode == "Medium":
            await self._api.send_command("wind", "2")
        elif fan_mode == "High":
            await self._api.send_command("wind", "3")
        elif fan_mode == "Automatic":
            await self._api.send_command("wind", "0")
        else:
            await self._api.send_command("wind", "0")
            _LOGGER.warning("Invalid fan mode.")

    async def async_update(self):
        await self._api.async_update()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is not None:
            await self._api.async_set_temperature(float(temperature))

    async def async_set_hvac_mode(self, hvac_mode):
        _LOGGER.info("SETTING HVAC MODE TO " + hvac_mode)
        for mode, mode_name in VALID_MODES.items():
            if hvac_mode == mode_name:
                if mode == "5":
                    await self._api.async_turn_off()
                else:
                    if self._api._power == "0":
                        await self._api.async_turn_on()
                    await self._api.async_set_fan_speed(0)
                    await self._api.async_set_hvac_mode(hvac_mode)
                break
