import logging
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.const import (
    UnitOfTemperature,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_NAME,
)
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_LOW,
    HVACMode,
)
from .const import (
    DOMAIN,
    MANUFACTURER,
    CLIMATE_MODEL,
    SENSOR_MODEL,
    CONF_INFRARED_ID,
    CONF_DEVICE_ID,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_TEMP_MIN,
    CONF_TEMP_MAX,
    CONF_TEMP_STEP,
    CONF_TEMP_UNIT,
    CONF_HVAC_MODES,
    CONF_FAN_MODES,
    CONF_HVAC_PRESETS,
    CONF_COMPATIBILITY_OPTIONS,
    CONF_HVAC_POWER_ON,
    CONF_TEMP_POWER_ON,
    CONF_FAN_POWER_ON,
    CONF_DRY_MIN_TEMP,
    CONF_DRY_MIN_FAN,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_PRECISION,
    DEFAULT_HVAC_POWER_ON,
    DEFAULT_TEMP_POWER_ON,
    DEFAULT_FAN_POWER_ON,
    DEFAULT_DRY_MIN_TEMP,
    DEFAULT_DRY_MIN_FAN,
    SUPPORTED_HVAC_MODES,
    SUPPORTED_FAN_MODES,
    PRESET_TEMP_HVAC_MODE,
    PRESET_FAN_HVAC_MODE,
    ENTITY_HVAC_MODE,
    ENTITY_FAN_MODE,
    ENTITY_TEMPERATURE_SETPOINT,
    ENTITY_CURRENT_TEMPERATURE,
    ENTITY_CURRENT_HUMIDITY,
    POWER_ON_NEVER,
    POWER_ON_ALWAYS,
    POWER_ON_ONLY_OFF,
)
from .models import RuntimeData
from .helpers import (
    valid_sensor_state,
    convert_temperature,
    convert_to_float,
)

_LOGGER = logging.getLogger(__package__)


