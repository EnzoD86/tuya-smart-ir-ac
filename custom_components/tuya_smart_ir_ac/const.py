from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVACMode,
)
from homeassistant.components.climate.const import (
    PRESET_NONE,
    PRESET_HOME,
    PRESET_SLEEP,
    PRESET_ECO,
    PRESET_COMFORT,
    PRESET_AWAY,
)
from homeassistant.const import Platform, UnitOfTemperature

# Core Integration Setup
DOMAIN = "tuya_smart_ir_ac"
MANUFACTURER = "Tuya"
CLIMATE_MODEL = "IR Air Conditioning"
GENERIC_MODEL = "IR Remote Control"
SENSOR_MODEL = "T & H Sensor"
TEST_MODE = True

# Platforms supported by this integration
PLATFORMS = [
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.CLIMATE,
    Platform.BUTTON,
]

# Timing parameters (seconds)
UPDATE_INTERVAL = 300
UPDATE_TIMEOUT = 15

# Sub-device Type Categories (stored inside ConfigEntry options)
DEVICE_TYPE_CLIMATES = "climates"
DEVICE_TYPE_GENERICS = "generics"
DEVICE_TYPE_SENSORS = "sensors"

# Sub-Entity Definitions
ENTITY_HVAC_MODE = "hvac_mode"
ENTITY_FAN_MODE = "fan_mode"
ENTITY_TEMPERATURE_SETPOINT = "temp_setpoint"
ENTITY_CURRENT_TEMPERATURE = "current_temperature"
ENTITY_CURRENT_HUMIDITY = "current_humidity"
ENTITY_SENSOR_TEMPERATURE = "temperature"
ENTITY_SENSOR_HUMIDITY = "humidity"
ENTITY_SENSOR_BATTERY = "battery"

# Configuration Flow Keys
CONF_ACCESS_ID = "access_id"
CONF_ACCESS_SECRET = "access_secret"
CONF_TUYA_COUNTRY = "country"
CONF_ENABLE_PULSAR = "enable_pulsar"
CONF_CLIMATE_UPDATE_INTERVAL = "climate_update_interval"
CONF_SENSOR_UPDATE_INTERVAL = "sensor_update_interval"
CONF_INFRARED_ID = "infrared_id"
CONF_DEVICE_ID = "device_id"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_TEMP_MIN = "min_temp"
CONF_TEMP_MAX = "max_temp"
CONF_TEMP_STEP = "temp_step"
CONF_HVAC_MODES = "hvac_modes"
CONF_FAN_MODES = "fan_modes"
CONF_PRESET_MODES = "preset_modes"
CONF_HVAC_PRESETS = "hvac_presets"
CONF_GLOBAL_PRESETS = "global_presets"
CONF_OPTIONAL_ENTITIES = "optional_entities"
CONF_COMPATIBILITY_OPTIONS = "compatibility_options"
CONF_HVAC_POWER_ON = "hvac_power_on"
CONF_TEMP_POWER_ON = "temp_power_on"
CONF_FAN_POWER_ON = "fan_power_on"
CONF_DRY_MIN_TEMP = "dry_min_temp"
CONF_DRY_MIN_FAN = "dry_min_fan"
CONF_CUSTOM_POWER_ON = "custom_power_on"
CONF_SENSOR_TYPES = "sensor_types"
CONF_TEMP_UNIT = "temp_unit"

# Power-On Modes
POWER_ON_NEVER = "never"
POWER_ON_ALWAYS = "always"
POWER_ON_ONLY_OFF = "only_off"

# Presets
PRESET_TEMP_HVAC_MODE = "temp_hvac_mode"
PRESET_FAN_HVAC_MODE = "fan_hvac_mode"

# Integration Defaults
DEFAULT_MIN_TEMP = 16
DEFAULT_MAX_TEMP = 30
DEFAULT_PRECISION = 1.0
DEFAULT_HVAC_POWER_ON = POWER_ON_NEVER
DEFAULT_TEMP_POWER_ON = POWER_ON_NEVER
DEFAULT_FAN_POWER_ON = POWER_ON_NEVER
DEFAULT_DRY_MIN_TEMP = False
DEFAULT_DRY_MIN_FAN = False
DEFAULT_ENABLE_PULSAR = False

# Climate default fallbacks
DEFAULT_POWER = False
DEFAULT_HVAC_MODE = HVACMode.OFF
DEFAULT_TEMPERATURE = 25.0
DEFAULT_FAN_MODE = FAN_AUTO

# Sensor defaults fallbacks
DEFAULT_TEMP_UNIT = "c"
DEFAULT_CURRENT_TEMPERATURE = 25
DEFAULT_CURRENT_HUMIDITY = 50
DEFAULT_BATTERY_STATE = 50

