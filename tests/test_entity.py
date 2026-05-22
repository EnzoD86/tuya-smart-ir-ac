import types

from homeassistant.components.climate.const import HVACMode
from homeassistant.core import State
from tuya_smart_ir_ac.entity import TuyaClimateEntity
from tuya_smart_ir_ac.models import RuntimeData, TuyaClimateData
from tuya_smart_ir_ac.const import (
    CONF_INFRARED_ID,
    CONF_DEVICE_ID,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_COMPATIBILITY_OPTIONS,
    CONF_HVAC_POWER_ON,
    CONF_TEMP_POWER_ON,
    POWER_ON_ALWAYS,
    POWER_ON_NEVER,
    POWER_ON_ONLY_OFF,
)
CONF_NAME = "name"


class DummyCoordinator:
    def __init__(self, data):
        self.data = data
        self.actions = []

    def is_available(self, _):
        return True

    async def async_turn_on(self, infrared_id, climate_id):
        self.actions.append(("turn_on", infrared_id, climate_id))

    async def async_turn_off(self, infrared_id, climate_id):
        self.actions.append(("turn_off", infrared_id, climate_id))

    async def async_set_hvac_mode(self, infrared_id, climate_id, hvac_mode, temperature, fan_mode):
        self.actions.append(("set_hvac_mode", infrared_id, climate_id, hvac_mode, temperature, fan_mode))

    async def async_set_temperature(self, infrared_id, climate_id, value):
        self.actions.append(("set_temperature", infrared_id, climate_id, value))

    async def async_set_fan_mode(self, infrared_id, climate_id, fan_mode):
        self.actions.append(("set_fan_mode", infrared_id, climate_id, fan_mode))


async def test_hvac_temperature_and_fan_mode_helpers():
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({}))
    config_data = {
        CONF_INFRARED_ID: "infra_1",
        CONF_DEVICE_ID: "device_1",
        CONF_NAME: "AC",
        CONF_TEMPERATURE_SENSOR: "sensor.temp",
        CONF_HUMIDITY_SENSOR: "sensor.humi",
        CONF_COMPATIBILITY_OPTIONS: {
            "hvac_power_on": POWER_ON_ALWAYS,
            "temp_power_on": POWER_ON_NEVER,
            "fan_power_on": POWER_ON_ONLY_OFF,
        },
    }
    entity = TuyaClimateEntity(config_data, runtime_data)
    entity.hass = types.SimpleNamespace(states={
        "sensor.temp": State(state="24.0", attributes={"unit_of_measurement": "°C"}),
        "sensor.humi": State(state="45", attributes={}),
    })
    entity.coordinator = runtime_data.climate_coordinator

    assert entity.get_temperature_unit_of_measurement() == "°C"
    assert entity.get_temperature_value(convert=True) == 24.0
    assert entity.get_humidity_value() == 45.0
    assert entity.get_power_on(POWER_ON_ALWAYS, HVACMode.OFF) is True
    assert entity.get_power_on(POWER_ON_NEVER, HVACMode.COOL) is False
    assert entity.get_power_on(POWER_ON_ONLY_OFF, HVACMode.OFF) is True
    assert entity.get_power_on(POWER_ON_ONLY_OFF, HVACMode.COOL) is False


async def test_async_execute_set_hvac_mode_calls_coordinator_with_power_on():
    climate_data = TuyaClimateData(power=False, hvac_mode=None, temperature=20.0, fan_mode="auto")
    coordinator = DummyCoordinator({"device_1": climate_data})
    runtime_data = RuntimeData(client=None, climate_coordinator=coordinator)
    entity = TuyaClimateEntity({
        CONF_INFRARED_ID: "infra_1",
        CONF_DEVICE_ID: "device_1",
        CONF_NAME: "AC",
        CONF_COMPATIBILITY_OPTIONS: {CONF_HVAC_POWER_ON: POWER_ON_ONLY_OFF},
    }, runtime_data)
    entity.coordinator = coordinator

    await entity.async_execute_set_hvac_mode(HVACMode.COOL)

    assert coordinator.actions[0][0] == "turn_on"
    assert coordinator.actions[1][0] == "set_hvac_mode"


async def test_async_execute_set_hvac_mode_does_not_turn_on_when_disabled():
    climate_data = TuyaClimateData(power=False, hvac_mode=HVACMode.OFF, temperature=20.0, fan_mode="auto")
    coordinator = DummyCoordinator({"device_1": climate_data})
    runtime_data = RuntimeData(client=None, climate_coordinator=coordinator)
    entity = TuyaClimateEntity({
        CONF_INFRARED_ID: "infra_1",
        CONF_DEVICE_ID: "device_1",
        CONF_NAME: "AC",
        CONF_COMPATIBILITY_OPTIONS: {CONF_HVAC_POWER_ON: POWER_ON_NEVER},
    }, runtime_data)
    entity.coordinator = coordinator

    await entity.async_execute_set_hvac_mode(HVACMode.COOL)

    assert len(coordinator.actions) == 1
    assert coordinator.actions[0][0] == "set_hvac_mode"


