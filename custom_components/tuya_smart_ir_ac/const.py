from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    HVACMode
)

DOMAIN = "tuya_smart_ir_ac"
TUYA_API_CLIENT = "tuya_api_client"

CONF_ACCESS_ID = "access_id"
CONF_ACCESS_SECRET = "access_secret"
CONF_INFRARED_ID = "infrared_id"
CONF_CLIMATE_ID = "climate_id"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_TEMP_MIN = "min_temp"
CONF_TEMP_MAX = "max_temp"
CONF_TEMP_STEP = "temp_step"
CONF_TUYA_COUNTRY = "country"

DEFAULT_PRECISION = 1.0
DEFAULT_TUYA_COUNTRY = "EU"

TUYA_ENDPOINTS = {
    "EU": "https://openapi.tuyaeu.com",
    "US": "https://openapi.tuyaus.com",
    "IN": "https://openapi.tuyain.com",
    "CN": "https://openapi.tuyacn.com"
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