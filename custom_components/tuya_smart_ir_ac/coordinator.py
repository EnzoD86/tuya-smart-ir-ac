import logging
import async_timeout
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ServiceValidationError
from .helpers import (
    filter_set_temperature,
    filter_set_fan_mode,
    filter_set_hvac_mode,
    hass_temperature,
    hass_fan_mode,
    hass_hvac_mode_v1,
    hass_hvac_mode_v2
)
from .const import (
    DOMAIN,
    UPDATE_INTERVAL,
    UPDATE_TIMEOUT
)

_LOGGER = logging.getLogger(__package__)


class TuyaCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
            always_update=False
        )
        self._api = api

    async def async_fetch_all_data(self, climate_ids):
        all_data = await self._api.async_fetch_all_data(climate_ids)
        devices = {}
        for data in all_data:
            devices[data.get("devId")] = TuyaData().parse_data_v1(data)
        return devices

    async def async_fetch_data(self, infrared_id, climate_id):
        data = await self._api.async_fetch_data(infrared_id, climate_id)
        return TuyaData().parse_data_v2(data)
        
    async def async_turn_on(self, infrared_id, climate_id):
        try:
            await self._api.async_send_command(infrared_id, climate_id, "power", "1")
            await self.async_request_refresh()
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_turn_on")
            
    async def async_turn_off(self, infrared_id, climate_id):
        try:
            await self._api.async_send_command(infrared_id, climate_id, "power", "0")
            await self.async_request_refresh()
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_turn_off")

    @filter_set_temperature
    async def async_set_temperature(self, infrared_id, climate_id, temp):
        try:
            await self._api.async_send_command(infrared_id, climate_id, "temp", temp)
            await self.async_request_refresh()
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_temperature")

    @filter_set_fan_mode
    async def async_set_fan_mode(self, infrared_id, climate_id, wind):
        try:
            await self._api.async_send_command(infrared_id, climate_id, "wind", wind)
            await self.async_request_refresh()
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_fan_mode")

    @filter_set_hvac_mode
    async def async_set_hvac_mode(self, infrared_id, climate_id, mode, temp, wind):
        try:
            if mode == "5":
                await self._api.async_send_command(infrared_id, climate_id, "power", "0")
            else:
                await self._api.async_send_multiple_command(infrared_id, climate_id, "1", mode, temp, wind)
            await self.async_request_refresh()                
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_hvac_mode")
            
    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(UPDATE_TIMEOUT):
                climate_ids = set(self.async_contexts())
                return await self.async_fetch_all_data(climate_ids)
        except Exception:
            raise UpdateFailed("error communicating with Tuya API")


class TuyaData(object):
    def parse_data_v1(self, data):
        self.hvac_mode = hass_hvac_mode_v1(data.get("powerOpen"), data.get("mode"))
        self.fan_mode = hass_fan_mode(data.get("fan"))
        self.temperature = hass_temperature(data.get("temp"))
        return self

    def parse_data_v2(self, data):
        self.hvac_mode = hass_hvac_mode_v2(data.get("power"), data.get("mode"))
        self.fan_mode = hass_fan_mode(data.get("wind"))
        self.temperature = hass_temperature(data.get("temp"))
        return self
        
    def __eq__(self, data):
        return (
            self.hvac_mode == data.hvac_mode and 
            self.fan_mode == data.fan_mode and 
            self.temperature == data.temperature
        )