DEFAULT_GLOBAL_PRESETS = {
    PRESET_HOME: {
        HVACMode.COOL: {"temp": 26.0, "fan": FAN_AUTO},
        HVACMode.HEAT: {"temp": 21.0, "fan": FAN_AUTO}
    },
    PRESET_SLEEP: {
        HVACMode.COOL: {"temp": 27.0, "fan": FAN_LOW},
        HVACMode.HEAT: {"temp": 20.0, "fan": FAN_LOW}
    },
    PRESET_ECO: {
        HVACMode.COOL: {"temp": 27.0, "fan": FAN_MEDIUM},
        HVACMode.HEAT: {"temp": 20.0, "fan": FAN_MEDIUM}
    },
    PRESET_COMFORT: {
        HVACMode.COOL: {"temp": 25.0, "fan": FAN_MEDIUM},
        HVACMode.HEAT: {"temp": 22.0, "fan": FAN_MEDIUM}
    },
    PRESET_AWAY: {
        HVACMode.COOL: {"temp": 28.0, "fan": FAN_LOW},
        HVACMode.HEAT: {"temp": 19.0, "fan": FAN_LOW}
    }
}

# Frontend Selection/Validation Lists
SUPPORTED_POWER_ON_MODES = [
    POWER_ON_NEVER,
    POWER_ON_ALWAYS,
    POWER_ON_ONLY_OFF,
]

SUPPORTED_HVAC_MODES = [
    HVACMode.AUTO,
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.OFF,
]

SUPPORTED_FAN_MODES = [
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
]

SUPPORTED_PRESET_MODES = [
    PRESET_NONE,
    PRESET_HOME,
    PRESET_SLEEP,
    PRESET_ECO,
    PRESET_COMFORT,    
    PRESET_AWAY,
]

SUPPORTED_HVAC_PRESETS = [
    PRESET_TEMP_HVAC_MODE,
    PRESET_FAN_HVAC_MODE,
]

SUPPORTED_TEMP_HVAC_MODES = [
    HVACMode.AUTO,
    HVACMode.COOL,
    HVACMode.HEAT,
]

SUPPORTED_OPTIONAL_ENTITIES = [
    ENTITY_HVAC_MODE,
    ENTITY_FAN_MODE,
    ENTITY_TEMPERATURE_SETPOINT,
    ENTITY_CURRENT_TEMPERATURE,
    ENTITY_CURRENT_HUMIDITY,
]

# Translation keys
TRANSLATION_KEY_HVAC_MODE = "hvac_mode"
TRANSLATION_KEY_FAN_MODE = "fan_mode"
TRANSLATION_KEY_TEMPERATURE = "temperature"
TRANSLATION_KEY_HVAC_MODES = "hvac_modes"
TRANSLATION_KEY_FAN_MODES = "fan_modes"
TRANSLATION_KEY_PRESET_MODES = "presets_modes"
TRANSLATION_KEY_COUNTRIES = "countries"
TRANSLATION_KEY_HVAC_PRESETS = "hvac_presets"
TRANSLATION_KEY_OPTIONAL_ENTITIES = "optional_entities"
TRANSLATION_KEY_POWER_ON_MODES = "power_on_modes"


# Tuya API Mappings
BATTERY_LEVELS = {
    "high": 100,
    "middle": 50,
    "low": 10,
}

TUYA_TEMP_UNIT = {
    "c": UnitOfTemperature.CELSIUS,
    "f": UnitOfTemperature.FAHRENHEIT,
}

TUYA_HVAC_MODES = {
    "0": HVACMode.COOL,
    "1": HVACMode.HEAT,
    "2": HVACMode.AUTO,
    "3": HVACMode.FAN_ONLY,
    "4": HVACMode.DRY,
    "5": HVACMode.OFF,
}

TUYA_FAN_MODES = {
    "0": FAN_AUTO,
    "1": FAN_LOW,
    "2": FAN_MEDIUM,
    "3": FAN_HIGH,
}

TUYA_API_ENDPOINTS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "in": "https://openapi.tuyain.com",
    "cn": "https://openapi.tuyacn.com",
    "sg": "https://openapi-sg.iotbing.com",
}

TUYA_PULSAR_ENDPOINTS = {
    "eu": "wss://mqe.tuyaeu.com:8285/",
    "us": "wss://mqe.tuyaus.com:8285/",
    "in": "wss://mqe.tuyain.com:8285/",
    "cn": "wss://mqe.tuyacn.com:8285/",
    "sg": "wss://mqe-sg.iotbing.com:8285/",
}

# Global normalization mapping for non-standard Tuya Data Point codes
TUYA_CODE_MAPPING = {
    "va_temperature": "temp_current",
    "va_humidity": "humidity_value",
}