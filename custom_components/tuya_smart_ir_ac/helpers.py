from homeassistant.util.unit_conversion import TemperatureConverter
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE
from .const import TUYA_HVAC_MODES, TUYA_FAN_MODES, BATTERY_LEVELS


def tuya_temp(temp):
    return str(float(temp))

def tuya_mode(hvac_mode):
    for mode, mode_name in TUYA_HVAC_MODES.items():
        if hvac_mode == mode_name:
            return mode
    return None

def tuya_wind(fan_mode):
    for mode, mode_name in TUYA_FAN_MODES.items():
        if fan_mode == mode_name:
            return mode
    return None

def hass_hvac_mode(mode):
    return TUYA_HVAC_MODES.get(mode, None)

def hass_fan_mode(wind):
    return TUYA_FAN_MODES.get(wind, None)

def hass_battery_state(battery):  
    return BATTERY_LEVELS.get(battery, None)

def hass_temperature(temperature, convert = False):
    return float(temperature) if convert is False else int(temperature) / 10.0

def valid_sensor_state(sensor_state):
    return sensor_state is not None and sensor_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE]

def valid_number_data(number_data):
    return number_data is not None and number_data.native_value is not None

def convert_temperature(value, from_unit, to_unit):
    if from_unit == to_unit or from_unit not in TemperatureConverter.VALID_UNITS or to_unit not in TemperatureConverter.VALID_UNITS:
        return value
    try:
        return TemperatureConverter.convert(value, from_unit, to_unit)
    except (ValueError, TypeError):
        return value

def convert_to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None