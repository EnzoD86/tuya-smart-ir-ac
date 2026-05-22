import sys
import types
from dataclasses import dataclass
from pathlib import Path

pytest_plugins = ["pytest_asyncio"]

# Make the custom component package importable as a top-level module during tests.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components"))

# Stub Home Assistant modules used by this repository.

homeassistant = types.ModuleType("homeassistant")
homeassistant.__path__ = []
sys.modules["homeassistant"] = homeassistant

config_entries = types.ModuleType("homeassistant.config_entries")
config_entries.ConfigEntry = object
sys.modules["homeassistant.config_entries"] = config_entries

exceptions = types.ModuleType("homeassistant.exceptions")
exceptions.ConfigEntryAuthFailed = Exception
exceptions.ServiceValidationError = Exception
sys.modules["homeassistant.exceptions"] = exceptions

const = types.ModuleType("homeassistant.const")
const.STATE_UNAVAILABLE = "unavailable"
const.STATE_UNKNOWN = "unknown"
const.CONF_NAME = "name"

class UnitOfTemperature:
    CELSIUS = "°C"
    FAHRENHEIT = "°F"

const.UnitOfTemperature = UnitOfTemperature
const.ATTR_UNIT_OF_MEASUREMENT = "unit_of_measurement"
sys.modules["homeassistant.const"] = const

entity_module = types.ModuleType("homeassistant.helpers.entity")

class DeviceInfo:
    def __init__(self, *, name=None, identifiers=None, manufacturer=None, model=None):
        self.name = name
        self.identifiers = identifiers
        self.manufacturer = manufacturer
        self.model = model

entity_module.DeviceInfo = DeviceInfo
sys.modules["homeassistant.helpers.entity"] = entity_module

core = types.ModuleType("homeassistant.core")

@dataclass
class State:
    state: str
    attributes: dict | None = None

class HomeAssistant:
    pass

core.State = State
core.HomeAssistant = HomeAssistant
core.callback = lambda func: func
sys.modules["homeassistant.core"] = core

climate = types.ModuleType("homeassistant.components.climate")
climate.FAN_AUTO = "auto"
climate.FAN_LOW = "low"
climate.FAN_MEDIUM = "medium"
climate.FAN_HIGH = "high"

class HVACModeType:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __eq__(self, other):
        return getattr(other, "value", other) == self.value

HVACMode = HVACModeType
HVACMode.AUTO = HVACModeType("auto")
HVACMode.COOL = HVACModeType("cool")
HVACMode.HEAT = HVACModeType("heat")
HVACMode.DRY = HVACModeType("dry")
HVACMode.FAN_ONLY = HVACModeType("fan_only")
HVACMode.OFF = HVACModeType("off")

climate.HVACMode = HVACMode
sys.modules["homeassistant.components.climate"] = climate

climate_const = types.ModuleType("homeassistant.components.climate.const")
climate_const.FAN_AUTO = "auto"
climate_const.FAN_LOW = "low"
climate_const.HVACMode = HVACMode
climate_const.ClimateEntityFeature = types.SimpleNamespace(
    TURN_OFF=1,
    TURN_ON=2,
    TARGET_TEMPERATURE=4,
    FAN_MODE=8,
)
sys.modules["homeassistant.components.climate.const"] = climate_const

const.Platform = types.SimpleNamespace(
    NUMBER="number",
    SELECT="select",
    SENSOR="sensor",
    CLIMATE="climate",
    BUTTON="button",
)

helpers_module = types.ModuleType("homeassistant.helpers")
helpers_module.__path__ = []
sys.modules["homeassistant.helpers"] = helpers_module

device_registry = types.ModuleType("homeassistant.helpers.device_registry")

def async_get(hass):
    return {}

def async_entries_for_config_entry(device_registry, entry_id):
    return []

def async_remove_device(device_id):
    return None

device_registry.async_get = async_get
device_registry.async_entries_for_config_entry = async_entries_for_config_entry
device_registry.async_remove_device = async_remove_device
sys.modules["homeassistant.helpers.device_registry"] = device_registry

config_validation = types.ModuleType("homeassistant.helpers.config_validation")
config_validation.string = str
config_validation.Coerce = lambda t: t
config_validation.Range = lambda **kwargs: lambda x: x
sys.modules["homeassistant.helpers.config_validation"] = config_validation

util = types.ModuleType("homeassistant.util")
sys.modules["homeassistant.util"] = util

unit_conversion = types.ModuleType("homeassistant.util.unit_conversion")

