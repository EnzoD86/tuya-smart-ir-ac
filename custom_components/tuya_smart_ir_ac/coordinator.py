import logging
from datetime import datetime, timedelta, timezone
import asyncio

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ServiceValidationError
from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACMode

from .const import (
    CONF_CLIMATE_UPDATE_INTERVAL,
    CONF_DEVICE_ID,
    CONF_SENSOR_UPDATE_INTERVAL,
    DOMAIN,
    DEVICE_TYPE_CLIMATES,
    DEVICE_TYPE_SENSORS,
    UPDATE_INTERVAL,
    UPDATE_TIMEOUT,
    DEFAULT_OFFLINE_THRESHOLD_HOURS,
)
from .helpers import tuya_temp, tuya_mode, tuya_wind
from .models import HubConfigEntry, TuyaClimateData, TuyaSensorData
from .connector import TuyaConnector

_LOGGER = logging.getLogger(__package__)


class TuyaClimateCoordinator(DataUpdateCoordinator[dict[str, TuyaClimateData]]):
    """Coordinator for IR climate entities, based on ConfigEntry options."""

    def __init__(
        self, 
        hass: HomeAssistant, 
        entry: HubConfigEntry, 
        connector: TuyaConnector
    ):
        """Initialize the climate coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"[{entry.title}] Climate Coordinator",
            update_interval=timedelta(seconds=entry.data.get(CONF_CLIMATE_UPDATE_INTERVAL, UPDATE_INTERVAL)),
            always_update=False
        )
        self.entry = entry
        self._api = connector.climate_api
        self._pulsar_bridge = connector.pulsar_bridge
        self.data = {}

    def sync_devices(self) -> None:
        """Synchronize coordinator state and Pulsar handlers with current options."""
        current_dev_ids = {
            str(d.get(CONF_DEVICE_ID))
            for d in self.entry.options.get(DEVICE_TYPE_CLIMATES, [])
            if d.get(CONF_DEVICE_ID)
        }

        stale_dev_ids = [dev_id for dev_id in self.data if dev_id not in current_dev_ids]
        for dev_id in stale_dev_ids:
            self.data.pop(dev_id, None)
            if self._pulsar_bridge:
                self._pulsar_bridge.unregister_handler(dev_id)

        for dev_id in current_dev_ids:
            if self._pulsar_bridge:
                self._pulsar_bridge.register_handler(dev_id, self._async_update_from_pulsar)

    def is_available(self, climate_id: str) -> bool:
        """Check if the climate device is available in the fetched data."""
        return self.data and self.data.get(climate_id) is not None

    def get_climate_data(self, climate_id: str) -> TuyaClimateData:
        """Return the latest climate data for a device, or its default state."""
        return self.data.get(climate_id, TuyaClimateData())

    async def async_send_power_command(
        self, infrared_id: str, climate_id: str, is_on: bool
    ) -> None:
        """Send a power command and handle validation errors."""
        state = "1" if is_on else "0"
        _LOGGER.debug("[%s] Sending IR command to turn %s climate", climate_id, "ON" if is_on else "OFF")
        result = await self._api.async_send_command(infrared_id, climate_id, "power", state)
        if not result.success:
            _LOGGER.error("Failed to turn %s climate %s: %s", "on" if is_on else "off", climate_id, result.error_info)
            translation_key = "climate_error_turn_on" if is_on else "climate_error_turn_off"
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key=translation_key)

    async def async_send_temperature_command(
        self, infrared_id: str, climate_id: str, temperature: float
    ) -> None:
        """Send raw temperature command and handle validation errors."""
        _LOGGER.debug("[%s] Sending IR command to set temperature to %s°C", climate_id, temperature)
        result = await self._api.async_send_command(infrared_id, climate_id, "temp", tuya_temp(temperature))
        if not result.success:
            _LOGGER.error("Failed to set temperature for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_temperature")

    async def async_send_fan_mode_command(
        self, infrared_id: str, climate_id: str, fan_mode: str
    ) -> None:
        """Send raw fan mode command and handle validation errors."""
        _LOGGER.debug("[%s] Sending IR command to set fan mode to %s", climate_id, fan_mode)
        result = await self._api.async_send_command(infrared_id, climate_id, "wind", tuya_wind(fan_mode))
        if not result.success:
            _LOGGER.error("Failed to set fan mode for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_fan_mode")

    async def async_send_hvac_mode_command(
        self, infrared_id: str, climate_id: str, hvac_mode: HVACMode
    ) -> None:
        """Send raw HVAC mode command and handle validation errors."""
        _LOGGER.debug("[%s] Sending IR command to set HVAC mode to %s", climate_id, hvac_mode)
        result = await self._api.async_send_command(infrared_id, climate_id, "mode", tuya_mode(hvac_mode))
        if not result.success:
            _LOGGER.error("Failed to set HVAC mode for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_hvac_mode")

    async def async_send_combined_command(
        self,
        infrared_id: str,
        climate_id: str,
        hvac_mode: HVACMode,
        temperature: float,
        fan_mode: str,
    ) -> None:
        """Send multi-command IR packet and handle validation errors."""
        _LOGGER.debug("[%s] Sending combined IR packet -> Mode: %s, Temp: %s, Fan: %s", climate_id, hvac_mode, temperature, fan_mode)
        result = await self._api.async_send_multiple_command(
            infrared_id, climate_id, "1", tuya_mode(hvac_mode), tuya_temp(temperature), tuya_wind(fan_mode)
        )
        if not result.success:
            _LOGGER.error("Failed to set HVAC combined mode for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_hvac_mode")

    def update_climate_cache(
        self,
        climate_id: str,
        power: bool | None = None,
        hvac_mode: HVACMode | None = None,
        temperature: float | None = None,
        fan_mode: str | None = None,
    ) -> None:
        """Optimistically update local state cache after an IR command execution."""
        if self.data and (current_data := self.data.get(climate_id)):
            self.data[climate_id] = TuyaClimateData.from_optimistic_update(
                current_data,
                power=power,
                hvac_mode=hvac_mode,
                temperature=temperature,
                fan_mode=fan_mode
            )
            self.async_update_listeners()

    async def _async_update_data(self) -> dict[str, TuyaClimateData]:
        """Fetch data from Tuya API via periodic polling using batch endpoint."""
        climate_ids = [device[CONF_DEVICE_ID] for device in self.entry.options.get(DEVICE_TYPE_CLIMATES, [])]
        if not climate_ids:
            return {}

        try:
            _LOGGER.debug("Fetching climate data for devices: %s", str(climate_ids))
            async with asyncio.timeout(UPDATE_TIMEOUT):
                result = await self._api.async_fetch_all_data(climate_ids)

                if not result.success:
                    raise ValueError(result.error_info)

                return result.data
        except (TimeoutError, ValueError, Exception) as e:
            _LOGGER.warning("Error or timeout communicating with Tuya API for climates: %s. Keeping fallback cache.", e)
            return self.data

    async def _async_update_from_pulsar(self, device_id: str, new_status: dict):
        """Process incoming Pulsar updates for climate devices."""
        current_item = self.data.get(device_id)
        status = new_status.get("status", [])
        if current_item and status:
            _LOGGER.debug("[%s] Update climate from Pulsar: %s", device_id, str(new_status))
            updated_state = TuyaClimateData.from_pulsar_data(current_item, status)
            self.data[device_id] = updated_state
            self.async_update_listeners()


class TuyaSensorCoordinator(DataUpdateCoordinator[dict[str, TuyaSensorData]]):
    """Coordinator for physical Hub sensors, with unified Smart Polling logic."""

    def __init__(self,
        hass: HomeAssistant, 
        entry: HubConfigEntry, 
        connector: TuyaConnector
    ):
        super().__init__(
            hass,
            _LOGGER,
            name=f"[{entry.title}] Sensor Coordinator",
            update_interval=timedelta(seconds=entry.data.get(CONF_SENSOR_UPDATE_INTERVAL, UPDATE_INTERVAL)),
            always_update=False
        )
        self.entry = entry
        self._api = connector.sensor_api
        self._pulsar_bridge = connector.pulsar_bridge
        self._supported_dps: dict[str, set[str]] = {}
        self.data = {}

    def sync_devices(self) -> None:
        """Synchronize coordinator state and Pulsar handlers with current options."""
        current_dev_ids = {
            str(d.get(CONF_DEVICE_ID))
            for d in self.entry.options.get(DEVICE_TYPE_SENSORS, [])
            if d.get(CONF_DEVICE_ID)
        }

        stale_dev_ids = [dev_id for dev_id in self.data if dev_id not in current_dev_ids]
        for dev_id in stale_dev_ids:
            self.data.pop(dev_id, None)
            if self._pulsar_bridge:
                self._pulsar_bridge.unregister_handler(dev_id)

        for dev_id in current_dev_ids:
            if self._pulsar_bridge:
                self._pulsar_bridge.register_handler(dev_id, self._async_update_from_pulsar)

    def is_available(self, device_id: str) -> bool:
        """Check if the device data is fresh within the allowed threshold."""
        device_data = self.data.get(device_id)
        if not device_data or not device_data.last_updated:
            return False

        return (datetime.now(timezone.utc) - device_data.last_updated) <= timedelta(hours=DEFAULT_OFFLINE_THRESHOLD_HOURS)

    def _needs_api_refresh(self, device_id: str, threshold: timedelta) -> bool:
        """Determine if API polling is needed based on the model's last_updated."""
        sensor_data = self.data.get(device_id)
        if not sensor_data or not sensor_data.last_updated:
            _LOGGER.debug("[%s] No data or timestamp recorded yet. API refresh needed.", device_id)
            return True

        now = datetime.now(timezone.utc)
        if (now - sensor_data.last_updated) > threshold:
            _LOGGER.debug("[%s] Sensor data is outdated. Triggering cloud update.", device_id)
            return True
        
        return False

    async def _async_update_data(self) -> dict[str, TuyaSensorData]:
        """Fetch data from Tuya API."""
        sensor_ids = [d[CONF_DEVICE_ID] for d in self.entry.options.get(DEVICE_TYPE_SENSORS, [])]
        threshold = self.update_interval - timedelta(seconds=5)
        devices_to_fetch = [d for d in sensor_ids if self._needs_api_refresh(d, threshold)]
        if not devices_to_fetch:
            return self.data

        try:
            _LOGGER.debug("Fetching sensor data for devices: %s", str(devices_to_fetch))
            async with asyncio.timeout(UPDATE_TIMEOUT):
                result = await self._api.async_fetch_all_data(devices_to_fetch)
                if not result.success:
                    raise UpdateFailed(f"Tuya error: {result.error_info}")
                
                for dev_id, sensor_data in result.data.items():
                    self._supported_dps[dev_id] = TuyaSensorData.get_available_dps(sensor_data)
                
                updated_data = self.data.copy()
                updated_data.update(result.data)
                return updated_data
        except TimeoutError as e:
            raise UpdateFailed(f"Timeout communicating with Tuya API for sensors: {e}")
        except Exception as e:
            raise UpdateFailed(f"Error communicating with Tuya API for sensors: {e}")

    async def _async_update_from_pulsar(self, device_id: str, new_status: dict):
        """Process incoming Pulsar updates in real-time."""
        status_list = new_status.get("status", [])
        if status_list:
            current_item = self.data.get(device_id)
            if current_item:
                _LOGGER.debug("[%s] Update sensor from Pulsar: %s", device_id, str(new_status))
                self.data[device_id] = TuyaSensorData.from_pulsar_data(current_item, status_list)
                self.async_update_listeners()