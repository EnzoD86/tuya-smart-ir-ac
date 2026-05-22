import math
import pytest

from tuya_smart_ir_ac.helpers import (
    clamp_to_boundaries,
    convert_to_float,
    convert_temperature,
    hass_temperature,
    hass_temp_unit,
    hass_battery_state,
    tuya_temp,
    tuya_mode,
    tuya_wind,
    valid_sensor_state,
)
from tuya_smart_ir_ac.const import TUYA_HVAC_MODES, TUYA_FAN_MODES, BATTERY_LEVELS
from homeassistant.const import UnitOfTemperature
from homeassistant.core import State


def test_clamp_to_boundaries_returns_min_when_value_too_low():
    assert clamp_to_boundaries(-5, 0, 10) == 0


def test_convert_to_float_handles_invalid_values():
    assert convert_to_float("abc") is None
    assert convert_to_float(None) is None


def test_convert_temperature_handles_same_units():
    assert convert_temperature(20, UnitOfTemperature.CELSIUS, UnitOfTemperature.CELSIUS) == 20


def test_convert_temperature_c_to_f():
    assert convert_temperature(0, UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT) == 32


def test_convert_temperature_f_to_c():
    assert convert_temperature(32, UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.CELSIUS) == 0


def test_hass_temperature_conversion():
    assert hass_temperature("250", convert=True) == 25.0


def test_tuya_temp_returns_string_from_numeric_value():
    assert tuya_temp(23) == "23.0"


def test_tuya_mode_and_wind_reverse_mapping():
    expected_hvac_key = next(key for key, value in TUYA_HVAC_MODES.items() if value == TUYA_HVAC_MODES["0"])
    assert tuya_mode(TUYA_HVAC_MODES["0"]) == "0"
    assert tuya_wind(TUYA_FAN_MODES["0"]) == "0"


def test_hass_temp_unit_maps_tuya_unit():
    assert hass_temp_unit("c") == UnitOfTemperature.CELSIUS


def test_hass_battery_state_maps_levels():
    assert hass_battery_state("high") == BATTERY_LEVELS["high"]


def test_tuya_temp_returns_none_for_invalid_value():
    assert tuya_temp("invalid") is None
    assert tuya_temp(None) is None


def test_tuya_mode_and_wind_unknown_return_none():
    assert tuya_mode("unknown") is None
    assert tuya_wind("unknown") is None


def test_hass_temperature_returns_none_for_invalid_input():
    assert hass_temperature("abc") is None
    assert hass_temperature(None, convert=True) is None


def test_convert_temperature_returns_input_for_invalid_units_and_nonfinite_values():
    assert convert_temperature(20, "invalid", UnitOfTemperature.CELSIUS) == 20
    assert math.isnan(convert_temperature(float("nan"), UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT))
    assert math.isinf(convert_temperature(float("inf"), UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT))


def test_valid_sensor_state_false_for_unavailable():
    state = State(state="unavailable", attributes={})
    assert not valid_sensor_state(state)


def test_valid_sensor_state_true_for_valid_state():
    state = State(state="20", attributes={})
    assert valid_sensor_state(state)
