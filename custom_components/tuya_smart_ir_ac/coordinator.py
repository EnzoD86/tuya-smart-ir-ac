import logging
import async_timeout
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ServiceValidationError
from .helpers import (
    hass_temperature,
    hass_fan_mode,
    hass_hvac_mode,
    tuya_temp,
    tuya_mode,
    tuya_wind
)
from .const import (
    DOMAIN,
    FIRST_UPDATE,
    UPDATE_INTERVAL,
    UPDATE_TIMEOUT
)

_LOGGER = logging.getLogger(__package__)


class TuyaCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, custom_update_interval=UPDATE_INTERVAL):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=FIRST_UPDATE),
            always_update=False
        )
        self._api = api
        self._first_update = True
        self._custom_update_interval = custom_update_interval

    def is_available(self, climate_id):
        return self.data and self.data.get(climate_id, None) is not None

    async def async_fetch_data(self, climate_ids):
        all_data = await self._api.async_fetch_all_data(climate_ids)
        devices = {}
        for data in all_data:
            devices[data.get("devId")] = TuyaData().parse_data(data)
        return devices

    async def async_turn_on(self, infrared_id, climate_id):
        try:
            await self._api.async_send_command(infrared_id, climate_id, "power", "1")
            await self._async_force_update_data(climate_id, power=True)
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_turn_on")

    async def async_turn_off(self, infrared_id, climate_id):
        try:
            await self._api.async_send_command(infrared_id, climate_id, "power", "0")
            await self._async_force_update_data(climate_id, power=False)
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_turn_off")

    async def async_set_temperature(self, infrared_id, climate_id, temperature):
        try:
            await self._api.async_send_command(infrared_id, climate_id, "temp", tuya_temp(temperature))
            await self._async_force_update_data(climate_id, power=True, temperature=temperature)
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_temperature")

    async def async_set_fan_mode(self, infrared_id, climate_id, fan_mode):
        try:
            await self._api.async_send_command(infrared_id, climate_id, "wind", tuya_wind(fan_mode))
            await self._async_force_update_data(climate_id, power=True, fan_mode=fan_mode)
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_fan_mode")

    async def async_set_hvac_mode(self, infrared_id, climate_id, hvac_mode, temperature, fan_mode):
        try:
            await self._api.async_send_multiple_command(infrared_id, climate_id, "1", tuya_mode(hvac_mode), tuya_temp(temperature), tuya_wind(fan_mode))
            await self._async_force_update_data(climate_id, True, hvac_mode, temperature, fan_mode)
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_hvac_mode")

    async def _async_update_data(self):
        try:
            if self._first_update:
                self._first_update = False
                self.update_interval = timedelta(seconds=self._custom_update_interval)

            async with async_timeout.timeout(UPDATE_TIMEOUT):
                climate_ids = set(self.async_contexts())
                return await self.async_fetch_data(climate_ids)
        except Exception as e:
            raise UpdateFailed(f"error communicating with Tuya API {e}")

    async def _async_force_update_data(self, climate_id, power=None, hvac_mode=None, temperature=None, fan_mode=None):
        data = self.data.get(climate_id, None)
        if data:
            data.power = power if power is not None else data.power
            data.hvac_mode = hvac_mode if hvac_mode is not None else data.hvac_mode
            data.temperature = temperature if temperature is not None else data.temperature
            data.fan_mode = fan_mode if fan_mode is not None else data.fan_mode


class TuyaData(object):
    def parse_data(self, data):
        self.power = data.get("powerOpen")
        self.hvac_mode = hass_hvac_mode(data.get("mode"))
        self.temperature = hass_temperature(data.get("temp"))
        self.fan_mode = hass_fan_mode(data.get("fan"))
        return self

    def __eq__(self, data):
        return (
            self.power == data.power and
            self.hvac_mode == data.hvac_mode and 
            self.temperature == data.temperature and
            self.fan_mode == data.fan_mode
        )