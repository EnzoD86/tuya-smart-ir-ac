import pytest

from homeassistant.components.climate.const import HVACMode, FAN_LOW, FAN_AUTO
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.update_coordinator import UpdateFailed

from tuya_smart_ir_ac.const import (
    CONF_DEVICE_ID,
    CONF_HVAC_PRESETS,
    CONF_INFRARED_ID,
    CONF_TEMP_UNIT,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_COMPATIBILITY_OPTIONS,
    CONF_HVAC_POWER_ON,
    CONF_TEMP_POWER_ON,
    CONF_FAN_POWER_ON,
    CONF_DRY_MIN_TEMP,
    CONF_DRY_MIN_FAN,
    PRESET_TEMP_HVAC_MODE,
    PRESET_FAN_HVAC_MODE,
    POWER_ON_ALWAYS,
    POWER_ON_NEVER,
    POWER_ON_ONLY_OFF,
)
from tuya_smart_ir_ac.coordinator import TuyaClimateCoordinator
from tuya_smart_ir_ac.entity import TuyaClimateEntity
from tuya_smart_ir_ac.manager import TuyaIRManager
from tuya_smart_ir_ac.models import RuntimeData, TuyaAPIResult, TuyaClimateData


class DummyEntry:
    def __init__(self, title="Test Hub", options=None, data=None):
        self.title = title
        self.options = options or {}
        self.data = data or {}


class DummyClient:
    pass


class DummyAPI:
    def __init__(self, result):
        self.result = result
        self.sent_commands = []

    async def async_fetch_all_data(self, ids):
        return self.result

    async def async_send_command(self, infrared_id, device_id, category, key, value=None):
        self.sent_commands.append((infrared_id, device_id, category, key, value))
        return self.result

    async def async_send_multiple_command(self, infrared_id, device_id, command_type, *values):
        self.sent_commands.append((infrared_id, device_id, command_type, *values))
        return self.result


class DummyAPIForManager:
    def __init__(self, result):
        self.result = result

    async def async_fetch_data(self, infrared_id, device_id):
        return self.result

    async def async_send_command(self, infrared_id, device_id, category_id, key_id, key):
        return self.result


class DummyState:
    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}


class DummyStates:
    def __init__(self, state):
        self._state = state

    def get(self, entity_id):
        return self._state


class DummyHass:
    def __init__(self, state):
        self.states = DummyStates(state)


@pytest.mark.asyncio
async def test_tuya_climate_coordinator_update_data_returns_empty_when_no_climates_configured():
    coordinator = TuyaClimateCoordinator(
        hass=DummyHass(None),
        entry=DummyEntry(options={"climates": []}),
        client=DummyClient(),
    )
    coordinator._api = DummyAPI(TuyaAPIResult(success=True, data={}))

    result = await coordinator._async_update_data()

    assert result == {}


@pytest.mark.asyncio
async def test_tuya_climate_coordinator_update_data_fetches_climate_data():
    climate_data = TuyaClimateData(power=True, hvac_mode=HVACMode.COOL, temperature=22.0, fan_mode="1")
    result_data = {"device_1": climate_data}
    coordinator = TuyaClimateCoordinator(
        hass=DummyHass(None),
        entry=DummyEntry(options={"climates": [{"device_id": "device_1"}]}),
        client=DummyClient(),
    )
    coordinator._api = DummyAPI(TuyaAPIResult(success=True, data=result_data))

    result = await coordinator._async_update_data()

    assert result == result_data
    assert result["device_1"].temperature == 22.0


@pytest.mark.asyncio
async def test_tuya_climate_coordinator_turn_on_updates_local_cache():
    coordinator = TuyaClimateCoordinator(
        hass=DummyHass(None),
        entry=DummyEntry(options={"climates": [{"device_id": "device_1"}]}),
        client=DummyClient(),
    )
    coordinator.data = {
        "device_1": TuyaClimateData(power=False, hvac_mode=HVACMode.COOL, temperature=22.0, fan_mode="1")
    }
    api = DummyAPI(TuyaAPIResult(success=True, data=None))
    coordinator._api = api

    await coordinator.async_turn_on("infra_1", "device_1")

    assert coordinator.data["device_1"].power is True


@pytest.mark.asyncio
async def test_tuya_climate_coordinator_turn_on_raises_when_api_fails():
    coordinator = TuyaClimateCoordinator(
        hass=DummyHass(None),
        entry=DummyEntry(options={"climates": [{"device_id": "device_1"}]}),
        client=DummyClient(),
    )
    coordinator.data = {
        "device_1": TuyaClimateData(power=False, hvac_mode=HVACMode.COOL, temperature=22.0, fan_mode="1")
    }
    coordinator._api = DummyAPI(TuyaAPIResult(success=False, error_code="ERR", error_msg="bad"))

    with pytest.raises(ServiceValidationError):
        await coordinator.async_turn_on("infra_1", "device_1")


@pytest.mark.asyncio
async def test_tuya_ir_manager_fetch_data_returns_generic_data_on_success():
    manager = TuyaIRManager(DummyHass(None), DummyEntry(title="Hub A"), DummyClient())
    manager._api = DummyAPIForManager(TuyaAPIResult(success=True, data={"category_id": "cat", "key_list": []}))

    result = await manager.async_fetch_data("infra_1", "device_1")

    assert result == {"category_id": "cat", "key_list": []}


