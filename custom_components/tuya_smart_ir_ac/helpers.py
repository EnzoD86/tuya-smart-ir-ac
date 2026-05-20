from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import State
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import BATTERY_LEVELS, TUYA_FAN_MODES, TUYA_HVAC_MODES, TUYA_TEMP_UNIT


def clamp_to_boundaries(value: float, min_boundary: float, max_boundary: float) -> float:
    """Clamp a given numeric value strictly within the specified minimum and maximum configuration boundaries."""
    return max(min_boundary, min(value, max_boundary))


def convert_to_float(value: Any) -> float | None:
    """Safely convert a value to float, returning None on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def tuya_temp(temp: Any) -> str | None:
    """Safely convert temperature to Tuya string protocol format."""
    float_val = convert_to_float(temp)
    return str(float_val) if float_val is not None else None


def tuya_mode(hvac_mode: str) -> str | None:
    """Reverse map Home Assistant HVAC mode to Tuya protocol mode."""
    for mode, mode_name in TUYA_HVAC_MODES.items():
        if hvac_mode == mode_name:
            return mode
    return None


def tuya_wind(fan_mode: str) -> str | None:
    """Reverse map Home Assistant Fan mode to Tuya protocol mode."""
    for mode, mode_name in TUYA_FAN_MODES.items():
        if fan_mode == mode_name:
            return mode
    return None


def hass_hvac_mode(mode: str) -> str | None:
    """Map Tuya protocol mode to Home Assistant HVAC mode."""
    return TUYA_HVAC_MODES.get(mode)


def hass_fan_mode(wind: str) -> str | None:
    """Map Tuya protocol wind code to Home Assistant Fan mode."""
    return TUYA_FAN_MODES.get(wind)


def hass_battery_state(battery: str) -> int | str | None:
    """Map Tuya battery state code to Home Assistant battery level/percentage."""
    return BATTERY_LEVELS.get(battery)


def hass_temperature(temperature: Any, convert: bool = False) -> float | None:
    """Process incoming temperature data with optional Tuya decimal conversion safety."""
    float_val = convert_to_float(temperature)
    if float_val is None:
        return None
    return float_val if not convert else int(float_val) / 10.0


def hass_temp_unit(temp_unit: str) -> str | None:
    """Map Tuya temperature unit string to Home Assistant constant unit."""
    return TUYA_TEMP_UNIT.get(temp_unit)


def valid_sensor_state(sensor_state: State | None) -> bool:
    """Check if an external tracking sensor state is initialized, online and valid."""
    return (
        sensor_state is not None 
        and sensor_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
    )


def valid_number_data(number_data: Any) -> bool:
    """Validate that restored Home Assistant number memory data contains a legitimate value."""
    return number_data is not None and number_data.native_value is not None


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    if (
        from_unit == to_unit 
        or from_unit not in TemperatureConverter.VALID_UNITS 
        or to_unit not in TemperatureConverter.VALID_UNITS
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        return value

    return TemperatureConverter.convert(value, from_unit, to_unit)