class TemperatureConverter:
    VALID_UNITS = {UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT}

    @staticmethod
    def convert(value: float, from_unit: str, to_unit: str) -> float:
        if from_unit == to_unit:
            return value
        if from_unit == UnitOfTemperature.CELSIUS and to_unit == UnitOfTemperature.FAHRENHEIT:
            return value * 9.0 / 5.0 + 32.0
        if from_unit == UnitOfTemperature.FAHRENHEIT and to_unit == UnitOfTemperature.CELSIUS:
            return (value - 32.0) * 5.0 / 9.0
        return value

unit_conversion.TemperatureConverter = TemperatureConverter
sys.modules["homeassistant.util.unit_conversion"] = unit_conversion

# Minimal stub for update coordinator imports if imported indirectly.
helpers_update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

class DataUpdateCoordinator:
    def __init__(self, hass=None, logger=None, name=None, update_interval=None, always_update=False):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.always_update = always_update
        self.data = None
        self._listeners = []

    @classmethod
    def __class_getitem__(cls, item):
        return cls

    def async_update_listeners(self):
        for listener in list(self._listeners):
            listener()

    def async_add_listener(self, listener):
        self._listeners.append(listener)

helpers_update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
helpers_update_coordinator.UpdateFailed = Exception
sys.modules["homeassistant.helpers.update_coordinator"] = helpers_update_coordinator

helpers_event = types.ModuleType("homeassistant.helpers.event")
helpers_event.async_track_state_change_event = lambda hass, sensors, callback: None
sys.modules["homeassistant.helpers.event"] = helpers_event

# Stub more Home Assistant components used by additional tests.
class EntityBase:
    def __init__(self, *args, **kwargs):
        pass

    @property
    def unique_id(self):
        return getattr(self, "_attr_unique_id", None)

    @property
    def name(self):
        return getattr(self, "_attr_name", None) or getattr(self, "_name", None)

    @property
    def device_info(self):
        return getattr(self, "_attr_device_info", None)

    def async_write_ha_state(self):
        return None

    def async_on_remove(self, func):
        self._remove = func

