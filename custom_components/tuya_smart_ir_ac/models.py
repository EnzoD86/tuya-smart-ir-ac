from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from .tuya_connector import TuyaOpenAPI

if TYPE_CHECKING:
    from .coordinator import TuyaClimateCoordinator, TuyaSensorCoordinator
    from .manager import TuyaIRManager

from .helpers import (
    hass_battery_state,
    hass_fan_mode,
    hass_hvac_mode,
    hass_temp_unit,
    hass_temperature,
)

# Custom type alias linking Home Assistant ConfigEntry to our RuntimeData container
type HubConfigEntry = ConfigEntry[RuntimeData]


@dataclass
class RuntimeData:
    """Isolated, thread-safe runtime data context unique to each individual Hub ConfigEntry."""
    client: TuyaOpenAPI
    climate_coordinator: TuyaClimateCoordinator | None = None
    sensor_coordinator: TuyaSensorCoordinator | None = None
    ir_manager: TuyaIRManager | None = None
    hvac_presets: dict[str, Any] = field(default_factory=dict)


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


@dataclass
class TuyaClimateData:
    """Domain model representing the operational state of an Infrared Air Conditioner."""
    power: bool | None = None
    hvac_mode: str | None = None
    temperature: float | None = None
    fan_mode: str | None = None

    @classmethod
    def from_raw_data(cls, data: dict[str, Any]) -> TuyaClimateData:
        """Parse raw single device operational state from Tuya Cloud into domain model."""
        return cls(
            power=data.get("powerOpen"),
            hvac_mode=hass_hvac_mode(data.get("mode")),
            temperature=hass_temperature(data.get("temp")),
            fan_mode=hass_fan_mode(data.get("fan")),
        )

    @classmethod
    def from_batch_data(cls, raw_list: list[dict[str, Any]]) -> dict[str, TuyaClimateData]:
        """Parse a raw batch list response from Tuya Cloud into a typed dictionary mapped by device ID."""
        devices = {}
        for data in raw_list:
            dev_id = data.get("devId")
            if dev_id:
                devices[dev_id] = cls.from_raw_data(data)
        return devices


@dataclass
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


@dataclass
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


@dataclass
class TuyaSensorData:
    """Domain model tracking environmental telemetry data from standalone multi-sensors."""
    temp_unit_convert: str | None = None
    temp_current: float | None = None
    humidity_value: int | None = None
    battery_state: str | None = None

    @classmethod
    def from_raw_data(cls, data: dict[str, Any]) -> TuyaSensorData:
        """Extract and sanitize variable length property payload arrays into a fixed type schema."""
        properties = data.get("properties", [])
        prop_map = {p.get("code"): p.get("value") for p in properties if "code" in p}

        return cls(
            temp_unit_convert=hass_temp_unit(prop_map.get("temp_unit_convert")),
            temp_current=hass_temperature(prop_map.get("temp_current"), convert=True),
            humidity_value=prop_map.get("humidity_value"),
            battery_state=hass_battery_state(prop_map.get("battery_state")),
        )