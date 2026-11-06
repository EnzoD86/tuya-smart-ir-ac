from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import cache
from typing import Any, ClassVar, TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import CONF_NAME, UnitOfTemperature

from .const import (
    CONF_COMPATIBILITY_OPTIONS,
    CONF_CUSTOM_POWER_ON,
    CONF_DEVICE_ID,
    CONF_DRY_MIN_FAN,
    CONF_DRY_MIN_TEMP,
    CONF_FAN_MODES,
    CONF_FAN_POWER_ON,
    CONF_HUMIDITY_SENSOR,
    CONF_HVAC_MODES,
    CONF_HVAC_PRESETS,
    CONF_HVAC_POWER_ON,
    CONF_INFRARED_ID,
    CONF_PRESET_MODES,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    CONF_TEMP_POWER_ON,
    CONF_TEMP_STEP,
    CONF_TEMP_UNIT,
    CONF_TEMPERATURE_SENSOR,
    DEFAULT_DRY_MIN_FAN,
    DEFAULT_DRY_MIN_TEMP,
    DEFAULT_FAN_POWER_ON,
    DEFAULT_HVAC_POWER_ON,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_PRECISION,
    DEFAULT_TEMP_POWER_ON,
    DEFAULT_POWER,
    DEFAULT_HVAC_MODE,
    DEFAULT_TEMPERATURE,
    DEFAULT_FAN_MODE,
    PRESET_FAN_HVAC_MODE,
    PRESET_TEMP_HVAC_MODE,
    SUPPORTED_FAN_MODES,
    SUPPORTED_HVAC_MODES,
    TEMP_UNIT_CONVERT_DPS,
    TEMP_CURRENT_DPS,
    HUMIDITY_VALUE_DPS,
    BATTERY_STATE_DPS,
)
from .helpers import (
    hass_battery_state,
    hass_fan_mode,
    hass_hvac_mode,
    hass_temp_unit,
    hass_temperature,
    get_val,
    normalize_tuya_payload,
)

if TYPE_CHECKING:
    from .coordinator import TuyaClimateCoordinator, TuyaSensorCoordinator
    from .manager import TuyaIRManager
    from .connector import TuyaConnector
    from .presets import GlobalPresetManager, HvacModePresetManager

type HubConfigEntry = ConfigEntry[RuntimeData]
type GlobalPresets = dict[str, dict[HVACMode, GlobalClimatePresetData]]


@dataclass(frozen=True)
class RuntimeData:
    """Isolated, thread-safe runtime data context unique to each individual Hub ConfigEntry."""
    connector: TuyaConnector
    climate_coordinator: TuyaClimateCoordinator
    sensor_coordinator: TuyaSensorCoordinator
    ir_manager: TuyaIRManager
    global_preset_manager: GlobalPresetManager
    hvac_mode_preset_manager: HvacModePresetManager


@dataclass(frozen=True)
class GlobalClimatePresetData:
    """Typed settings for one HVAC mode within a global preset."""

    temperature: float
    fan_mode: str


@dataclass(frozen=True)
class GlobalPresetSelectionData:
    """Resolved global preset settings for the applicable HVAC mode."""

    hvac_mode: HVACMode
    temperature: float
    fan_mode: str


@dataclass
class HvacModePresetData:
    """Default temperature and fan settings for HVAC mode changes."""

    temperatures: dict[HVACMode, float] = field(default_factory=dict)
    fan_mode: str | None = None


@dataclass(frozen=True)
class TuyaAPIResult:
    """Universal immutable container wrapping any raw or parsed response from the Tuya API layer."""
    success: bool
    data: Any = None
    error_code: str | int | None = None
    error_msg: str | None = None

    @property
    def error_info(self) -> str:
        """Return a formatted error string suitable for logging and UI placeholder injection."""
        if self.error_code or self.error_msg:
            return f"Code {self.error_code or 'Unknown'}: {self.error_msg or 'No message'}"
        return ""



