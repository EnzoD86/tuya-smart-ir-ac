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

_LOGGER = logging.getLogger(__package__)


class TuyaClimateCoordinator(DataUpdateCoordinator[dict[str, TuyaClimateData]]):
    """Coordinator for IR climate entities, based on ConfigEntry options."""

    def __init__(
        self, 
        hass: HomeAssistant, 
        entry: ConfigEntry, 
        climate_api: TuyaClimateAPI,
        pulsar_bridge: TuyaPulsarBridge,
        custom_update_interval=UPDATE_INTERVAL
    ):
        """Initialize the climate coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"[{entry.title}] Climate Coordinator",
            update_interval=timedelta(seconds=custom_update_interval),
            always_update=False
        )
        self.entry = entry
        self._api = climate_api
        self._pulsar_bridge = pulsar_bridge

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh and register Pulsar handlers."""
        await super().async_config_entry_first_refresh()

        for dev_id in self.data.keys():
            self._pulsar_bridge.register_handler(dev_id, self._async_update_from_pulsar)

    def is_available(self, climate_id: str) -> bool:
        """Check if the climate device is available in the fetched data."""
        return self.data and self.data.get(climate_id) is not None

    async def async_turn_on(self, infrared_id: str, climate_id: str):
        """Send IR command to turn on the climate entity and update local cache."""
        _LOGGER.debug("[%s] Sending IR command to turn ON climate", climate_id)
        result = await self._api.async_send_command(infrared_id, climate_id, "power", "1")
        if not result.success:
            _LOGGER.error("Failed to turn on climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_turn_on")
            
        await self._async_force_update_data(climate_id, power=True)

    async def async_turn_off(self, infrared_id: str, climate_id: str):
        """Send IR command to turn off the climate entity and update local cache."""
        _LOGGER.debug("[%s] Sending IR command to turn OFF climate", climate_id)
        result = await self._api.async_send_command(infrared_id, climate_id, "power", "0")
        if not result.success:
            _LOGGER.error("Failed to turn off climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_turn_off")
            
        await self._async_force_update_data(climate_id, power=False)

    async def async_set_temperature(self, infrared_id: str, climate_id: str, temperature: float):
        """Send IR command to set target temperature and update local cache."""
        _LOGGER.debug("[%s] Sending IR command to set temperature to %s°C", climate_id, temperature)
        result = await self._api.async_send_command(infrared_id, climate_id, "temp", tuya_temp(temperature))
        if not result.success:
            _LOGGER.error("Failed to set temperature for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_temperature")
            
        await self._async_force_update_data(climate_id, power=True, temperature=temperature)

    async def async_set_fan_mode(self, infrared_id: str, climate_id: str, fan_mode: str):
        """Send IR command to set fan mode and update local cache."""
        _LOGGER.debug("[%s] Sending IR command to set fan mode to %s", climate_id, fan_mode)
        result = await self._api.async_send_command(infrared_id, climate_id, "wind", tuya_wind(fan_mode))
        if not result.success:
            _LOGGER.error("Failed to set fan mode for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_fan_mode")
            
        await self._async_force_update_data(climate_id, power=True, fan_mode=fan_mode)

    async def async_set_hvac_mode(self, infrared_id: str, climate_id: str, hvac_mode: HVACMode, temperature: float, fan_mode: str):
        """Send a combined multi-command IR packet (Mode, Temp, Fan) and update local cache."""
        _LOGGER.debug("[%s] Sending combined IR packet -> Mode: %s, Temp: %s, Fan: %s", climate_id, hvac_mode, temperature, fan_mode)
        result = await self._api.async_send_multiple_command(
            infrared_id, climate_id, "1", tuya_mode(hvac_mode), tuya_temp(temperature), tuya_wind(fan_mode)
        )
        if not result.success:
            _LOGGER.error("Failed to set HVAC combined mode for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_hvac_mode")
            
        await self._async_force_update_data(climate_id, power=True, hvac_mode=hvac_mode, temperature=temperature, fan_mode=fan_mode)

    async def _async_update_data(self) -> dict[str, TuyaClimateData]:
        """Fetch data from Tuya API via periodic polling using batch endpoint."""
        try:
            async with asyncio.timeout(UPDATE_TIMEOUT):
                climate_ids = [device["device_id"] for device in self.entry.options.get("climates", [])]
                
                if not climate_ids:
                    return {}
                    
                result = await self._api.async_fetch_all_data(climate_ids)
                
                if not result.success:
                    raise UpdateFailed(f"Tuya cloud reported an error fetching climates: {result.error_info}")
                    
                return result.data
        except UpdateFailed:
            raise
        except TimeoutError as e:
            raise UpdateFailed(f"Timeout communicating with Tuya API for climates: {e}")
        except Exception as e:
            raise UpdateFailed(f"Error communicating with Tuya API for climates: {e}")

    async def _async_force_update_data(self, climate_id, power=None, hvac_mode=None, temperature=None, fan_mode=None):
        """Optimistically update local state cache after an IR command execution."""
        if self.data and (data := self.data.get(climate_id)):
            data.power = power if power is not None else data.power
            data.hvac_mode = hvac_mode if hvac_mode is not None else data.hvac_mode
            data.temperature = temperature if temperature is not None else data.temperature
            data.fan_mode = fan_mode if fan_mode is not None else data.fan_mode
            self.async_update_listeners()

    async def _async_update_from_pulsar(self, device_id: str, new_status: dict):
        """Process incoming Pulsar updates for climate devices."""
        current_item = self.data.get(device_id)
        status = new_status.get("status", [])
        if current_item and status:
            _LOGGER.debug("[%s] Update climate from Pulsar: %s", device_id, str(new_status))
            updated_state = current_item.from_pulsar_data(status)
            self.data[device_id] = updated_state
            self.async_update_listeners()


class TuyaSensorCoordinator(DataUpdateCoordinator[dict[str, TuyaSensorData]]):
    """Coordinator for physical Hub sensors, based on ConfigEntry options."""

    def __init__(
        self, 
        hass: HomeAssistant, 
        entry: ConfigEntry, 
        sensor_api: TuyaSensorAPI, 
        pulsar_bridge: TuyaPulsarBridge,
        custom_update_interval=300
    ):
        """Initialize the sensor coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"[{entry.title}] Sensor Coordinator",
            update_interval=timedelta(seconds=custom_update_interval),
            always_update=False
        )
        self.entry = entry
        self._api = sensor_api
        self._pulsar_bridge = pulsar_bridge

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh and register Pulsar handlers."""
        await super().async_config_entry_first_refresh()

        for dev_id in self.data.keys():
            self._pulsar_bridge.register_handler(dev_id, self._async_update_from_pulsar)

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
        except TimeoutError as e:
            raise UpdateFailed(f"Timeout communicating with Tuya API for sensors: {e}")
        except Exception as e:
            raise UpdateFailed(f"Error communicating with Tuya API for sensors: {e}")

    async def _async_update_from_pulsar(self, device_id: str, new_status: dict):
        """Process incoming Pulsar updates for physical sensors."""
        current_item = self.data.get(device_id)
        status = new_status.get("status", [])
        if current_item and status:
            _LOGGER.debug("[%s] Update sensor from Pulsar: %s", device_id, str(new_status))
            updated_state = current_item.from_pulsar_data(status)
            self.data[device_id] = updated_state
            self.async_update_listeners()
            