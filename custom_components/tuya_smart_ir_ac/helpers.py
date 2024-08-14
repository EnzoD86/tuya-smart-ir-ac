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