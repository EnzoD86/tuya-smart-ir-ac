import types

import pytest

from tuya_smart_ir_ac import config_flow
from tuya_smart_ir_ac.const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_TUYA_COUNTRY,
    CONF_CLIMATE_UPDATE_INTERVAL,
    CONF_SENSOR_UPDATE_INTERVAL,
    CONF_HVAC_MODES,
    CONF_FAN_MODES,
    SUPPORTED_HVAC_MODES,
    SUPPORTED_FAN_MODES,
)


async def test_overwrite_invalid_user_input_sets_default_modes():
    user_input = {CONF_HVAC_MODES: [], CONF_FAN_MODES: []}
    config_flow.overwrite_invalid_user_input(user_input)

    assert user_input[CONF_HVAC_MODES] == SUPPORTED_HVAC_MODES
    assert user_input[CONF_FAN_MODES] == SUPPORTED_FAN_MODES


def test_schema_generators_return_selector_objects():
    hub_schema = config_flow.hub_data_schema()
    assert CONF_ACCESS_ID in hub_schema and CONF_ACCESS_SECRET in hub_schema

    device_schema = config_flow.device1_data()
    assert CONF_ACCESS_ID not in device_schema


@pytest.mark.asyncio
async def test_async_validate_and_connect_success(monkeypatch):
    async def fake_connect():
        return {"success": True}

    class DummyClient:
        def __init__(self, api_endpoint, access_id, access_secret):
            self.session = None
        async def connect(self):
            return await fake_connect()

    monkeypatch.setattr(config_flow, "TuyaOpenAPI", DummyClient)

    errors = await config_flow.async_validate_and_connect({
        CONF_ACCESS_ID: "abc",
        CONF_ACCESS_SECRET: "def",
        CONF_TUYA_COUNTRY: "us",
        CONF_CLIMATE_UPDATE_INTERVAL: 30,
        CONF_SENSOR_UPDATE_INTERVAL: 30,
    })

    assert errors == {}


@pytest.mark.asyncio
async def test_async_validate_and_connect_invalid_country_returns_error():
    errors = await config_flow.async_validate_and_connect({
        CONF_ACCESS_ID: "abc",
        CONF_ACCESS_SECRET: "def",
        CONF_TUYA_COUNTRY: "invalid",
        CONF_CLIMATE_UPDATE_INTERVAL: 30,
        CONF_SENSOR_UPDATE_INTERVAL: 30,
    })

    assert CONF_TUYA_COUNTRY in errors


@pytest.mark.asyncio
async def test_async_step_hub_settings_creates_entry_on_valid_input(monkeypatch):
    async def fake_connect():
        return {"success": True}

    class DummyClient:
        def __init__(self, api_endpoint, access_id, access_secret):
            self.session = None
        async def connect(self):
            return await fake_connect()

    monkeypatch.setattr(config_flow, "TuyaOpenAPI", DummyClient)

    handler = config_flow.ConfigFlowHandler()
    handler.hass = types.SimpleNamespace(
        config_entries=types.SimpleNamespace(async_entries=lambda domain: [], async_get_entry=lambda entry_id: None),
    )
    handler.context = {}

    result = await handler.async_step_hub_settings({
        CONF_ACCESS_ID: "abc",
        CONF_ACCESS_SECRET: "def",
        CONF_TUYA_COUNTRY: "us",
        CONF_CLIMATE_UPDATE_INTERVAL: 30,
        CONF_SENSOR_UPDATE_INTERVAL: 30,
    })

    assert result["type"] == "create_entry"
    assert CONF_ACCESS_ID in result["data"]


@pytest.mark.asyncio
async def test_async_step_hub_settings_rejects_changed_access_id_for_existing_entry():
    handler = config_flow.ConfigFlowHandler()
    handler.hass = types.SimpleNamespace(
        config_entries=types.SimpleNamespace(
            async_entries=lambda domain: [],
            async_get_entry=lambda entry_id: types.SimpleNamespace(data={CONF_ACCESS_ID: "abc"}, options={})
        ),
    )
    handler.context = {"entry_id": "entry1"}

    result = await handler.async_step_hub_settings({
        CONF_ACCESS_ID: "different",
        CONF_ACCESS_SECRET: "def",
        CONF_TUYA_COUNTRY: "us",
        CONF_CLIMATE_UPDATE_INTERVAL: 30,
        CONF_SENSOR_UPDATE_INTERVAL: 30,
    })

    assert result["type"] == "form"
    assert result["errors"][CONF_ACCESS_ID] == "cannot_change_access_id"


def test_options_flow_get_options_flow_returns_handler():
    entry = types.SimpleNamespace(data={CONF_ACCESS_ID: "abc"}, options={})
    options_flow = config_flow.ConfigFlowHandler.async_get_options_flow(entry)

    assert isinstance(options_flow, config_flow.OptionsFlowHandler)


@pytest.mark.asyncio
async def test_options_flow_init_shows_device_management_menu():
    handler = config_flow.OptionsFlowHandler()
    handler.config_entry = types.SimpleNamespace(data={CONF_ACCESS_ID: "abc"}, options={})
    handler.hass = types.SimpleNamespace(config_entries=types.SimpleNamespace(async_update_entry=lambda entry, data: None))

    result = await handler.async_step_init()

    assert result["type"] == "form"
    assert result["step_id"] == "init"
    assert "device_management" in result["menu_options"]


@pytest.mark.asyncio
async def test_options_flow_hub_settings_rejects_access_id_change():
    handler = config_flow.OptionsFlowHandler()
    handler.config_entry = types.SimpleNamespace(data={CONF_ACCESS_ID: "abc"}, options={})
    handler.hass = types.SimpleNamespace(config_entries=types.SimpleNamespace(async_update_entry=lambda entry, data: None))

    result = await handler.async_step_hub_settings({
        CONF_ACCESS_ID: "different",
        CONF_ACCESS_SECRET: "def",
        CONF_TUYA_COUNTRY: "us",
        CONF_CLIMATE_UPDATE_INTERVAL: 30,
        CONF_SENSOR_UPDATE_INTERVAL: 30,
    })

    assert result["type"] == "form"
    assert result["errors"][CONF_ACCESS_ID] == "cannot_change_access_id"
