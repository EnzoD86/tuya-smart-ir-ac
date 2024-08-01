from homeassistant.exceptions import ServiceValidationError
from .helpers import (
    filter_set_temperature,
    filter_set_fan_mode,
    filter_set_hvac_mode,
    hass_temperature,
    hass_fan_mode,
    hass_hvac_mode
)
from .const import DOMAIN
from .api import TuyaAPI


class TuyaService:
    def __init__(self, hass, infrared_id, climate_id):
        self._api = TuyaAPI(hass, infrared_id, climate_id)

    async def async_fetch_status(self):
        status = await self._api.async_fetch_status()
        return TuyaData(status) if status else None

    async def async_turn_on(self):
        try:
            await self._api.async_send_command("power", "1")
        except Exception as e:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_turn_on")
        
    async def async_turn_off(self):
        await self._api.async_send_command("power", "0")

    @filter_set_temperature
    async def async_set_temperature(self, temp):
        try:
            await self._api.async_send_command("temp", temp)
        except Exception as e:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_temperature")

    @filter_set_fan_mode
    async def async_set_fan_mode(self, wind):
        try:
            await self._api.async_send_command("wind", wind)
        except Exception as e:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_fan_mode")

    @filter_set_hvac_mode
    async def async_set_hvac_mode(self, mode, temp, wind):
        try:
            if mode == "5":
                await self.async_turn_off()
            else:
                await self._api.async_send_multiple_command("1", mode, temp, wind)
        except Exception as e:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_hvac_mode")


class TuyaData(object):
    def __init__(self, status):
        self.hvac_mode = hass_hvac_mode(status.get("power"), status.get("mode"))
        self.fan_mode = hass_fan_mode(status.get("wind"))
        self.temperature = hass_temperature(status.get("temp"))