button_module = types.ModuleType("homeassistant.components.button")
class ButtonEntity(EntityBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
button_module.ButtonEntity = ButtonEntity
sys.modules["homeassistant.components.button"] = button_module

number_module = types.ModuleType("homeassistant.components.number")
class NumberEntity(EntityBase):
    def __init__(self, *args, **kwargs):
        if args:
            self.coordinator = args[0]
        elif "coordinator" in kwargs:
            self.coordinator = kwargs["coordinator"]
        super().__init__(*args, **kwargs)

class RestoreNumber(EntityBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def async_added_to_hass(self):
        return None

    async def async_get_last_number_data(self):
        return None

number_module.NumberEntity = NumberEntity
number_module.RestoreNumber = RestoreNumber
sys.modules["homeassistant.components.number"] = number_module

number_const = types.ModuleType("homeassistant.components.number.const")
class NumberDeviceClass:
    TEMPERATURE = "temperature"
class NumberMode:
    SLIDER = "slider"
number_const.NumberDeviceClass = NumberDeviceClass
number_const.NumberMode = NumberMode
sys.modules["homeassistant.components.number.const"] = number_const

select_module = types.ModuleType("homeassistant.components.select")
class SelectEntity(EntityBase):
    def __init__(self, *args, **kwargs):
        if args:
            self.coordinator = args[0]
        elif "coordinator" in kwargs:
            self.coordinator = kwargs["coordinator"]
        super().__init__(*args, **kwargs)
select_module.SelectEntity = SelectEntity
sys.modules["homeassistant.components.select"] = select_module

sensor_module = types.ModuleType("homeassistant.components.sensor")
class SensorEntity(EntityBase):
    def __init__(self, *args, **kwargs):
        if args:
            self.coordinator = args[0]
        elif "coordinator" in kwargs:
            self.coordinator = kwargs["coordinator"]
        super().__init__(*args, **kwargs)

    async def async_added_to_hass(self):
        return None
sensor_module.SensorEntity = SensorEntity
sensor_module.SensorDeviceClass = types.SimpleNamespace(TEMPERATURE="temperature", HUMIDITY="humidity", BATTERY="battery")
sensor_module.SensorStateClass = types.SimpleNamespace(MEASUREMENT="measurement")
sys.modules["homeassistant.components.sensor"] = sensor_module

sensor_const = types.ModuleType("homeassistant.components.sensor.const")
sensor_const.SensorDeviceClass = sensor_module.SensorDeviceClass
sensor_const.SensorStateClass = sensor_module.SensorStateClass
sys.modules["homeassistant.components.sensor.const"] = sensor_const

restore_state = types.ModuleType("homeassistant.helpers.restore_state")
class RestoreEntity:
    async def async_added_to_hass(self):
        pass
    async def async_get_last_state(self):
        return None
    async def async_get_last_number_data(self):
        return None
restore_state.RestoreEntity = RestoreEntity
sys.modules["homeassistant.helpers.restore_state"] = restore_state

selector_module = types.ModuleType("homeassistant.helpers.selector")
class TextSelector:
    def __init__(self, config):
        self.config = config
class TextSelectorConfig:
    def __init__(self, type=None):
        self.type = type
class TextSelectorType:
    TEXT = "text"
class NumberSelector:
    def __init__(self, config):
        self.config = config
class NumberSelectorConfig:
    def __init__(self, min=None, max=None, step=None, mode=None):
        self.min = min
        self.max = max
        self.step = step
        self.mode = mode
class NumberSelectorMode:
    BOX = "box"
class SelectSelector:
    def __init__(self, config):
        self.config = config
class SelectSelectorConfig:
    def __init__(self, options=None, multiple=None, mode=None, translation_key=None):
        self.options = options
        self.multiple = multiple
        self.mode = mode
        self.translation_key = translation_key
class SelectSelectorMode:
    DROPDOWN = "dropdown"
    LIST = "list"
class EntitySelector:
    def __init__(self, config):
        self.config = config
class EntitySelectorConfig:
    def __init__(self, domain=None, device_class=None, multiple=False):
        self.domain = domain
        self.device_class = device_class
        self.multiple = multiple
class BooleanSelector:
    def __init__(self):
        pass
selector_module.TextSelector = TextSelector
selector_module.TextSelectorConfig = TextSelectorConfig
selector_module.TextSelectorType = TextSelectorType
selector_module.NumberSelector = NumberSelector
selector_module.NumberSelectorConfig = NumberSelectorConfig
selector_module.NumberSelectorMode = NumberSelectorMode
selector_module.SelectSelector = SelectSelector
selector_module.SelectSelectorConfig = SelectSelectorConfig
selector_module.SelectSelectorMode = SelectSelectorMode
selector_module.EntitySelector = EntitySelector
selector_module.EntitySelectorConfig = EntitySelectorConfig
selector_module.BooleanSelector = BooleanSelector
sys.modules["homeassistant.helpers.selector"] = selector_module

# minimal data entry flow stub used by config_flow.py
data_entry_flow = types.ModuleType("homeassistant.data_entry_flow")
def section(schema, options):
    return {"schema": schema, "options": options}
data_entry_flow.section = section
data_entry_flow.FlowResult = dict
sys.modules["homeassistant.data_entry_flow"] = data_entry_flow

# extend HA const stub with entity categories and percentage
const.PERCENTAGE = "%"
const.EntityCategory = types.SimpleNamespace(CONFIG="config", DIAGNOSTIC="diagnostic")

# extend climate module with entity base classes and features
class ClimateEntity:
    pass
climate.ClimateEntity = ClimateEntity
climate.ClimateEntityFeature = types.SimpleNamespace(
    TURN_OFF=1,
    TURN_ON=2,
    TARGET_TEMPERATURE=4,
    FAN_MODE=8,
)
sys.modules["homeassistant.components.climate"] = climate

# CoordinatorEntity stub for classifier inheritance
class CoordinatorEntity:
    def __init__(self, coordinator=None):
        self.coordinator = coordinator
    def async_write_ha_state(self):
        pass
    def async_on_remove(self, func):
        self._remove = func
helpers_update_coordinator.CoordinatorEntity = CoordinatorEntity
sys.modules["homeassistant.helpers.update_coordinator"] = helpers_update_coordinator

# Config flow base classes
class ConfigFlow:
    def __init__(self):
        self.context = {}
        self.hass = None
    def async_show_form(self, step_id=None, data_schema=None, errors=None, description_placeholders=None):
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
            "description_placeholders": description_placeholders or {},
        }
    def async_create_entry(self, title, data):
        return {"type": "create_entry", "title": title, "data": data}
    def async_update_reload_and_abort(self, entry, data):
        return {"type": "abort_reload", "data": data}
    def async_abort(self, reason=None):
        return {"type": "abort", "reason": reason}
    def async_set_unique_id(self, unique_id):
        self.unique_id = unique_id
    def _abort_if_unique_id_configured(self):
        return None
    def add_suggested_values_to_schema(self, schema, current_data):
        return schema

class OptionsFlow:
    def __init__(self, config_entry=None):
        self.config_entry = config_entry
        self.hass = None
    def async_show_menu(self, step_id=None, menu_options=None):
        return {"type": "menu", "step_id": step_id, "menu_options": menu_options}
    def async_create_entry(self, title, data):
        return {"type": "create_entry", "title": title, "data": data}

config_entries.ConfigFlow = ConfigFlow
config_entries.OptionsFlow = OptionsFlow
sys.modules["homeassistant.config_entries"] = config_entries
