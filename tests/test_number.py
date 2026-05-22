import types

from tuya_smart_ir_ac.number import TuyaPresetTemperatureNumber, TuyaTemperatureSetPointNumber, async_setup_entry
from tuya_smart_ir_ac.models import RuntimeData, TuyaClimateData
from tuya_smart_ir_ac.const import (
    DEVICE_TYPE_CLIMATES,
    CONF_INFRARED_ID,
    CONF_DEVICE_ID,
    CONF_HVAC_PRESETS,
    ENTITY_TEMPERATURE_SETPOINT,
    PRESET_TEMP_HVAC_MODE,
    CONF_OPTIONAL_ENTITIES,
)
CONF_NAME = "name"


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


async def test_async_setup_entry_creates_number_entities():
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({}))
    config_entry = DummyConfigEntry(
        title="Hub D",
        options={DEVICE_TYPE_CLIMATES: [{CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "AC", CONF_HVAC_PRESETS: [PRESET_TEMP_HVAC_MODE], CONF_OPTIONAL_ENTITIES: [ENTITY_TEMPERATURE_SETPOINT]}]},
        runtime_data=runtime_data,
    )
    created = []
    await async_setup_entry(None, config_entry, lambda entities: created.extend(entities))

    assert any(isinstance(entity, TuyaPresetTemperatureNumber) for entity in created)
    assert any(isinstance(entity, TuyaTemperatureSetPointNumber) for entity in created)


async def test_tuya_preset_temperature_number_restores_last_value_and_sets_preset():
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({}))
    config_data = {CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "AC", CONF_HVAC_PRESETS: [PRESET_TEMP_HVAC_MODE]}
    entity = TuyaPresetTemperatureNumber(config_data, runtime_data, "cool")

    async def fake_last_number():
        return types.SimpleNamespace(native_value=23.5)

    entity.async_get_last_number_data = fake_last_number
    entity.async_write_ha_state = lambda: None

    await entity.async_added_to_hass()

    assert entity._attr_native_value == 23.5
    assert runtime_data.hvac_presets["device_1"]["temp_cool"] == 23.5


async def test_tuya_temperature_setpoint_number_reports_coordinator_value_and_sends_temperature():
    climate_data = TuyaClimateData(power=True, hvac_mode="cool", temperature=20.0, fan_mode="auto")
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({"device_1": climate_data}))
    config_data = {CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "AC"}
    entity = TuyaTemperatureSetPointNumber(config_data, runtime_data)

    assert entity.native_value == 20.0

    called = []

    async def fake_execute(value):
        called.append(value)

    entity.async_execute_set_temperature = fake_execute
    entity.async_write_ha_state = lambda: None

    await entity.async_set_native_value(19.0)
    assert called == [19.0]