class TuyaClimateEntity:
    """Base class for Tuya Climate entities supplying shared configuration and state logics."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData, sub_entity_type: str | None = None) -> None:
        """Initialize core configuration boundaries and user preferences."""
        self._runtime_data = runtime_data
        
        self._infrared_id = config_data.get(CONF_INFRARED_ID)
        self._climate_id = config_data.get(CONF_DEVICE_ID)
        self._name = config_data.get(CONF_NAME)
        self._temperature_sensor = config_data.get(CONF_TEMPERATURE_SENSOR)
        self._humidity_sensor = config_data.get(CONF_HUMIDITY_SENSOR)
        self._min_temp = config_data.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP)
        self._max_temp = config_data.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP)
        self._temp_step = config_data.get(CONF_TEMP_STEP, DEFAULT_PRECISION)
        self._hvac_modes = config_data.get(CONF_HVAC_MODES, SUPPORTED_HVAC_MODES)
        self._fan_modes = config_data.get(CONF_FAN_MODES, SUPPORTED_FAN_MODES)
        self._preset_temp_hvac_mode = PRESET_TEMP_HVAC_MODE in config_data.get(CONF_HVAC_PRESETS, [])
        self._preset_fan_hvac_mode = PRESET_FAN_HVAC_MODE in config_data.get(CONF_HVAC_PRESETS, [])
        
        compatibility = config_data.get(CONF_COMPATIBILITY_OPTIONS, {})
        self._hvac_power_on = compatibility.get(CONF_HVAC_POWER_ON, DEFAULT_HVAC_POWER_ON)
        self._temp_power_on = compatibility.get(CONF_TEMP_POWER_ON, DEFAULT_TEMP_POWER_ON)
        self._fan_power_on = compatibility.get(CONF_FAN_POWER_ON, DEFAULT_FAN_POWER_ON)
        self._dry_min_temp = compatibility.get(CONF_DRY_MIN_TEMP, DEFAULT_DRY_MIN_TEMP)
        self._dry_min_fan = compatibility.get(CONF_DRY_MIN_FAN, DEFAULT_DRY_MIN_FAN)

        base_id = f"{self._infrared_id}_{self._climate_id}"
        self._attr_unique_id = f"{base_id}_{sub_entity_type}" if sub_entity_type else base_id
        self._attr_device_info = DeviceInfo(
            name=self._name,
            identifiers={(DOMAIN, base_id)},
            manufacturer=MANUFACTURER,
            model=CLIMATE_MODEL,
        )

    @property
    def available(self) -> bool:
        """Return entity availability based on the coordinator."""
        return self.coordinator.is_available(self._climate_id)


    # =========================================================================
    # CENTRAL SHARED DATA ACCESSORS & COORDINATOR ENCAPSULATION
    # =========================================================================

    @property
    def _device_climate_data(self) -> Any | None:
        """Centralized accessor to safely extract the current device's data from the coordinator cache."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._climate_id)
        return None

    @property
    def _current_hvac_mode(self) -> HVACMode:
        """Centralized accessor to fetch the current active HVAC mode from the coordinator state."""
        if (data := self._device_climate_data) and data.hvac_mode:
            return data.hvac_mode if data.power else HVACMode.OFF
        return HVACMode.OFF

    def get_hvac_preset_temperature(self, hvac_mode: HVACMode) -> float | None:
        """Extract the target temperature value stored for a specific operational mode."""
        device_presets = self._runtime_data.hvac_presets.setdefault(self._climate_id, {})
        return device_presets.get(f"temp_{hvac_mode.value}")

    def set_hvac_preset_temperature(self, hvac_mode: str, value: float) -> None:
        """Commit a target temperature value for a specific operational mode."""
        device_presets = self._runtime_data.hvac_presets.setdefault(self._climate_id, {})
        device_presets[f"temp_{hvac_mode}"] = value

    def get_hvac_preset_fan_mode(self) -> str | None:
        """Extract the fallback ventilation option stored for the device."""
        device_presets = self._runtime_data.hvac_presets.setdefault(self._climate_id, {})
        return device_presets.get("fan_preset")

    def set_hvac_preset_fan_mode(self, option: str) -> None:
        """Commit a fallback ventilation option for the device."""
        device_presets = self._runtime_data.hvac_presets.setdefault(self._climate_id, {})
        device_presets["fan_preset"] = option

    def async_track_sensor_states(self, sensors=()) -> None:
        """Establish state tracking listeners on external reference entities."""
        if valid_sensors := [s for s in sensors if s]:
            self.async_on_remove(
                async_track_state_change_event(self.hass, valid_sensors, self._handle_sensor_state_change)
            )

    # =========================================================================
    # BUSINESS LOGIC HELPER METHODS
    # =========================================================================

    def get_hvac_temperature(self, hvac_mode: HVACMode) -> float:
        """Get the correct target temperature for the selected HVAC mode, using presets or coordinator data."""
        if (preset_temp := self.get_hvac_preset_temperature(hvac_mode)) is not None and self._preset_temp_hvac_mode:
            return preset_temp

        if hvac_mode is HVACMode.DRY and self._dry_min_temp:
            return DEFAULT_MIN_TEMP

        current_temp = (DEFAULT_MAX_TEMP - DEFAULT_MIN_TEMP) / 2
        if (data := self._device_climate_data) and data.temperature:
            current_temp = data.temperature

        if current_temp < self._min_temp:
            return self._min_temp

        return current_temp

    def get_hvac_fan_mode(self, hvac_mode: HVACMode) -> str:
        """Get the correct fan mode for the selected HVAC mode, using presets or coordinator data."""
        if hvac_mode is HVACMode.DRY:
            return FAN_LOW if self._dry_min_fan else FAN_AUTO

        if self._preset_fan_hvac_mode and (preset_fan := self.get_hvac_preset_fan_mode()) is not None:
            return preset_fan

        current_fan = FAN_AUTO
        if (data := self._device_climate_data) and data.fan_mode:
            current_fan = data.fan_mode

        return current_fan

    def get_hvac_power_on(self, hvac_mode_previous_state: HVACMode) -> bool:
        """Check whether an explicit power command must precede a mode alteration."""
        return self.get_power_on(self._hvac_power_on, hvac_mode_previous_state)

    def get_temp_power_on(self, hvac_mode_previous_state: HVACMode) -> bool:
        """Check whether an explicit power command must precede a temperature shift."""
        return self.get_power_on(self._temp_power_on, hvac_mode_previous_state)

    def get_fan_power_on(self, hvac_mode_previous_state: HVACMode) -> bool:
        """Check whether an explicit power command must precede a ventilation shift."""
        return self.get_power_on(self._fan_power_on, hvac_mode_previous_state)

    def get_power_on(self, power_on_setting: str, hvac_mode_previous_state: HVACMode) -> bool:
        """Match hardware policy definitions against current machine states to verify power requirements."""
        if power_on_setting == POWER_ON_NEVER:
            return False
        if power_on_setting == POWER_ON_ALWAYS:
            return True
        if power_on_setting == POWER_ON_ONLY_OFF and hvac_mode_previous_state is HVACMode.OFF:
            return True
        return False

    def get_temperature_unit_of_measurement(self) -> str:
        """Read the measurement scale symbol used by the designated environmental tracking source."""
        if self._temperature_sensor is not None:
            if sensor_state := self.hass.states.get(self._temperature_sensor):
                return sensor_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature.CELSIUS)
        return UnitOfTemperature.CELSIUS

    def get_temperature_value(self, convert: bool = False) -> float | None:
        """Extract, validate and optionally standardize environmental temperature values from source entities."""
        if self._temperature_sensor is None:
            return None

        sensor_state = self.hass.states.get(self._temperature_sensor)
        if not valid_sensor_state(sensor_state):
            return None
        
        value = convert_to_float(sensor_state.state)
        if value is None:
            return None

        if convert:
            unit = sensor_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            return convert_temperature(value, unit, self.get_temperature_unit_of_measurement())

        return value

    def get_humidity_value(self) -> float | None:
        """Extract and validate relative environmental humidity metrics from source entities."""
        if self._humidity_sensor is None:
            return None

        sensor_state = self.hass.states.get(self._humidity_sensor)
        if not valid_sensor_state(sensor_state):
            return None

        return convert_to_float(sensor_state.state)

    # =========================================================================
    # CENTRALIZED SERVICE CALL HANDLERS
    # =========================================================================

    async def async_execute_turn_on(self) -> None:
        """Turn on the climate device power via coordinator service."""
        _LOGGER.info("Sending power on command for device %s", self._name)
        await self.coordinator.async_turn_on(self._infrared_id, self._climate_id)

    async def async_execute_turn_off(self) -> None:
        """Turn off the climate device power via coordinator service."""
        _LOGGER.info("Sending power off command for device %s", self._name)
        await self.coordinator.async_turn_off(self._infrared_id, self._climate_id)

    async def async_execute_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode for the climate device via coordinator service."""
        _LOGGER.info("Setting hvac mode to %s for device %s", hvac_mode, self._name)

        if hvac_mode is HVACMode.OFF:
            await self.coordinator.async_turn_off(self._infrared_id, self._climate_id)
        else:
            temperature = self.get_hvac_temperature(hvac_mode)
            fan_mode = self.get_hvac_fan_mode(hvac_mode)

            if self.get_hvac_power_on(self._current_hvac_mode):
                await self.coordinator.async_turn_on(self._infrared_id, self._climate_id)

            await self.coordinator.async_set_hvac_mode(
                self._infrared_id, self._climate_id, hvac_mode, temperature, fan_mode
            )

    async def async_execute_set_temperature(self, value: float, hvac_mode: HVACMode | None = None) -> None:
        """Set target temperature for the climate device via coordinator service."""
        if hvac_mode is not None:
            if hvac_mode is HVACMode.OFF:
                _LOGGER.info("Turning off climate control for device %s", self._name)
                await self.coordinator.async_turn_off(self._infrared_id, self._climate_id)
            else:
                _LOGGER.info("Setting hvac mode to %s and target temperature to %s for device %s", hvac_mode, value, self._name)
                fan_mode = self.get_hvac_fan_mode(hvac_mode)

                if self.get_hvac_power_on(self._current_hvac_mode):
                    await self.coordinator.async_turn_on(self._infrared_id, self._climate_id)
                    
                await self.coordinator.async_set_hvac_mode(
                    self._infrared_id, self._climate_id, hvac_mode, value, fan_mode
                )
        else:
            _LOGGER.info("Setting target temperature to %s for device %s", value, self._name)

            if self.get_temp_power_on(self._current_hvac_mode):
                await self.coordinator.async_turn_on(self._infrared_id, self._climate_id)
                
            await self.coordinator.async_set_temperature(self._infrared_id, self._climate_id, value)

    async def async_execute_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode for the climate device via coordinator service."""
        _LOGGER.info("Setting fan mode to %s for device %s", fan_mode, self._name)

        if self.get_fan_power_on(self._current_hvac_mode):
            await self.coordinator.async_turn_on(self._infrared_id, self._climate_id)

        await self.coordinator.async_set_fan_mode(self._infrared_id, self._climate_id, fan_mode)


class TuyaSensorEntity:
    """Base class for standalone sensor devices managed by this integration."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData, sensor_type: str) -> None:
        """Initialize core reporting identities and linked climate device metadata."""
        self._runtime_data = runtime_data
        self._sensor_type = sensor_type
        
        self._device_id = config_data.get(CONF_DEVICE_ID)
        self._name = config_data.get(CONF_NAME)
        self._unit_of_measurement = config_data.get(CONF_TEMP_UNIT, UnitOfTemperature.CELSIUS)
        
        self._attr_unique_id = f"{self._device_id}_{self._sensor_type}"
        self._attr_device_info = DeviceInfo(
            name=self._name,
            identifiers={(DOMAIN, self._device_id)},
            manufacturer=MANUFACTURER,
            model=SENSOR_MODEL,
        )

    @property
    def available(self) -> bool:
        """Check availability using the coordinator data cache mapping."""
        return self.coordinator.is_available(self._device_id)