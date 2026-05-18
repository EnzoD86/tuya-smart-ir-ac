import logging
from datetime import timedelta
import asyncio

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ServiceValidationError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACMode

from .const import DOMAIN, UPDATE_INTERVAL, UPDATE_TIMEOUT
from .helpers import tuya_temp, tuya_mode, tuya_wind
from .api import TuyaClimateAPI, TuyaSensorAPI
from .models import TuyaClimateData, TuyaSensorData
from .tuya_connector import TuyaOpenAPI


_LOGGER = logging.getLogger(__package__)


class TuyaClimateCoordinator(DataUpdateCoordinator[dict[str, TuyaClimateData]]):
    """Coordinator for IR climate entities, based on ConfigEntry options."""

    def __init__(
        self, 
        hass: HomeAssistant, 
        entry: ConfigEntry, 
        client: TuyaOpenAPI, 
        custom_update_interval=UPDATE_INTERVAL
    ):
        """Initialize the climate coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.title}_climate",
            update_interval=timedelta(seconds=custom_update_interval),
            always_update=False
        )
        self.entry = entry
        self._api = TuyaClimateAPI(hass, client=client)

    def is_available(self, climate_id: str) -> bool:
        """Check if the climate device is available in the fetched data."""
        return self.data and self.data.get(climate_id) is not None

    async def _async_update_data(self) -> dict[str, TuyaClimateData]:
        """Fetch data from Tuya API via periodic polling using batch endpoint."""
        try:
            async with asyncio.timeout(UPDATE_TIMEOUT):
                climate_ids = [device["device_id"] for device in self.entry.options.get("climates", [])]
                
                if not climate_ids:
                    return {}
                    
                result = await self._api.async_fetch_all_data(climate_ids)
                
                if not result.success:
                    raise UpdateFailed(f"Tuya cloud reported an error: {result.error_info}")
                    
                return result.data
        except UpdateFailed:
            raise
        except Exception as e:
            raise UpdateFailed(f"Error communicating with Tuya API: {e}")

    async def async_turn_on(self, infrared_id: str, climate_id: str):
        """Send IR command to turn on the climate entity and update local cache."""
        result = await self._api.async_send_command(infrared_id, climate_id, "power", "1")
        if not result.success:
            _LOGGER.error("Failed to turn on climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_turn_on")
            
        self._async_force_update_data(climate_id, power=True)

    async def async_turn_off(self, infrared_id: str, climate_id: str):
        """Send IR command to turn off the climate entity and update local cache."""
        result = await self._api.async_send_command(infrared_id, climate_id, "power", "0")
        if not result.success:
            _LOGGER.error("Failed to turn off climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_turn_off")
            
        self._async_force_update_data(climate_id, power=False)

    async def async_set_temperature(self, infrared_id: str, climate_id: str, temperature: float):
        """Send IR command to set target temperature and update local cache."""
        result = await self._api.async_send_command(infrared_id, climate_id, "temp", tuya_temp(temperature))
        if not result.success:
            _LOGGER.error("Failed to set temperature for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_temperature")
            
        self._async_force_update_data(climate_id, power=True, temperature=temperature)

    async def async_set_fan_mode(self, infrared_id: str, climate_id: str, fan_mode: str):
        """Send IR command to set fan mode and update local cache."""
        result = await self._api.async_send_command(infrared_id, climate_id, "wind", tuya_wind(fan_mode))
        if not result.success:
            _LOGGER.error("Failed to set fan mode for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_fan_mode")
            
        self._async_force_update_data(climate_id, power=True, fan_mode=fan_mode)

    async def async_set_hvac_mode(self, infrared_id: str, climate_id: str, hvac_mode: HVACMode, temperature: float, fan_mode: str):
        """Send a combined multi-command IR packet (Mode, Temp, Fan) and update local cache."""
        result = await self._api.async_send_multiple_command(
            infrared_id, climate_id, "1", tuya_mode(hvac_mode), tuya_temp(temperature), tuya_wind(fan_mode)
        )
        if not result.success:
            _LOGGER.error("Failed to set HVAC combined mode for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_hvac_mode")
            
        self._async_force_update_data(climate_id, power=True, hvac_mode=hvac_mode, temperature=temperature, fan_mode=fan_mode)

    def _async_force_update_data(self, climate_id, power=None, hvac_mode=None, temperature=None, fan_mode=None):
        """Optimistically update local state cache after an IR command execution."""
        if self.data and (data := self.data.get(climate_id)):
            data.power = power if power is not None else data.power
            data.hvac_mode = hvac_mode if hvac_mode is not None else data.hvac_mode
            data.temperature = temperature if temperature is not None else data.temperature
            data.fan_mode = fan_mode if fan_mode is not None else data.fan_mode
            self.async_update_listeners()


class TuyaSensorCoordinator(DataUpdateCoordinator[dict[str, TuyaSensorData]]):
    """Coordinator for physical Hub sensors, based on ConfigEntry options."""

    def __init__(
        self, 
        hass: HomeAssistant, 
        entry: ConfigEntry, 
        client: TuyaOpenAPI, 
        custom_update_interval=300
    ):
        """Initialize the sensor coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.title}_sensor",
            update_interval=timedelta(seconds=custom_update_interval),
            always_update=False
        )
        self.entry = entry
        self._api = TuyaSensorAPI(hass, client=client)

    def is_available(self, device_id: str) -> bool:
        """Check if the sensor device is available in the fetched data."""
        return self.data and self.data.get(device_id) is not None

    async def _async_update_data(self) -> dict[str, TuyaSensorData]:
        """Fetch data from Tuya API via periodic polling."""
        try:
            async with asyncio.timeout(UPDATE_TIMEOUT):
                device_ids = [device["device_id"] for device in self.entry.options.get("sensors", [])]
                
                if not device_ids:
                    return {}
                    
                result = await self._api.async_fetch_all_data(device_ids)
                
                if not result.success:
                    raise UpdateFailed(f"Tuya cloud reported an error fetching sensors: {result.error_info}")
                    
                return result.data
        except UpdateFailed:
            raise
        except Exception as e:
            raise UpdateFailed(f"Error communicating with Tuya API for sensors: {e}")