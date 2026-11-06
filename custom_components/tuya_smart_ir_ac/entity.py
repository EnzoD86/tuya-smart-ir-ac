from collections.abc import Iterable
from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.const import (
    UnitOfTemperature,
    ATTR_UNIT_OF_MEASUREMENT,
)
from homeassistant.components.climate.const import HVACMode
from .const import (
    DOMAIN,
    MANUFACTURER,
    CLIMATE_MODEL,
    SENSOR_MODEL,
)
from .models import (
    RuntimeData,
    TuyaClimateData,
    TuyaSensorData,
    TuyaClimateConfig,
    TuyaSensorConfig,
)
from .helpers import (
    valid_sensor_state,
    convert_temperature,
    convert_to_float,
)
from .commands import (
    ClimateCommandHandler,
)
class TuyaClimateEntity:
    """Base class for Tuya Climate entities supplying shared configuration and state logics."""

    coordinator: Any

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData, sub_entity_type: str | None = None) -> None:
        """Initialize core configuration boundaries and user preferences."""
        self._runtime_data = runtime_data
        self._config = TuyaClimateConfig.from_config_data(config_data)

        base_id = f"{self._config.infrared_id}_{self._config.climate_id}"
        self._attr_unique_id = f"{base_id}_{sub_entity_type}" if sub_entity_type else base_id
        self._attr_device_info = DeviceInfo(
            name=self._config.name,
            identifiers={(DOMAIN, base_id)},
            manufacturer=MANUFACTURER,
            model=CLIMATE_MODEL,
        )
        self._temperature_unit = UnitOfTemperature.CELSIUS
        self._last_valid_preset_hvac_mode = None
        self._command_handler = ClimateCommandHandler(
            runtime_data=runtime_data,
            config=self._config,
        )

    @property
    def available(self) -> bool:
        """Return entity availability based on the coordinator."""
        return self.coordinator.is_available(self._config.climate_id)

    def _get_climate_data(self) -> TuyaClimateData:
        """Return this device's latest data from the coordinator."""
        return self.coordinator.get_climate_data(self._config.climate_id)

    def get_preset_modes(self) -> list[str]:
        """Return the global presets available for this climate's current state."""
        climate_data = self._get_climate_data()
        return self._runtime_data.global_preset_manager.get_available_presets(
            self._config.preset_modes,
            climate_data.hvac_mode,
            climate_data.current_hvac_mode,
            self._last_valid_preset_hvac_mode,
        )

    def get_preset_mode(self) -> str:
        """Return the global preset matching this climate's current state."""
        climate_data = self._get_climate_data()
        return self._runtime_data.global_preset_manager.get_current_preset(
            climate_data.hvac_mode,
            climate_data.current_hvac_mode,
            climate_data.temperature,
            climate_data.fan_mode,
        )

    def async_track_sensor_states(self, sensors: Iterable[str] = ()) -> None:
        """Establish state tracking listeners on external reference entities."""
        if valid_sensors := [s for s in sensors if s]:
            self.async_on_remove(
                async_track_state_change_event(self.hass, valid_sensors, self._handle_sensor_state_change)
            )

    def update_preset_history(self) -> None:
        """Update the history of the last valid HVAC mode supporting presets."""
        mode = self._get_climate_data().hvac_mode
        if mode in (HVACMode.COOL, HVACMode.HEAT):
            self._last_valid_preset_hvac_mode = mode

    def get_temperature_unit_of_measurement(self) -> str:
        """Read the measurement scale symbol used by the designated temperature tracking source."""
        if self._config.temperature_sensor is not None:
            if sensor_state := self.hass.states.get(self._config.temperature_sensor):
                return sensor_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature.CELSIUS)
        return UnitOfTemperature.CELSIUS

    def get_temperature_value(self, convert: bool = False) -> float | None:
        """Extract, validate and optionally standardize environmental temperature values from source entities."""
        if self._config.temperature_sensor is None:
            return None

        sensor_state = self.hass.states.get(self._config.temperature_sensor)
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
        if self._config.humidity_sensor is None:
            return None

        sensor_state = self.hass.states.get(self._config.humidity_sensor)
        if not valid_sensor_state(sensor_state):
            return None

        return convert_to_float(sensor_state.state)

    async def async_handle_turn_on(self) -> None:
        """Delegate turning on the climate device."""
        await self._command_handler.async_handle_turn_on()

    async def async_handle_turn_off(self) -> None:
        """Delegate turning off the climate device."""
        await self._command_handler.async_handle_turn_off()

    async def async_handle_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Delegate setting the HVAC mode."""
        await self._command_handler.async_handle_set_hvac_mode(hvac_mode)

    async def async_handle_set_temperature(self, temperature: float, hvac_mode: HVACMode | None = None) -> None:
        """Delegate setting the target temperature."""
        await self._command_handler.async_handle_set_temperature(temperature, hvac_mode)

    async def async_handle_set_fan_mode(self, fan_mode: str) -> None:
        """Delegate setting the fan mode."""
        await self._command_handler.async_handle_set_fan_mode(fan_mode)

    async def async_handle_set_preset_mode(self, preset_mode: str) -> None:
        """Delegate applying the selected preset."""
        await self._command_handler.async_handle_set_preset_mode(
            preset_mode, self._last_valid_preset_hvac_mode
        )


class TuyaSensorEntity:
    """Base class for standalone environmental Temperature/Humidity sensor devices managed by this integration."""

    coordinator: Any

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData, sensor_type: str) -> None:
        """Initialize core reporting identities and linked environmental device metadata."""
        self._runtime_data = runtime_data
        self._config = TuyaSensorConfig.from_config_data(config_data, sensor_type)
        
        self._attr_unique_id = f"{self._config.device_id}_{self._config.entity_type}"
        self._attr_device_info = DeviceInfo(
            name=self._config.name,
            identifiers={(DOMAIN, self._config.device_id)},
            manufacturer=MANUFACTURER,
            model=SENSOR_MODEL,
        )

    @property
    def available(self) -> bool:
        """Check environmental sensor availability using the coordinator data cache mapping."""
        return self.coordinator.is_available(self._config.device_id)
    
    @property
    def _device_sensor_data(self) -> TuyaSensorData | None:
        """Centralized accessor to safely extract the current device's data from the coordinator cache."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._config.device_id)
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