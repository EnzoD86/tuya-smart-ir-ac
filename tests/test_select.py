import types

from homeassistant.components.climate.const import HVACMode
from tuya_smart_ir_ac.select import (
    TuyaPresetFanSelect,
    TuyaHvacModeSelect,
    TuyaFanModeSelect,
    async_setup_entry,
)
from tuya_smart_ir_ac.models import RuntimeData, TuyaClimateData
from tuya_smart_ir_ac.const import (
    DEVICE_TYPE_CLIMATES,
    CONF_INFRARED_ID,
    CONF_DEVICE_ID,
    CONF_HVAC_PRESETS,
    PRESET_FAN_HVAC_MODE,
    CONF_OPTIONAL_ENTITIES,
    ENTITY_HVAC_MODE,
    ENTITY_FAN_MODE,
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


async def test_async_setup_entry_creates_select_entities():
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({}))
    config_entry = DummyConfigEntry(
        title="Hub E",
        options={DEVICE_TYPE_CLIMATES: [{CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "AC", CONF_HVAC_PRESETS: [PRESET_FAN_HVAC_MODE], CONF_OPTIONAL_ENTITIES: [ENTITY_HVAC_MODE, ENTITY_FAN_MODE]}]},
        runtime_data=runtime_data,
    )
    created = []
    await async_setup_entry(None, config_entry, lambda entities: created.extend(entities))

    assert any(isinstance(entity, TuyaPresetFanSelect) for entity in created)
    assert any(isinstance(entity, TuyaHvacModeSelect) for entity in created)
    assert any(isinstance(entity, TuyaFanModeSelect) for entity in created)


async def test_tuya_preset_fan_select_restores_state_and_updates_option():
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({}))
    config_data = {CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "AC", CONF_HVAC_PRESETS: [PRESET_FAN_HVAC_MODE]}
    entity = TuyaPresetFanSelect(config_data, runtime_data)

    async def fake_last_state():
        return types.SimpleNamespace(state="low")

    entity.async_get_last_state = fake_last_state
    entity.async_write_ha_state = lambda: None

    await entity.async_added_to_hass()
    assert entity._attr_current_option == "low"

    await entity.async_select_option("high")
    assert entity._attr_current_option == "high"


async def test_tuya_hvac_mode_select_reports_option_and_executes_mode():
    climate_data = TuyaClimateData(power=True, hvac_mode=HVACMode.COOL, temperature=20.0, fan_mode="auto")
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({"device_1": climate_data}))
    config_data = {CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "AC"}
    entity = TuyaHvacModeSelect(config_data, runtime_data)
    entity.async_write_ha_state = lambda: None

    assert entity.current_option == HVACMode.COOL.value

    called = []
    async def fake_execute(mode):
        called.append(mode)
    entity.async_execute_set_hvac_mode = fake_execute
    await entity.async_select_option(HVACMode.COOL.value)
    assert called == [HVACMode.COOL]


async def test_tuya_fan_mode_select_reports_option_and_executes():
    climate_data = TuyaClimateData(power=True, hvac_mode=HVACMode.COOL, temperature=20.0, fan_mode="high")
    runtime_data = RuntimeData(client=None, climate_coordinator=DummyCoordinator({"device_1": climate_data}))
    entity = TuyaFanModeSelect({CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "AC"}, runtime_data)
    entity.async_write_ha_state = lambda: None

    assert entity.current_option == "high"

    called = []
    async def fake_execute(option):
        called.append(option)
    entity.async_execute_set_fan_mode = fake_execute
    await entity.async_select_option("low")
    assert called == ["low"]