@pytest.mark.asyncio
async def test_tuya_ir_manager_fetch_data_returns_none_on_failure():
    manager = TuyaIRManager(DummyHass(None), DummyEntry(title="Hub A"), DummyClient())
    manager._api = DummyAPIForManager(TuyaAPIResult(success=False, error_code="ERR", error_msg="fail"))

    result = await manager.async_fetch_data("infra_1", "device_1")

    assert result is None


@pytest.mark.asyncio
async def test_tuya_ir_manager_send_command_raises_on_failure():
    manager = TuyaIRManager(DummyHass(None), DummyEntry(title="Hub B"), DummyClient())
    manager._api = DummyAPIForManager(TuyaAPIResult(success=False, error_code="ERR", error_msg="fail"))

    with pytest.raises(ServiceValidationError):
        await manager.async_send_command("infra_1", "device_1", "cat", "key_id", "key")


@pytest.mark.asyncio
async def test_tuya_climate_coordinator_update_data_raises_update_failed_on_api_error():
    coordinator = TuyaClimateCoordinator(
        hass=DummyHass(None),
        entry=DummyEntry(options={"climates": [{"device_id": "device_1"}]}),
        client=DummyClient(),
    )
    coordinator._api = DummyAPI(TuyaAPIResult(success=False, error_code="ERR", error_msg="fetch fail"))

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_tuya_sensor_coordinator_update_data_raises_update_failed_on_api_error():
    from tuya_smart_ir_ac.coordinator import TuyaSensorCoordinator

    coordinator = TuyaSensorCoordinator(
        hass=DummyHass(None),
        entry=DummyEntry(options={"sensors": [{"device_id": "sensor_1"}]}),
        client=DummyClient(),
    )
    coordinator._api = DummyAPI(TuyaAPIResult(success=False, error_code="ERR", error_msg="fetch fail"))

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


def test_tuya_climate_entity_preset_and_power_on_logic():
    config_data = {
        CONF_INFRARED_ID: "infra_1",
        CONF_DEVICE_ID: "device_1",
        "name": "Test Climate",
        CONF_HVAC_PRESETS: [PRESET_TEMP_HVAC_MODE, PRESET_FAN_HVAC_MODE],
        CONF_COMPATIBILITY_OPTIONS: {
            CONF_HVAC_POWER_ON: POWER_ON_ALWAYS,
            CONF_TEMP_POWER_ON: POWER_ON_ONLY_OFF,
            CONF_FAN_POWER_ON: POWER_ON_NEVER,
            CONF_DRY_MIN_TEMP: 18,
            CONF_DRY_MIN_FAN: True,
        },
        CONF_TEMPERATURE_SENSOR: "sensor.temp",
        CONF_HUMIDITY_SENSOR: "sensor.humidity",
    }
    runtime_data = RuntimeData(client=None)
    entity = TuyaClimateEntity(config_data, runtime_data)
    entity.coordinator = type("StubCoordinator", (), {"data": {"device_1": TuyaClimateData(power=True, hvac_mode=HVACMode.COOL, temperature=21.0, fan_mode="1")}, "is_available": lambda self, device_id: device_id == "device_1"})()
    entity.hass = DummyHass(DummyState("68", {ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.FAHRENHEIT}))

    entity.set_hvac_preset_temperature(HVACMode.COOL, 19.5)
    assert entity.get_hvac_preset_temperature(HVACMode.COOL) == 19.5

    entity.set_hvac_preset_fan_mode("low")
    assert entity.get_hvac_preset_fan_mode() == "low"

    assert entity.get_hvac_temperature(HVACMode.COOL) == 19.5
    assert entity.get_hvac_fan_mode(HVACMode.DRY) == FAN_LOW
    assert entity.get_hvac_fan_mode(HVACMode.COOL) == "low"
    assert entity.get_power_on(POWER_ON_ALWAYS, HVACMode.OFF) is True
    assert entity.get_power_on(POWER_ON_NEVER, HVACMode.COOL) is False
    assert entity.get_power_on(POWER_ON_ONLY_OFF, HVACMode.OFF) is True

    assert entity.get_temperature_value(convert=True) == pytest.approx(68.0)


def test_get_hvac_fan_mode_uses_coordinator_and_defaults():
    entity = TuyaClimateEntity(
        {
            CONF_INFRARED_ID: "infra_1",
            CONF_DEVICE_ID: "device_1",
            "name": "Test Climate",
        },
        RuntimeData(client=None),
    )
    entity.coordinator = type(
        "StubCoordinator",
        (),
        {
            "data": {"device_1": TuyaClimateData(power=True, hvac_mode=HVACMode.COOL, temperature=22.0, fan_mode="high")},
            "is_available": lambda self, device_id: device_id == "device_1",
        },
    )()

    assert entity.get_hvac_fan_mode(HVACMode.COOL) == "high"

    entity.coordinator.data["device_1"].fan_mode = None
    assert entity.get_hvac_fan_mode(HVACMode.COOL) == FAN_AUTO

    entity._dry_min_fan = False
    assert entity.get_hvac_fan_mode(HVACMode.DRY) == FAN_AUTO
