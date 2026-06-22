from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.const import (
    UnitOfTemperature,
    Platform,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_NAME,
)
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_LOW,
    PRESET_NONE,
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
    CONF_PRESET_MODES,
    CONF_HVAC_PRESETS,
    CONF_COMPATIBILITY_OPTIONS,
    CONF_HVAC_POWER_ON,
    CONF_TEMP_POWER_ON,
    CONF_FAN_POWER_ON,
    CONF_DRY_MIN_TEMP,
    CONF_DRY_MIN_FAN,
    CONF_CUSTOM_POWER_ON,
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
    POWER_ON_NEVER,
    POWER_ON_ALWAYS,
    POWER_ON_ONLY_OFF,
)
from .models import (
    RuntimeData,
    TuyaClimateData,
    TuyaSensorData
)
from .helpers import (
    valid_sensor_state,
    convert_temperature,
    convert_to_float,
)


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
        self._preset_modes = config_data.get(CONF_PRESET_MODES, [])
        self._preset_temp_hvac_mode = PRESET_TEMP_HVAC_MODE in config_data.get(CONF_HVAC_PRESETS, [])
        self._preset_fan_hvac_mode = PRESET_FAN_HVAC_MODE in config_data.get(CONF_HVAC_PRESETS, [])
        compatibility = config_data.get(CONF_COMPATIBILITY_OPTIONS, {})
        self._hvac_power_on = compatibility.get(CONF_HVAC_POWER_ON, DEFAULT_HVAC_POWER_ON)
        self._temp_power_on = compatibility.get(CONF_TEMP_POWER_ON, DEFAULT_TEMP_POWER_ON)
        self._fan_power_on = compatibility.get(CONF_FAN_POWER_ON, DEFAULT_FAN_POWER_ON)
        self._dry_min_temp = compatibility.get(CONF_DRY_MIN_TEMP, DEFAULT_DRY_MIN_TEMP)
        self._dry_min_fan = compatibility.get(CONF_DRY_MIN_FAN, DEFAULT_DRY_MIN_FAN)
        self._custom_power_on = compatibility.get(CONF_CUSTOM_POWER_ON)

        base_id = f"{self._infrared_id}_{self._climate_id}"
        self._attr_unique_id = f"{base_id}_{sub_entity_type}" if sub_entity_type else base_id
        self._attr_device_info = DeviceInfo(
            name=self._name,
            identifiers={(DOMAIN, base_id)},
            manufacturer=MANUFACTURER,
            model=CLIMATE_MODEL,
        )
        self._temperature_unit = UnitOfTemperature.CELSIUS
        self._last_valid_preset_hvac_mode = None

    @property
    def available(self) -> bool:
        """Return entity availability based on the coordinator."""
        return self.coordinator.is_available(self._climate_id)

    # =========================================================================
    # CENTRAL SHARED DATA ACCESSORS & COORDINATOR ENCAPSULATION
    # =========================================================================

    @property
    def _device_climate_data(self) -> TuyaClimateData | None:
        """Centralized accessor to safely extract the current device's data from the coordinator cache."""
        if self.coordinator and self.coordinator.data:
            return self.coordinator.data.get(self._climate_id, TuyaClimateData())
        return TuyaClimateData()

    @property
    def _real_hvac_mode(self) -> HVACMode:
        """Centralized accessor to fetch the current active HVAC mode from the coordinator state."""
        data = self._device_climate_data
        return data.hvac_mode

    @property
    def _current_hvac_mode(self) -> HVACMode:
        """Centralized accessor to fetch the current active HVAC mode."""
        data = self._device_climate_data
        return data.hvac_mode if data.power else HVACMode.OFF

    @property
    def _current_target_temperature(self) -> float:
        """Centralized accessor to safely fetch the current target temperature."""
        return self._device_climate_data.temperature

    @property
    def _current_fan_mode(self) -> str:
        """Centralized accessor to safely fetch the current fan mode."""
        return self._device_climate_data.fan_mode

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

    def update_preset_history(self) -> None:
        """Update the history of the last valid HVAC mode supporting presets."""
        mode = self._real_hvac_mode
        if mode in (HVACMode.COOL, HVACMode.HEAT):
            self._last_valid_preset_hvac_mode = mode

    # =========================================================================
    # BUSINESS LOGIC HELPER METHODS
    # =========================================================================

    def get_hvac_temperature(self, hvac_mode: HVACMode) -> float:
        """Get the correct target temperature for the selected HVAC mode, using presets or coordinator data."""
        if self._preset_temp_hvac_mode and (preset_temp := self.get_hvac_preset_temperature(hvac_mode)) is not None:
            return preset_temp

        if hvac_mode is HVACMode.DRY and self._dry_min_temp:
            return DEFAULT_MIN_TEMP

        current_temp = self._current_target_temperature

        if current_temp < self._min_temp:
            return self._min_temp

        return current_temp

    def get_hvac_fan_mode(self, hvac_mode: HVACMode) -> str:
        """Get the correct fan mode for the selected HVAC mode, using presets or coordinator data."""
        if hvac_mode is HVACMode.DRY:
            return FAN_LOW if self._dry_min_fan else FAN_AUTO

        if self._preset_fan_hvac_mode and (preset_fan := self.get_hvac_preset_fan_mode()) is not None:
            return preset_fan

        return self._current_fan_mode

    def get_hvac_power_on(self, hvac_mode_previous_state: HVACMode) -> bool:
        """Check whether an explicit power command must precede a mode alteration."""
        if self._custom_power_on and hvac_mode_previous_state is HVACMode.OFF:
            return True
        return self.get_power_on(self._hvac_power_on, hvac_mode_previous_state)

    def get_temp_power_on(self, hvac_mode_previous_state: HVACMode) -> bool:
        """Check whether an explicit power command must precede a temperature shift."""
        if self._custom_power_on and hvac_mode_previous_state is HVACMode.OFF:
            return True
        return self.get_power_on(self._temp_power_on, hvac_mode_previous_state)

    def get_fan_power_on(self, hvac_mode_previous_state: HVACMode) -> bool:
        """Check whether an explicit power command must precede a ventilation shift."""
        if self._custom_power_on and hvac_mode_previous_state is HVACMode.OFF:
            return True
        return self.get_power_on(self._fan_power_on, hvac_mode_previous_state)

    @property
    def _is_custom_power_on_scene(self) -> bool:
        """Return True if the custom power-on action is a scene."""
        return bool(self._custom_power_on and self._custom_power_on.startswith("scene."))

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
        """Read the measurement scale symbol used by the designated temperature tracking source."""
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
            return convert_temperature(value, unit, self._temperature_unit)

        return value

    def get_humidity_value(self) -> float | None:
        """Extract and validate relative environmental humidity metrics from source entities."""
        if self._humidity_sensor is None:
            return None

        sensor_state = self.hass.states.get(self._humidity_sensor)
        if not valid_sensor_state(sensor_state):
            return None

        return convert_to_float(sensor_state.state)

    def get_preset_modes(self) -> str:
        """Return the list of available preset modes based on current HVAC mode."""    
        global_presets = self._runtime_data.global_presets

        if not global_presets or not self._preset_modes:
            return None

        current_mode = self._real_hvac_mode
        if self._last_valid_preset_hvac_mode and self.hvac_mode is HVACMode.OFF:
            current_mode = self._last_valid_preset_hvac_mode

        available_presets = [PRESET_NONE]

        for preset_name in self._preset_modes:
            hvac_configs = global_presets.get(preset_name)
            if hvac_configs and current_mode in hvac_configs:
                available_presets.append(preset_name)

        return available_presets
    
    def get_preset_mode(self) -> str:
        """Return the active preset matching real-time device configurations."""        
        if self._current_hvac_mode is HVACMode.OFF:
            return PRESET_NONE

        for preset_name, mode_configs in self._runtime_data.global_presets.items():
            if self._real_hvac_mode not in mode_configs:
                continue

            if mode_config := mode_configs.get(self._real_hvac_mode):
                if mode_config.get("temp") == self._current_target_temperature and mode_config.get("fan") == self._current_fan_mode:
                    return preset_name

        return PRESET_NONE

    # =========================================================================
    # CENTRALIZED SERVICE CALL HANDLERS
    # =========================================================================

    async def async_handle_turn_on(self) -> None:
        """Turn on the climate device power via coordinator service."""
        await self._async_trigger_custom_on_if_configured()
        if self._is_custom_power_on_scene:
            await self.coordinator._async_force_update_data(self._climate_id, power=True)
        else:
            await self.coordinator.async_turn_on(self._infrared_id, self._climate_id)

    async def async_handle_turn_off(self) -> None:
        """Turn off the climate device power via coordinator service."""
        await self.coordinator.async_turn_off(self._infrared_id, self._climate_id)

    async def async_handle_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode for the climate device via coordinator service."""
        if hvac_mode is HVACMode.OFF:
            await self.coordinator.async_turn_off(self._infrared_id, self._climate_id)
            return

        temperature = self.get_hvac_temperature(hvac_mode)
        fan_mode = self.get_hvac_fan_mode(hvac_mode)

        if self.get_hvac_power_on(self._current_hvac_mode):
            await self._async_trigger_custom_on_if_configured()
            if self._is_custom_power_on_scene:
                await self.coordinator.async_set_hvac_mode(
                    self._infrared_id, self._climate_id, hvac_mode, temperature, fan_mode, skip_ensure_off=True
                )
            else:
                await self.coordinator.async_turn_on_with_hvac_mode(
                    self._infrared_id, self._climate_id, hvac_mode, temperature, fan_mode
                )
        else:
            await self.coordinator.async_set_hvac_mode(
                self._infrared_id, self._climate_id, hvac_mode, temperature, fan_mode
            )

    async def async_handle_set_temperature(self, value: float, hvac_mode: HVACMode | None = None) -> None:
        """Set target temperature for the climate device via coordinator service."""
        if hvac_mode is not None:
            if hvac_mode is HVACMode.OFF:
                await self.coordinator.async_turn_off(self._infrared_id, self._climate_id)
            else:
                fan_mode = self.get_hvac_fan_mode(hvac_mode)

                if self.get_hvac_power_on(self._current_hvac_mode):
                    await self._async_trigger_custom_on_if_configured()
                    if self._is_custom_power_on_scene:
                        await self.coordinator.async_set_hvac_mode(
                            self._infrared_id, self._climate_id, hvac_mode, value, fan_mode, skip_ensure_off=True
                        )
                    else:
                        await self.coordinator.async_turn_on_with_hvac_mode(
                            self._infrared_id, self._climate_id, hvac_mode, value, fan_mode
                        )
                else:
                    await self.coordinator.async_set_hvac_mode(
                        self._infrared_id, self._climate_id, hvac_mode, value, fan_mode
                    )
        else:
            if self.get_temp_power_on(self._current_hvac_mode):
                await self._async_trigger_custom_on_if_configured()
                if self._is_custom_power_on_scene:
                    await self.coordinator.async_set_temperature(
                        self._infrared_id, self._climate_id, value, skip_ensure_off=True
                    )
                else:
                    await self.coordinator.async_turn_on_with_temperature(
                        self._infrared_id, self._climate_id, value
                    )
            else:
                await self.coordinator.async_set_temperature(
                    self._infrared_id, self._climate_id, value
                )

    async def async_handle_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode for the climate device via coordinator service."""
        if self.get_fan_power_on(self._current_hvac_mode):
            await self._async_trigger_custom_on_if_configured()
            if self._is_custom_power_on_scene:
                await self.coordinator.async_set_fan_mode(
                    self._infrared_id, self._climate_id, fan_mode, skip_ensure_off=True
                )
            else:
                await self.coordinator.async_turn_on_with_fan_mode(
                    self._infrared_id, self._climate_id, fan_mode
                )
        else:
            await self.coordinator.async_set_fan_mode(
                self._infrared_id, self._climate_id, fan_mode
            )

    async def async_handle_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode for the climate device."""
        
        if preset_mode == PRESET_NONE:
            return

        if (preset_config := self._runtime_data.global_presets.get(preset_mode)) is not None:
            target_mode = self._real_hvac_mode

            if self._last_valid_preset_hvac_mode and self._current_hvac_mode is HVACMode.OFF:
                target_mode = self._last_valid_preset_hvac_mode

            if target_mode not in preset_config:
                return

            mode_config = preset_config.get(target_mode)
            target_temp = mode_config.get("temp")
            target_fan = mode_config.get("fan")

            if self.get_hvac_power_on(self._current_hvac_mode):
                await self._async_trigger_custom_on_if_configured()
                if self._is_custom_power_on_scene:
                    await self.coordinator.async_set_hvac_mode(
                        self._infrared_id, 
                        self._climate_id, 
                        target_mode,
                        target_temp, 
                        target_fan,
                        skip_ensure_off=True
                    )
                else:
                    await self.coordinator.async_turn_on_with_hvac_mode(
                        self._infrared_id, 
                        self._climate_id, 
                        target_mode,
                        target_temp, 
                        target_fan
                    )
            else:
                await self.coordinator.async_set_hvac_mode(
                    self._infrared_id, 
                    self._climate_id, 
                    target_mode,
                    target_temp, 
                    target_fan
                )

    async def _async_trigger_custom_on_if_configured(self) -> None:
        """Trigger the custom hardware alternative power-on button or scene if configured."""
        if not self._custom_power_on:
            return

        domain = self._custom_power_on.split(".", 1)[0]
        if domain == "scene":
            service = "turn_on"
        elif domain == "button":
            service = "press"
        else:
            _LOGGER.error("[%s] Unsupported custom power-on entity domain: %s", self._climate_id, domain)
            return

        await self.hass.services.async_call(
            domain=domain,
            service=service,
            service_data={"entity_id": self._custom_power_on},
            blocking=True
        )


class TuyaSensorEntity:
    """Base class for standalone environmental Temperature/Humidity sensor devices managed by this integration."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData, sensor_type: str) -> None:
        """Initialize core reporting identities and linked environmental device metadata."""
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
        """Check environmental sensor availability using the coordinator data cache mapping."""
        return self.coordinator.is_available(self._device_id)
    
    @property
    def _device_sensor_data(self) -> TuyaSensorData | None:
        """Centralized accessor to safely extract the current device's data from the coordinator cache."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._device_id)
        return TuyaSensorData()
    
    @property
    def _current_temperature(self) -> float:
        """Centralized accessor to safely fetch the current temperature."""
        return self._device_sensor_data.temp_current
    
    @property
    def _current_humidity(self) -> float:
        """Centralized accessor to safely fetch the current humidity."""
        return self._device_sensor_data.humidity_value
    
    @property
    def _battery_state(self) -> float:
        """Centralized accessor to safely fetch the battery state."""
        return self._device_sensor_data.battery_state