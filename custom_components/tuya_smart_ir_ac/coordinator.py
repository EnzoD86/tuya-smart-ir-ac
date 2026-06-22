import logging
from datetime import datetime, timedelta, timezone
import asyncio
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ServiceValidationError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACMode

from .const import (
    DOMAIN,
    UPDATE_INTERVAL,
    UPDATE_TIMEOUT,
    CONF_DEVICE_ID,
    DEVICE_TYPE_CLIMATES,
    DEVICE_TYPE_SENSORS,
    CONF_COMPATIBILITY_OPTIONS,
    CONF_SEND_OFF_BEFORE_ON,
    DEFAULT_SEND_OFF_BEFORE_ON,
)
from .helpers import tuya_temp, tuya_mode, tuya_wind
from .api import TuyaClimateAPI, TuyaSensorAPI
from .bridge import TuyaPulsarBridge
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
        self._register_pulsar_handlers()
        self.data = {}

    def is_available(self, climate_id: str) -> bool:
        """Check if the climate device is available in the fetched data."""
        return self.data and self.data.get(climate_id) is not None

    def _get_compatibility_option(self, climate_id: str, option_key: str, default: Any) -> Any:
        """Get compatibility option value for a specific climate device."""
        climates = self.entry.options.get(DEVICE_TYPE_CLIMATES, [])
        for d in climates:
            if d.get(CONF_DEVICE_ID) == climate_id:
                return d.get(CONF_COMPATIBILITY_OPTIONS, {}).get(option_key, default)
        return default

    async def _async_ensure_off_before_on(self, infrared_id: str, climate_id: str) -> None:
        """Ensure a power-off command is sent before any command that turns the device on."""
        send_off_before_on = self._get_compatibility_option(
            climate_id, CONF_SEND_OFF_BEFORE_ON, DEFAULT_SEND_OFF_BEFORE_ON
        )
        if not send_off_before_on:
            return

        _LOGGER.debug("[%s] Sending power-off command before power-on", climate_id)
        await self._api.async_send_command(infrared_id, climate_id, "power", "0")
    
    # =========================================================================
    # PUBLIC ATOMIC COORDINATOR ACTIONS
    # =========================================================================

    async def async_turn_on(self, infrared_id: str, climate_id: str):
        """Send IR command to turn on the climate entity and update local cache."""
        await self._send_power_command(infrared_id, climate_id, "1")
        await self._async_force_update_data(climate_id, power=True)

    async def async_turn_off(self, infrared_id: str, climate_id: str):
        """Send IR command to turn off the climate entity and update local cache."""
        await self._send_power_command(infrared_id, climate_id, "0")
        await self._async_force_update_data(climate_id, power=False)

    async def async_set_temperature(self, infrared_id: str, climate_id: str, temperature: float):
        """Send IR command to set target temperature and update local cache."""
        await self._send_temperature_command(infrared_id, climate_id, temperature)
        await self._async_force_update_data(climate_id, power=True, temperature=temperature)

    async def async_set_fan_mode(self, infrared_id: str, climate_id: str, fan_mode: str):
        """Send IR command to set fan mode and update local cache."""
        await self._send_fan_mode_command(infrared_id, climate_id, fan_mode)
        await self._async_force_update_data(climate_id, power=True, fan_mode=fan_mode)

    async def async_set_hvac_mode(self, infrared_id: str, climate_id: str, hvac_mode: HVACMode, temperature: float, fan_mode: str):
        """Send a combined multi-command IR packet (Mode, Temp, Fan) and update local cache."""
        await self._send_combined_command(infrared_id, climate_id, hvac_mode, temperature, fan_mode)
        await self._async_force_update_data(climate_id, power=True, hvac_mode=hvac_mode, temperature=temperature, fan_mode=fan_mode)

    # =========================================================================
    # PUBLIC COMBINED ATOMIC FLOWS (NO UI FLICKER)
    # =========================================================================

    async def async_turn_on_with_hvac_mode(self, infrared_id: str, climate_id: str, hvac_mode: HVACMode, temperature: float, fan_mode: str):
        """Execute a combined flow: turn on the device via cloud and immediately set HVAC parameters, updating cache once."""
        _LOGGER.debug("[%s] Executing combined power-on and hvac mode configuration flow (%s)", climate_id, hvac_mode)
        
        await self._send_power_command(infrared_id, climate_id, "1")
        await self._send_combined_command(infrared_id, climate_id, hvac_mode, temperature, fan_mode)
        
        await self._async_force_update_data(climate_id, power=True, hvac_mode=hvac_mode, temperature=temperature, fan_mode=fan_mode)

    async def async_turn_on_with_temperature(self, infrared_id: str, climate_id: str, temperature: float):
        """Execute a combined flow: turn on the device via cloud and immediately set temperature, updating cache once."""
        _LOGGER.debug("[%s] Executing combined power-on and temperature configuration flow (%s)", climate_id, temperature)

        await self._send_power_command(infrared_id, climate_id, "1")
        await self._send_temperature_command(infrared_id, climate_id, temperature)

        await self._async_force_update_data(climate_id, power=True, temperature=temperature)

    async def async_turn_on_with_fan_mode(self, infrared_id: str, climate_id: str, fan_mode: str):
        """Execute a combined flow: turn on the device via cloud and immediately set fan mode, updating cache once."""
        _LOGGER.debug("[%s] Executing combined power-on and fan mode configuration flow (%s)", climate_id, fan_mode)

        await self._send_power_command(infrared_id, climate_id, "1")
        await self._send_fan_mode_command(infrared_id, climate_id, fan_mode)

        await self._async_force_update_data(climate_id, power=True, fan_mode=fan_mode)

    # =========================================================================
    # PRIVATE LOW-LEVEL COMMAND HELPERS
    # =========================================================================

    async def _send_power_command(self, infrared_id: str, climate_id: str, state: str, skip_ensure_off: bool = False) -> None:
        """Send raw power command and handle validation errors."""
        if state == "1" and not skip_ensure_off:
            await self._async_ensure_off_before_on(infrared_id, climate_id)

        _LOGGER.debug("[%s] Sending IR command to turn %s climate", climate_id, "ON" if state == "1" else "OFF")
        result = await self._api.async_send_command(infrared_id, climate_id, "power", state)
        if not result.success:
            _LOGGER.error("Failed to turn %s climate %s: %s", "on" if state == "1" else "off", climate_id, result.error_info)
            translation_key = "climate_error_turn_on" if state == "1" else "climate_error_turn_off"
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key=translation_key)

    async def _send_temperature_command(self, infrared_id: str, climate_id: str, temperature: float) -> None:
        """Send raw temperature command and handle validation errors."""
        _LOGGER.debug("[%s] Sending IR command to set temperature to %s°C", climate_id, temperature)
        result = await self._api.async_send_command(infrared_id, climate_id, "temp", tuya_temp(temperature))
        if not result.success:
            _LOGGER.error("Failed to set temperature for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_temperature")

    async def _send_fan_mode_command(self, infrared_id: str, climate_id: str, fan_mode: str) -> None:
        """Send raw fan mode command and handle validation errors."""
        _LOGGER.debug("[%s] Sending IR command to set fan mode to %s", climate_id, fan_mode)
        result = await self._api.async_send_command(infrared_id, climate_id, "wind", tuya_wind(fan_mode))
        if not result.success:
            _LOGGER.error("Failed to set fan mode for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_fan_mode")

    async def _send_combined_command(self, infrared_id: str, climate_id: str, hvac_mode: HVACMode, temperature: float, fan_mode: str) -> None:
        """Send multi-command IR packet and handle validation errors."""
        _LOGGER.debug("[%s] Sending combined IR packet -> Mode: %s, Temp: %s, Fan: %s", climate_id, hvac_mode, temperature, fan_mode)
        result = await self._api.async_send_multiple_command(
            infrared_id, climate_id, "1", tuya_mode(hvac_mode), tuya_temp(temperature), tuya_wind(fan_mode)
        )
        if not result.success:
            _LOGGER.error("Failed to set HVAC combined mode for climate %s: %s", climate_id, result.error_info)
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="climate_error_hvac_mode")

    # =========================================================================
    # PRIVATE COORDINATOR LIFECYCLE & STATE LIFTLINE HANDLERS
    # =========================================================================

    def _register_pulsar_handlers(self):
        """Register handlers for climate devices."""
        climates = self.entry.options.get(DEVICE_TYPE_CLIMATES, [])
        for d in climates:
            dev_id = d.get(CONF_DEVICE_ID)
            if self._pulsar_bridge and dev_id:
                self._pulsar_bridge.register_handler(dev_id, self._async_update_from_pulsar)

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
                    raise UpdateFailed(f"Tuya cloud reported an error fetching climates: {result.error_info}")

                return result.data
        except TimeoutError as e:
            raise UpdateFailed(f"Timeout communicating with Tuya API for climates: {e}")
        except Exception as e:
            raise UpdateFailed(f"Error communicating with Tuya API for climates: {e}")

    async def _async_force_update_data(self, climate_id, power=None, hvac_mode=None, temperature=None, fan_mode=None):
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
        entry: ConfigEntry, 
        sensor_api: TuyaSensorAPI,
        pulsar_bridge: TuyaPulsarBridge,
        custom_update_interval=UPDATE_INTERVAL
    ):
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
        self._pulsar_last_updates: dict[str, dict[str, datetime]] = {}
        self.data = {}
        self._register_pulsar_handlers()

    def _register_pulsar_handlers(self):
        """Register handlers for sensor devices."""
        sensors = self.entry.options.get(DEVICE_TYPE_SENSORS, [])
        for d in sensors:
            dev_id = d.get(CONF_DEVICE_ID)
            if self._pulsar_bridge and dev_id:
                self._pulsar_bridge.register_handler(dev_id, self._async_update_from_pulsar)

    def _update_dps_timestamp(self, device_id: str, codes: list[str]):
        """Centralized logic to mark DPS codes as fresh."""
        if device_id not in self._pulsar_last_updates:
            self._pulsar_last_updates[device_id] = {}

        now = datetime.now(timezone.utc)
        monitored_codes = TuyaSensorData.get_dps_codes()
        for code in [c for c in codes if c in monitored_codes]:
            self._pulsar_last_updates[device_id][code] = now

    def _needs_api_refresh(self, device_id: str, threshold: timedelta) -> bool:
        """Determine if API polling is needed."""
        if device_id not in self._pulsar_last_updates:
            _LOGGER.debug("[%s] No Pulsar updates recorded. API refresh needed.", device_id)
            return True

        now = datetime.now(timezone.utc)
        for code, last_ts in self._pulsar_last_updates[device_id].items():
            if (now - last_ts) > threshold:
                _LOGGER.debug("[%s] DPs code '%s' is outdated. Triggering cloud update.", device_id, code)
                return True
        
        _LOGGER.debug("[%s] All DPS codes are fresh. Skipping API refresh.", device_id)
        return False

    async def _async_update_data(self) -> dict[str, TuyaSensorData]:
        """Fetch data from Tuya API and sync timestamps."""
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
                
                for dev_id, _ in result.data.items():
                    self._update_dps_timestamp(dev_id, TuyaSensorData.get_dps_codes())
                
                updated_data = self.data.copy()
                updated_data.update(result.data)
                return updated_data
        except TimeoutError as e:
            raise UpdateFailed(f"Timeout communicating with Tuya API for sensors: {e}")
        except Exception as e:
            raise UpdateFailed(f"Error communicating with Tuya API for sensors: {e}")

    async def _async_update_from_pulsar(self, device_id: str, new_status: dict):
        """Process incoming Pulsar updates."""
        codes = [item.get("code") for item in new_status.get("status", [])]
        self._update_dps_timestamp(device_id, codes)

        current_item = self.data.get(device_id)
        if current_item and new_status.get("status"):
            _LOGGER.debug("[%s] Update sensor from Pulsar: %s", device_id, str(new_status))
            self.data[device_id] = TuyaSensorData.from_pulsar_data(current_item, new_status["status"])
            self.async_update_listeners()