from homeassistant.components.climate.const import (
    HVACMode
)
from .const import (
    TUYA_HVAC_MODES,
    TUYA_FAN_MODES
)


def filter_set_temperature(func):
    def func_wrapper(self, infrared_id, climate_id, temp):
        return func(self, infrared_id, climate_id, tuya_temp(temp))
    return func_wrapper

def filter_set_fan_mode(func):
    def func_wrapper(self, infrared_id, climate_id, wind):
        return func(self, infrared_id, climate_id, tuya_wind(wind))
    return func_wrapper

def filter_set_hvac_mode(func):
    def func_wrapper(self, infrared_id, climate_id, mode, temp, wind):
        return func(self, infrared_id, climate_id, tuya_mode(mode), tuya_temp(temp), tuya_wind(wind))
    return func_wrapper

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

def hass_temperature(temperature):
    return float(temperature)

def hass_fan_mode(wind):
    return TUYA_FAN_MODES.get(wind, None)

def hass_hvac_mode_v1(power, mode):
    return TUYA_HVAC_MODES.get(mode, None) if power else HVACMode.OFF 
    
def hass_hvac_mode_v2(power, mode):
    return TUYA_HVAC_MODES.get(mode, None) if power == "1" else HVACMode.OFF 