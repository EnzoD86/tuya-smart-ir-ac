from homeassistant.components.climate.const import (
    HVACMode
)
from .const import (
    TUYA_HVAC_MODES,
    TUYA_FAN_MODES
)

def filter_set_temperature(func):
    def func_wrapper(self, temp):
        return func(self, tuya_temp(temp))
    return func_wrapper
    
def filter_set_fan_mode(func):
    def func_wrapper(self, wind):
        return func(self, tuya_wind(wind))
    return func_wrapper
    
def filter_set_hvac_mode(func):
    def func_wrapper(self, mode, temp, wind):
        return func(self, tuya_mode(mode), tuya_temp(temp), tuya_wind(wind))
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

def hass_power(power):
    return power == "1"

def hass_temperature(temperature):
    return float(temperature)

def hass_fan_mode(wind):
    return TUYA_FAN_MODES.get(wind, None)

def hass_hvac_mode(power, mode):
    return HVACMode.OFF if hass_power(power) is False else TUYA_HVAC_MODES.get(mode, None)