async def test_async_execute_set_fan_mode_calls_coordinator_with_power_on():
    climate_data = TuyaClimateData(power=False, hvac_mode=None, temperature=20.0, fan_mode="auto")
    coordinator = DummyCoordinator({"device_1": climate_data})
    runtime_data = RuntimeData(client=None, climate_coordinator=coordinator)
    entity = TuyaClimateEntity({
        CONF_INFRARED_ID: "infra_1",
        CONF_DEVICE_ID: "device_1",
        CONF_NAME: "AC",
        CONF_COMPATIBILITY_OPTIONS: {"fan_power_on": POWER_ON_ONLY_OFF},
    }, runtime_data)
    entity.coordinator = coordinator

    await entity.async_execute_set_fan_mode("low")

    assert coordinator.actions[0][0] == "turn_on"
    assert coordinator.actions[1][0] == "set_fan_mode"


async def test_async_execute_set_temperature_calls_coordinator_with_power_on():
    climate_data = TuyaClimateData(power=False, hvac_mode=None, temperature=20.0, fan_mode="auto")
    coordinator = DummyCoordinator({"device_1": climate_data})
    runtime_data = RuntimeData(client=None, climate_coordinator=coordinator)
    entity = TuyaClimateEntity({
        CONF_INFRARED_ID: "infra_1",
        CONF_DEVICE_ID: "device_1",
        CONF_NAME: "AC",
        CONF_COMPATIBILITY_OPTIONS: {CONF_TEMP_POWER_ON: POWER_ON_ONLY_OFF},
    }, runtime_data)
    entity.coordinator = coordinator

    await entity.async_execute_set_temperature(22.5)

    assert coordinator.actions[0][0] == "turn_on"
    assert coordinator.actions[1][0] == "set_temperature"


async def test_async_execute_set_temperature_does_not_turn_on_when_disabled():
    climate_data = TuyaClimateData(power=False, hvac_mode=None, temperature=20.0, fan_mode="auto")
    coordinator = DummyCoordinator({"device_1": climate_data})
    runtime_data = RuntimeData(client=None, climate_coordinator=coordinator)
    entity = TuyaClimateEntity({
        CONF_INFRARED_ID: "infra_1",
        CONF_DEVICE_ID: "device_1",
        CONF_NAME: "AC",
        CONF_COMPATIBILITY_OPTIONS: {CONF_TEMP_POWER_ON: POWER_ON_NEVER},
    }, runtime_data)
    entity.coordinator = coordinator

    await entity.async_execute_set_temperature(22.5)

    assert len(coordinator.actions) == 1
    assert coordinator.actions[0][0] == "set_temperature"


async def test_async_execute_set_temperature_with_hvac_mode_calls_coordinator_with_power_on():
    climate_data = TuyaClimateData(power=False, hvac_mode=HVACMode.OFF, temperature=20.0, fan_mode="auto")
    coordinator = DummyCoordinator({"device_1": climate_data})
    runtime_data = RuntimeData(client=None, climate_coordinator=coordinator)
    entity = TuyaClimateEntity({
        CONF_INFRARED_ID: "infra_1",
        CONF_DEVICE_ID: "device_1",
        CONF_NAME: "AC",
        CONF_COMPATIBILITY_OPTIONS: {CONF_HVAC_POWER_ON: POWER_ON_ONLY_OFF},
    }, runtime_data)
    entity.coordinator = coordinator

    await entity.async_execute_set_temperature(22.5, hvac_mode=HVACMode.COOL)

    assert coordinator.actions[0][0] == "turn_on"
    assert coordinator.actions[1][0] == "set_hvac_mode"


async def test_async_execute_set_temperature_with_hvac_mode_off_turns_device_off():
    climate_data = TuyaClimateData(power=True, hvac_mode=HVACMode.COOL, temperature=20.0, fan_mode="auto")
    coordinator = DummyCoordinator({"device_1": climate_data})
    runtime_data = RuntimeData(client=None, climate_coordinator=coordinator)
    entity = TuyaClimateEntity({
        CONF_INFRARED_ID: "infra_1",
        CONF_DEVICE_ID: "device_1",
        CONF_NAME: "AC",
    }, runtime_data)
    entity.coordinator = coordinator

    await entity.async_execute_set_temperature(18.0, hvac_mode=HVACMode.OFF)

    assert len(coordinator.actions) == 1
    assert coordinator.actions[0][0] == "turn_off"


async def test_async_execute_set_fan_mode_does_not_turn_on_when_disabled():
    climate_data = TuyaClimateData(power=False, hvac_mode=None, temperature=20.0, fan_mode="auto")
    coordinator = DummyCoordinator({"device_1": climate_data})
    runtime_data = RuntimeData(client=None, climate_coordinator=coordinator)
    entity = TuyaClimateEntity({
        CONF_INFRARED_ID: "infra_1",
        CONF_DEVICE_ID: "device_1",
        CONF_NAME: "AC",
        CONF_COMPATIBILITY_OPTIONS: {"fan_power_on": POWER_ON_NEVER},
    }, runtime_data)
    entity.coordinator = coordinator

    await entity.async_execute_set_fan_mode("low")

    assert len(coordinator.actions) == 1
    assert coordinator.actions[0][0] == "set_fan_mode"
