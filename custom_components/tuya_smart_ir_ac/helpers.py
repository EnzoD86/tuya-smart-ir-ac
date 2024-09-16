from homeassistant.const import (
    STATE_UNKNOWN, 
    STATE_UNAVAILABLE
)
from .const import (
    TUYA_HVAC_MODES,
    TUYA_FAN_MODES
)


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

def hass_temperature(temperature):
    return float(temperature)

def valid_sensor_state(sensor_state):
    return sensor_state is not None and sensor_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE]

def valid_number_data(number_data):
    return number_data is not None and number_data.native_value is not None