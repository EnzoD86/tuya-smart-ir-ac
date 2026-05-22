import types

from tuya_smart_ir_ac.sensor import (
    TuyaClimateTemperatureSensor,
    TuyaClimateHumiditySensor,
    TuyaSensorTemperatureSensor,
    TuyaSensorHumiditySensor,
    TuyaSensorBatterySensor,
    async_setup_entry,
)
from tuya_smart_ir_ac.models import RuntimeData, TuyaSensorData, TuyaClimateData
from tuya_smart_ir_ac.const import (
    DEVICE_TYPE_CLIMATES,
    DEVICE_TYPE_SENSORS,
    CONF_INFRARED_ID,
    CONF_DEVICE_ID,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_SENSOR_TYPES,
    CONF_OPTIONAL_ENTITIES,
    ENTITY_CURRENT_TEMPERATURE,
    ENTITY_CURRENT_HUMIDITY,
    ENTITY_SENSOR_TEMPERATURE,
    ENTITY_SENSOR_HUMIDITY,
    ENTITY_SENSOR_BATTERY,
)
CONF_NAME = "name"
from homeassistant.core import State


class DummyCoordinator:
    def __init__(self, data):
        self.data = data

    def is_available(self, _):
        return True


class DummyConfigEntry:
    def __init__(self, title, options, runtime_data):
        self.title = title
        self.options = options
        self.runtime_data = runtime_data


async def test_async_setup_entry_creates_sensor_entities():
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({}), sensor_coordinator=DummyCoordinator({}))
    config_entry = DummyConfigEntry(
        title="Hub F",
        options={
            DEVICE_TYPE_CLIMATES: [{CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "AC", CONF_TEMPERATURE_SENSOR: "sensor.temp", CONF_HUMIDITY_SENSOR: "sensor.humi", CONF_OPTIONAL_ENTITIES: [ENTITY_CURRENT_TEMPERATURE, ENTITY_CURRENT_HUMIDITY]}],
            DEVICE_TYPE_SENSORS: [{CONF_DEVICE_ID: "sensor_1", CONF_NAME: "Sensor", CONF_SENSOR_TYPES: [ENTITY_SENSOR_TEMPERATURE, ENTITY_SENSOR_HUMIDITY, ENTITY_SENSOR_BATTERY]}],
        },
        runtime_data=runtime_data,
    )
    created = []
    await async_setup_entry(None, config_entry, lambda entities: created.extend(entities))

    assert any(isinstance(entity, TuyaClimateTemperatureSensor) for entity in created)
    assert any(isinstance(entity, TuyaClimateHumiditySensor) for entity in created)
    assert any(isinstance(entity, TuyaSensorTemperatureSensor) for entity in created)
    assert any(isinstance(entity, TuyaSensorHumiditySensor) for entity in created)
    assert any(isinstance(entity, TuyaSensorBatterySensor) for entity in created)


async def test_climate_temperature_sensor_reads_state_and_updates_on_event():
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({}))
    entity = TuyaClimateTemperatureSensor({CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "AC", CONF_TEMPERATURE_SENSOR: "sensor.temp"}, runtime_data)
    entity.hass = types.SimpleNamespace(states={"sensor.temp": State(state="22", attributes={"unit_of_measurement": "°C"})})

    async def fake_last_state():
        return types.SimpleNamespace(state="22", attributes={"unit_of_measurement": "°C"})

    entity.async_get_last_state = fake_last_state
    entity.async_write_ha_state = lambda: setattr(entity, "wrote", True)

    await entity.async_added_to_hass()
    assert entity.native_unit_of_measurement == "°C"
    assert entity.native_value == 22.0

    entity._handle_sensor_state_change(types.SimpleNamespace(data={"new_state": {}}))
    assert getattr(entity, "wrote", False)


async def test_climate_humidity_sensor_reads_state_and_updates_on_event():
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({}))
    entity = TuyaClimateHumiditySensor({CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "AC", CONF_HUMIDITY_SENSOR: "sensor.humi"}, runtime_data)
    entity.hass = types.SimpleNamespace(states={"sensor.humi": State(state="44", attributes={})})

    async def fake_last_state():
        return types.SimpleNamespace(state="44", attributes={})

    entity.async_get_last_state = fake_last_state
    entity.async_write_ha_state = lambda: setattr(entity, "wrote", True)

    await entity.async_added_to_hass()
    assert entity.native_value == 44.0

    entity._handle_sensor_state_change(types.SimpleNamespace(data={"new_state": {}}))
    assert getattr(entity, "wrote", False)


async def test_sensor_entities_return_coordinator_values():
    sensor_data = TuyaSensorData(temp_unit_convert="c", temp_current=23.5, humidity_value=55, battery_state=90)
    runtime_data = RuntimeData(client=None, sensor_coordinator=DummyCoordinator({"sensor_1": sensor_data}))
    temperature = TuyaSensorTemperatureSensor({CONF_DEVICE_ID: "sensor_1", CONF_NAME: "Sensor"}, runtime_data)
    humidity = TuyaSensorHumiditySensor({CONF_DEVICE_ID: "sensor_1", CONF_NAME: "Sensor"}, runtime_data)
    battery = TuyaSensorBatterySensor({CONF_DEVICE_ID: "sensor_1", CONF_NAME: "Sensor"}, runtime_data)

    assert temperature.native_value == 23.5
    assert humidity.native_value == 55
    assert battery.native_value == 90