@dataclass(frozen=True)
class TuyaClimateData:
    """Domain model representing the operational state of an Infrared Air Conditioner."""
    power: bool = DEFAULT_POWER
    hvac_mode: HVACMode = DEFAULT_HVAC_MODE
    temperature: float = DEFAULT_TEMPERATURE
    fan_mode: str = DEFAULT_FAN_MODE

    @property
    def current_hvac_mode(self) -> HVACMode:
        """Return the active mode, or OFF when the device is powered down."""
        return self.hvac_mode if self.power else HVACMode.OFF

    @classmethod
    def from_raw_data(cls, data: dict[str, Any]) -> TuyaClimateData:
        """Parse raw single device operational state from Tuya Cloud into domain model."""
        raw_power = data.get("power")
        raw_hvac_mode = hass_hvac_mode(data.get("mode"))
        raw_temperature = hass_temperature(data.get("temp"))
        raw_fan_mode = hass_fan_mode(data.get("wind"))

        return cls(
            power=get_val(raw_power, DEFAULT_POWER),
            hvac_mode=get_val(raw_hvac_mode, DEFAULT_HVAC_MODE),
            temperature=get_val(raw_temperature, DEFAULT_TEMPERATURE),
            fan_mode=get_val(raw_fan_mode, DEFAULT_FAN_MODE),
        )

    @classmethod
    def from_batch_data(cls, raw_list: list[dict[str, Any]]) -> dict[str, TuyaClimateData]:
        """Parse a raw batch list response from Tuya Cloud into a typed dictionary mapped by device ID."""
        devices = {}
        for data in raw_list:
            dev_id = data.get("devId")
            if dev_id:
                raw_power = data.get("powerOpen")
                raw_hvac_mode = hass_hvac_mode(data.get("mode"))
                raw_temperature = hass_temperature(data.get("temp"))
                raw_fan_mode = hass_fan_mode(data.get("fan"))

                devices[dev_id] = cls(
                    power=get_val(raw_power, DEFAULT_POWER),
                    hvac_mode=get_val(raw_hvac_mode, DEFAULT_HVAC_MODE),
                    temperature=get_val(raw_temperature, DEFAULT_TEMPERATURE),
                    fan_mode=get_val(raw_fan_mode, DEFAULT_FAN_MODE),
                )
        return devices

    @classmethod
    def from_pulsar_data(cls, current_instance: TuyaClimateData, status_list: list) -> TuyaClimateData:
        """Update existing climate state from raw Pulsar status updates."""
        updates = {item["code"]: item["value"] for item in status_list}

        raw_power = updates.get("power")
        raw_hvac_mode = hass_hvac_mode(updates.get("mode"))
        raw_temperature = hass_temperature(updates.get("temp"))
        raw_fan_mode = hass_fan_mode(updates.get("wind"))

        return replace(
            current_instance,
            power=get_val(raw_power, current_instance.power),
            hvac_mode=get_val(raw_hvac_mode, current_instance.hvac_mode),
            temperature=get_val(raw_temperature, current_instance.temperature),
            fan_mode=get_val(raw_fan_mode, current_instance.fan_mode),
        )

    @classmethod
    def from_optimistic_update(
        cls,
        current_instance: TuyaClimateData,
        power: bool | None = None,
        hvac_mode: HVACMode | None = None,
        temperature: float | None = None,
        fan_mode: str | None = None,
    ) -> TuyaClimateData:
        """Return a new immutable instance with optimistic updates applied."""
        return replace(
            current_instance,
            power=power if power is not None else current_instance.power,
            hvac_mode=hvac_mode if hvac_mode is not None else current_instance.hvac_mode,
            temperature=temperature if temperature is not None else current_instance.temperature,
            fan_mode=fan_mode if fan_mode is not None else current_instance.fan_mode,
        )


@dataclass(frozen=True)
class TuyaGenericKeyData:
    """Data abstraction for a single customizable infrared command key layout."""
    key: str | None = None
    key_id: str | None = None
    key_name: str | None = None

    @classmethod
    def from_raw_data(cls, data: dict[str, Any]) -> TuyaGenericKeyData:
        """Parse a single raw key dictionary from Tuya Cloud into domain model."""
        return cls(
            key=data.get("key"),
            key_id=data.get("key_id"),
            key_name=data.get("key_name"),
        )


