from homeassistant.const import Platform
from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    HVACMode
)


DOMAIN = "tuya_smart_ir_ac"
MANUFACTURER = "Tuya"
CLIENT = "CLIENT"
CLIMATE_COORDINATOR = "CLIMATE_COORDINATOR"
SENSOR_COORDINATOR = "SENSOR_COORDINATOR"
SERVICE = "SERVICE"
FIRST_UPDATE = 5
UPDATE_INTERVAL = 60
UPDATE_TIMEOUT = 15
PLATFORMS = [Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.CLIMATE, Platform.BUTTON]

DEVICE_TYPE_CLIMATE = "climate"
DEVICE_TYPE_GENERIC = "generic"
DEVICE_TYPE_SENSOR = "sensor"

POWER_ON_NEVER = "never"
POWER_ON_ALWAYS = "always"
POWER_ON_ONLY_OFF = "only_off"

SENSOR_TEMPERATURE = "temperature"
SENSOR_HUMIDITY = "humidity"
SENSOR_BATTERY = "battery"

CONF_ACCESS_ID = "access_id"
CONF_ACCESS_SECRET = "access_secret"
CONF_TUYA_COUNTRY = "country"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_DEVICE_TYPE = "device_type"
CONF_INFRARED_ID = "infrared_id"
CONF_DEVICE_ID = "device_id"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_TEMP_MIN = "min_temp"
CONF_TEMP_MAX = "max_temp"
CONF_TEMP_STEP = "temp_step"
CONF_HVAC_MODES = "hvac_modes"
CONF_FAN_MODES = "fan_modes"
CONF_TEMP_HVAC_MODE = "temp_hvac_mode"
CONF_FAN_HVAC_MODE = "fan_hvac_mode"
CONF_EXTRA_SENSORS = "extra_sensors"
CONF_COMPATIBILITY_OPTIONS = "compatibility_options"
CONF_HVAC_POWER_ON = "hvac_power_on"
CONF_TEMP_POWER_ON = "temp_power_on"
CONF_FAN_POWER_ON = "fan_power_on"
CONF_DRY_MIN_TEMP = "dry_min_temp"
CONF_DRY_MIN_FAN = "dry_min_fan"
CONF_SENSOR_TYPES = "sensor_types"

DEFAULT_MIN_TEMP = 16
DEFAULT_MAX_TEMP = 30
DEFAULT_PRECISION = 1.0
DEFAULT_TEMP_HVAC_MODE = False
DEFAULT_FAN_HVAC_MODE = False
DEFAULT_EXTRA_SENSORS = False
DEFAULT_HVAC_POWER_ON = POWER_ON_NEVER
DEFAULT_TEMP_POWER_ON = POWER_ON_NEVER
DEFAULT_FAN_POWER_ON = POWER_ON_NEVER
DEFAULT_DRY_MIN_TEMP = False
DEFAULT_DRY_MIN_FAN = False

DEFAULT_DEVICE_TYPES = [
    DEVICE_TYPE_CLIMATE,
    DEVICE_TYPE_GENERIC,
    DEVICE_TYPE_SENSOR
]

DEFAULT_TEMP_HVAC_MODES = [
    HVACMode.AUTO,
    HVACMode.COOL,
    HVACMode.HEAT
]

DEFAULT_POWER_ON_MODES = [
    POWER_ON_NEVER,
    POWER_ON_ALWAYS,
    POWER_ON_ONLY_OFF
]

DEFAULT_HVAC_MODES = [
    HVACMode.AUTO,
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.OFF
]

DEFAULT_FAN_MODES = [
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH
]

BATTERY_LEVELS = {
    "high": 100,
    "middle": 50,
    "low": 10
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
    "3": FAN_HIGH
}

TUYA_ENDPOINTS = {
    "EU": "https://openapi.tuyaeu.com",
    "US": "https://openapi.tuyaus.com",
    "IN": "https://openapi.tuyain.com",
    "CN": "https://openapi.tuyacn.com",
    "SG": "https://openapi-sg.iotbing.com"
}