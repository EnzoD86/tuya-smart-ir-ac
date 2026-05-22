from tuya_smart_ir_ac.models import (
    TuyaClimateData,
    TuyaGenericData,
    TuyaSensorData,
)


def test_tuya_climate_data_from_raw_data_parses_values():
    raw = {"powerOpen": True, "mode": "0", "temp": "250", "fan": "1"}
    data = TuyaClimateData.from_raw_data(raw)

    assert data.power is True
    assert data.hvac_mode is not None
    assert data.temperature == 250.0
    assert data.fan_mode is not None


def test_tuya_climate_data_from_batch_data_skips_invalid_devices():
    raw_list = [
        {"devId": "abc", "powerOpen": False, "mode": "5", "temp": "180", "fan": "0"},
        {"powerOpen": True, "mode": "0", "temp": "220", "fan": "1"},
    ]
    result = TuyaClimateData.from_batch_data(raw_list)

    assert "abc" in result
    assert len(result) == 1


def test_tuya_generic_data_from_raw_data_builds_key_list():
    raw = {"category_id": "cat1", "key_list": [{"key": "power", "key_id": "1", "key_name": "Power"}]}
    generic = TuyaGenericData.from_raw_data(raw)

    assert generic.category_id == "cat1"
    assert len(generic.key_list) == 1
    assert generic.key_list[0].key == "power"


def test_tuya_sensor_data_from_raw_data_parses_properties():
    raw = {
        "properties": [
            {"code": "temp_unit_convert", "value": "c"},
            {"code": "temp_current", "value": 235},
            {"code": "humidity_value", "value": 55},
            {"code": "battery_state", "value": "high"},
        ]
    }
    sensor = TuyaSensorData.from_raw_data(raw)

    assert sensor.temp_unit_convert == "°C"
    assert sensor.temp_current == 23.5
    assert sensor.humidity_value == 55
    assert sensor.battery_state == 100