@dataclass(frozen=True)
class TuyaGenericData:
    """Configuration model wrapping full layout schema and command sets for generic IR peripherals."""
    category_id: str | None = None
    key_list: list[TuyaGenericKeyData] = field(default_factory=list)

    @classmethod
    def from_raw_data(cls, data: dict[str, Any]) -> TuyaGenericData:
        """Parse raw cluster configuration maps from Tuya Cloud into typed peripheral schemas."""
        raw_keys = data.get("key_list", [])
        return cls(
            category_id=data.get("category_id"),
            key_list=[TuyaGenericKeyData.from_raw_data(k) for k in raw_keys],
        )


@dataclass(frozen=True)
class TuyaSensorData:
    """Domain model tracking environmental telemetry data from standalone multi-sensors."""
    temp_unit_convert: str | None = None
    temp_current: float | None = None
    humidity_value: int | None = None
    battery_state: int | None = None

    _DPS_MAPPINGS: ClassVar[dict[str, tuple[str, ...]]] = {
        "temp_unit_convert": TEMP_UNIT_CONVERT_DPS,
        "temp_current": TEMP_CURRENT_DPS,
        "humidity_value": HUMIDITY_VALUE_DPS,
        "battery_state": BATTERY_STATE_DPS,
    }

    @classmethod
    def from_raw_data(cls, data: dict[str, Any]) -> TuyaSensorData:
        """Extract and sanitize variable length property payload arrays into a fixed type schema."""
        prop_map = normalize_tuya_payload(data.get("properties", []), mapping=cls.get_flat_map())

        raw_temp_unit_convert = hass_temp_unit(prop_map.get("temp_unit_convert"))
        raw_temp_current = hass_temperature(prop_map.get("temp_current"), convert=True)
        raw_humidity_value = prop_map.get("humidity_value")
        raw_battery_state = hass_battery_state(prop_map.get("battery_state"))

        return cls(
            temp_unit_convert=raw_temp_unit_convert,
            temp_current=raw_temp_current,
            humidity_value=raw_humidity_value,
            battery_state=raw_battery_state,
        )

    @classmethod
    def from_pulsar_data(cls, current_instance: TuyaSensorData, status_list: list) -> TuyaSensorData:
        """Update existing sensor state from raw Pulsar status updates."""
        updates = normalize_tuya_payload(status_list, mapping=cls.get_flat_map())

        raw_temp_current = hass_temperature(updates.get("temp_current"), convert=True)
        raw_humidity_value = updates.get("humidity_value")
        raw_battery_state = hass_battery_state(updates.get("battery_state"))

        return replace(
            current_instance,
            temp_unit_convert=current_instance.temp_unit_convert,
            temp_current=get_val(raw_temp_current, current_instance.temp_current),
            humidity_value=get_val(raw_humidity_value, current_instance.humidity_value),
            battery_state=get_val(raw_battery_state, current_instance.battery_state)
        )

    @classmethod
    @cache
    def get_dps_codes(cls) -> tuple[str, ...]:
        """Return canonical names of monitored sensor entities."""
        return tuple(
            logical_name
            for logical_name in cls._DPS_MAPPINGS
            if logical_name != "temp_unit_convert"
        )

    @classmethod
    @cache
    def get_flat_map(cls) -> dict[str, str]:
        """Returns the flat mapping for non-standard Tuya DP codes."""
        return {
            raw_code: logical_name
            for logical_name, raw_codes in cls._DPS_MAPPINGS.items()
            for raw_code in raw_codes
        }

    @classmethod
    def normalize_dps_codes(cls, codes: list[str]) -> set[str]:
        """Normalize raw or logical DPS names to monitored logical names."""
        flat_map = cls.get_flat_map()
        normalized_codes = {
            flat_map.get(code, code)
            for code in codes
        }
        return normalized_codes.intersection(cls.get_dps_codes())

    @classmethod
    def get_available_dps(cls, data: TuyaSensorData) -> set[str]:
        """Return monitored DPS names with values available on a sensor."""
        return {
            code
            for code in cls.get_dps_codes()
            if getattr(data, code) is not None
        }

    @classmethod
    def get_dps_from_payload(cls, payload: list[dict[str, Any]]) -> set[str]:
        """Return monitored logical DPS names found in a raw payload."""
        normalized_payload = normalize_tuya_payload(
            payload,
            mapping=cls.get_flat_map(),
        )
        return set(normalized_payload).intersection(cls.get_dps_codes())


