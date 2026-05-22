import types

from tuya_smart_ir_ac.button import TuyaButton, async_setup_entry
from tuya_smart_ir_ac.models import RuntimeData, TuyaAPIResult
from tuya_smart_ir_ac.const import DEVICE_TYPE_GENERICS, CONF_INFRARED_ID, CONF_DEVICE_ID
CONF_NAME = "name"


class DummyIRManager:
    def __init__(self, response):
        self.response = response
        self.sent_commands = []

    async def async_fetch_data(self, infrared_id, device_id):
        return self.response

    async def async_send_command(self, infrared_id, device_id, category, key_id, key):
        self.sent_commands.append((infrared_id, device_id, category, key_id, key))
        return TuyaAPIResult(success=True, data=None)


class DummyConfigEntry:
    def __init__(self, title, options, runtime_data, entry_id="entry1"):
        self.title = title
        self.options = options
        self.runtime_data = runtime_data
        self.entry_id = entry_id


async def test_async_setup_entry_creates_button_entities():
    key_data = types.SimpleNamespace(key="power", key_id="1", key_name="Power")
    device_data = types.SimpleNamespace(category_id="cat", key_list=[key_data])
    ir_manager = DummyIRManager(device_data)
    runtime_data = RuntimeData(client=None, ir_manager=ir_manager)
    config_entry = DummyConfigEntry(
        title="Hub A",
        options={DEVICE_TYPE_GENERICS: [{CONF_INFRARED_ID: "infra_1", CONF_DEVICE_ID: "device_1", CONF_NAME: "Remote"}]},
        runtime_data=runtime_data,
    )
    created = []

    await async_setup_entry(None, config_entry, lambda entities: created.extend(entities))

    assert len(created) == 1
    button = created[0]
    assert isinstance(button, TuyaButton)
    assert button.unique_id == "infra_1_device_1_1"
    assert button.name == "Remote Power"

    await button.async_press()
    assert ir_manager.sent_commands == [("infra_1", "device_1", "cat", "1", "power")]


async def test_async_setup_entry_skips_invalid_generic_data():
    ir_manager = DummyIRManager(None)
    runtime_data = RuntimeData(client=None, ir_manager=ir_manager)
    config_entry = DummyConfigEntry(
        title="Hub B",
        options={DEVICE_TYPE_GENERICS: [{CONF_INFRARED_ID: None, CONF_DEVICE_ID: "device_1", CONF_NAME: "Remote"}]},
        runtime_data=runtime_data,
    )
    created = []

    await async_setup_entry(None, config_entry, lambda entities: created.extend(entities))

    assert created == []
