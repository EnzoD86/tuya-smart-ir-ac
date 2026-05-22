import types

import pytest

from homeassistant.components.climate.const import HVACMode
from homeassistant.components.climate import FAN_AUTO
from homeassistant.core import State
from tuya_smart_ir_ac.climate import TuyaClimate, async_setup_entry
from tuya_smart_ir_ac.models import RuntimeData, TuyaClimateData
from tuya_smart_ir_ac.const import DEVICE_TYPE_CLIMATES, CONF_INFRARED_ID, CONF_DEVICE_ID

CONF_NAME = "name"


class DummyCoordinator:
    def __init__(self, data):
        self.data = data

    def is_available(self, climate_id):
        return climate_id in self.data


class DummyConfigEntry:
    def __init__(self, title, options, runtime_data):
        self.title = title
        self.options = options
        self.runtime_data = runtime_data


async def test_async_setup_entry_initializes_climate_entities():
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({}))
    config_entry = DummyConfigEntry(
        title="Hub C",
        options={DEVICE_TYPE_CLIMATES: [{CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "Living Room"}]},
        runtime_data=runtime_data,
    )
    created = []
    await async_setup_entry(None, config_entry, lambda entities: created.extend(entities))

    assert len(created) == 1
    entity = created[0]
    assert entity._attr_unique_id == "infra_1_device_1"


async def test_tuya_climate_entity_properties_fallback_and_coordinator_data():
    climate_data = TuyaClimateData(power=True, hvac_mode=HVACMode.COOL, temperature=21.0, fan_mode="high")
    coordinator = DummyCoordinator({"device_1": climate_data})
    runtime_data = RuntimeData(client=None, climate_coordinator=coordinator)
    entity = TuyaClimate({CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "Living Room"}, runtime_data)
    entity.coordinator = coordinator

    assert entity.hvac_mode == HVACMode.COOL
    assert entity.target_temperature == 21.0
    assert entity.fan_mode == "high"

    # When data is missing, fallback values are used.
    empty_runtime = RuntimeData(client=None, climate_coordinator=DummyCoordinator({}))
    fallback_entity = TuyaClimate({CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_2", CONF_NAME: "Bedroom"}, empty_runtime)
    fallback_entity.coordinator = empty_runtime.climate_coordinator

    assert fallback_entity.hvac_mode == HVACMode.OFF
    assert fallback_entity.target_temperature == 25.0
    assert fallback_entity.fan_mode == "auto"


async def test_async_climate_control_methods_invoke_execution_logic():
    coordinator = DummyCoordinator({})
    runtime_data = RuntimeData(client=None, climate_coordinator=coordinator)
    entity = TuyaClimate({CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "Living Room"}, runtime_data)

    called = []

    async def fake_execute(*args, **kwargs):
        if "hvac_mode" in kwargs:
            called.append(kwargs["hvac_mode"])
        elif args:
            called.append(args[0])

    entity.async_execute_set_hvac_mode = fake_execute
    await entity.async_set_hvac_mode(HVACMode.COOL)
    assert called == [HVACMode.COOL]

    called.clear()
    entity.async_execute_set_temperature = fake_execute
    await entity.async_set_temperature(temperature=22.5)
    assert called == [22.5]

    called.clear()
    entity.async_execute_set_fan_mode = fake_execute
    await entity.async_set_fan_mode("low")
    assert called == ["low"]


async def test_async_turn_on_and_turn_off_execute_correctly():
    coordinator = types.SimpleNamespace()
    entity = TuyaClimate({"infrared_id": "infra_1", "device_id": "device_1", "name": "Living Room"}, RuntimeData(client=None, climate_coordinator=coordinator))

    called = []
    async def fake_execute_turn_on():
        called.append("turn_on")
    async def fake_execute_turn_off():
        called.append("turn_off")

    entity.async_execute_turn_on = fake_execute_turn_on
    entity.async_execute_turn_off = fake_execute_turn_off
    entity.async_write_ha_state = lambda: None

    await entity.async_turn_on()
    await entity.async_turn_off()

    assert called == ["turn_on", "turn_off"]


async def test_async_climate_entity_updates_on_sensor_state_change():
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({}))
    entity = TuyaClimate({"infrared_id": "infra_1", "device_id": "device_1", "name": "Living Room", "temperature_sensor": "sensor.temp", "humidity_sensor": "sensor.humi"}, runtime_data)
    entity.hass = types.SimpleNamespace(states={
        "sensor.temp": State(state="22", attributes={"unit_of_measurement": "°C"}),
        "sensor.humi": State(state="45", attributes={}),
    })

    async def fake_last_state():
        return None

    entity.async_get_last_state = fake_last_state
    entity.async_write_ha_state = lambda: setattr(entity, "wrote", True)

    await entity.async_added_to_hass()
    assert entity.current_temperature == 22.0
    assert entity.current_humidity == 45.0

    entity._handle_sensor_state_change(types.SimpleNamespace(data={"new_state": {}}))
    assert getattr(entity, "wrote", False)


async def test_hvac_mode_property_handles_dry_and_fan_only():
    climate_data = TuyaClimateData(power=True, hvac_mode=HVACMode.DRY, temperature=18.0, fan_mode="auto")
    coordinator = DummyCoordinator({"device_1": climate_data})
    runtime_data = RuntimeData(client=None, climate_coordinator=coordinator)
    entity = TuyaClimate({"infrared_id": "infra_1", "device_id": "device_1", "name": "Living Room"}, runtime_data)
    entity.coordinator = coordinator

    assert entity.hvac_mode == HVACMode.DRY
    assert entity.fan_mode == "auto"

    coordinator.data["device_1"].hvac_mode = HVACMode.FAN_ONLY
    assert entity.hvac_mode == HVACMode.FAN_ONLY