@dataclass(frozen=True)
class TuyaClimateConfig:
    """Parsed climate device configuration shared by its entities and command handler."""

    infrared_id: str
    climate_id: str
    name: str | None
    temperature_sensor: str | None
    humidity_sensor: str | None
    min_temperature: float
    max_temperature: float
    temperature_step: float
    hvac_modes: list[HVACMode]
    fan_modes: list[str]
    preset_modes: list[str]
    temperature_hvac_preset_enabled: bool
    fan_hvac_preset_enabled: bool
    hvac_power_on: str
    temperature_power_on: str
    fan_power_on: str
    dry_min_temperature: bool
    dry_min_fan: bool
    custom_power_on: str | None

    @classmethod
    def from_config_data(cls, config_data: dict[str, Any]) -> TuyaClimateConfig:
        """Parse the climate configuration entry and apply integration defaults."""
        compatibility = config_data.get(CONF_COMPATIBILITY_OPTIONS, {})
        hvac_presets = config_data.get(CONF_HVAC_PRESETS, [])
        return cls(
            infrared_id=config_data.get(CONF_INFRARED_ID),
            climate_id=config_data.get(CONF_DEVICE_ID),
            name=config_data.get(CONF_NAME),
            temperature_sensor=config_data.get(CONF_TEMPERATURE_SENSOR),
            humidity_sensor=config_data.get(CONF_HUMIDITY_SENSOR),
            min_temperature=config_data.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP),
            max_temperature=config_data.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP),
            temperature_step=config_data.get(CONF_TEMP_STEP, DEFAULT_PRECISION),
            hvac_modes=config_data.get(CONF_HVAC_MODES, SUPPORTED_HVAC_MODES),
            fan_modes=config_data.get(CONF_FAN_MODES, SUPPORTED_FAN_MODES),
            preset_modes=config_data.get(CONF_PRESET_MODES, []),
            temperature_hvac_preset_enabled=PRESET_TEMP_HVAC_MODE in hvac_presets,
            fan_hvac_preset_enabled=PRESET_FAN_HVAC_MODE in hvac_presets,
            hvac_power_on=compatibility.get(CONF_HVAC_POWER_ON, DEFAULT_HVAC_POWER_ON),
            temperature_power_on=compatibility.get(
                CONF_TEMP_POWER_ON, DEFAULT_TEMP_POWER_ON
            ),
            fan_power_on=compatibility.get(CONF_FAN_POWER_ON, DEFAULT_FAN_POWER_ON),
            dry_min_temperature=compatibility.get(
                CONF_DRY_MIN_TEMP, DEFAULT_DRY_MIN_TEMP
            ),
            dry_min_fan=compatibility.get(CONF_DRY_MIN_FAN, DEFAULT_DRY_MIN_FAN),
            custom_power_on=compatibility.get(CONF_CUSTOM_POWER_ON),
        )


@dataclass(frozen=True)
class TuyaSensorConfig:
    """Parsed standalone sensor configuration shared by its entities."""

    device_id: str
    name: str | None
    temperature_unit: str
    entity_type: str

    @classmethod
    def from_config_data(
        cls, config_data: dict[str, Any], entity_type: str
    ) -> TuyaSensorConfig:
        """Parse standalone sensor configuration and apply its defaults."""
        return cls(
            device_id=config_data.get(CONF_DEVICE_ID),
            name=config_data.get(CONF_NAME),
            temperature_unit=config_data.get(
                CONF_TEMP_UNIT, UnitOfTemperature.CELSIUS
            ),
            entity_type=entity_type,
        )
