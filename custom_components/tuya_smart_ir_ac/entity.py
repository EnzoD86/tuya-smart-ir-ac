import logging
from homeassistant.const import (
    Platform,
    CONF_NAME
)
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_LOW,
    HVACMode
)
from .const import (
    DOMAIN,
    MANUFACTURER,
    CONF_INFRARED_ID,
    CONF_CLIMATE_ID,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_TEMP_MIN,
    CONF_TEMP_MAX,
    CONF_TEMP_STEP,
    CONF_HVAC_MODES,
    CONF_FAN_MODES,
    CONF_TEMP_HVAC_MODE,
    CONF_FAN_HVAC_MODE,
    CONF_COMPATIBILITY_OPTIONS,
    CONF_HVAC_POWER_ON,
    CONF_DRY_MIN_TEMP,
    CONF_DRY_MIN_FAN,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_PRECISION,
    DEFAULT_HVAC_MODES,
    DEFAULT_FAN_MODES,
    DEFAULT_TEMP_HVAC_MODE,
    DEFAULT_FAN_HVAC_MODE,
    DEFAULT_TEMP_HVAC_MODES,
    DEFAULT_HVAC_POWER_ON,
    DEFAULT_DRY_MIN_TEMP,
    DEFAULT_DRY_MIN_FAN
)

_LOGGER = logging.getLogger(__package__)


class TuyaEntity():
    def __init__(self, config, registry=None):
        self._registry = registry
        self._infrared_id = config.get(CONF_INFRARED_ID)
        self._climate_id = config.get(CONF_CLIMATE_ID)
        self._name = config.get(CONF_NAME)
        self._temperature_sensor = config.get(CONF_TEMPERATURE_SENSOR, None)
        self._humidity_sensor = config.get(CONF_HUMIDITY_SENSOR, None)
        self._min_temp = config.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP)
        self._max_temp = config.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP)
        self._temp_step = config.get(CONF_TEMP_STEP, DEFAULT_PRECISION)
        self._hvac_modes = config.get(CONF_HVAC_MODES, DEFAULT_HVAC_MODES)
        self._fan_modes = config.get(CONF_FAN_MODES, DEFAULT_FAN_MODES)
        self._temp_hvac_mode = config.get(CONF_TEMP_HVAC_MODE, DEFAULT_TEMP_HVAC_MODE)
        self._fan_hvac_mode = config.get(CONF_FAN_HVAC_MODE, DEFAULT_FAN_HVAC_MODE)
        self._hvac_power_on = config.get(CONF_COMPATIBILITY_OPTIONS, {}).get(CONF_HVAC_POWER_ON, DEFAULT_HVAC_POWER_ON)
        self._dry_min_temp = config.get(CONF_COMPATIBILITY_OPTIONS, {}).get(CONF_DRY_MIN_TEMP, DEFAULT_DRY_MIN_TEMP)
        self._dry_min_fan = config.get(CONF_COMPATIBILITY_OPTIONS, {}).get(CONF_DRY_MIN_FAN, DEFAULT_DRY_MIN_FAN)

    def tuya_device_info(self):
        return {
            "name": self._name,
            "identifiers": {(DOMAIN, self._climate_id)},
            "via_device": (DOMAIN, self._infrared_id),
            "manufacturer": MANUFACTURER
        }

    def climate_unique_id(self):
        return f"{self._infrared_id}_{self._climate_id}"

    def number_unique_id(self, temp_hvac_mode):
        return f"{self.climate_unique_id()}_{CONF_TEMP_HVAC_MODE}_{temp_hvac_mode}"

    def select_unique_id(self):
        return f"{self.climate_unique_id()}_{CONF_FAN_HVAC_MODE}"

    def load_optional_entities(self):
        self._hvac_temp_entities = self.load_hvac_temp_entities()
        self._hvac_fan_entity = self.load_hvac_fan_entity()

    def load_hvac_temp_entities(self):
        hvac_temp_entities = {}
        if self._temp_hvac_mode:
            for hvac_mode in DEFAULT_TEMP_HVAC_MODES:
                entity_id = self._registry.async_get_entity_id(Platform.NUMBER, DOMAIN, self.number_unique_id(hvac_mode))
                if entity_id:
                    hvac_temp_entities[hvac_mode] = entity_id
        return hvac_temp_entities

    def load_hvac_fan_entity(self):
        hvac_fan_entity = None
        if self._fan_hvac_mode:
            entity_id = self._registry.async_get_entity_id(Platform.SELECT, DOMAIN, self.select_unique_id())
            if entity_id:
                hvac_fan_entity = entity_id
        return hvac_fan_entity

    def get_hvac_temperature(self, hvac_mode):
        if hvac_mode in self._hvac_temp_entities:
            entity_id = self._hvac_temp_entities.get(hvac_mode)
            number_state = self.hass.states.get(entity_id)
            return float(number_state.state)

        if hvac_mode is HVACMode.DRY and self._dry_min_temp:
            return DEFAULT_MIN_TEMP

        if self.target_temperature < self._min_temp:
            return self._min_temp

        return self.target_temperature

    def get_hvac_fan_mode(self, hvac_mode):
        if hvac_mode is HVACMode.DRY:
            return FAN_LOW if self._dry_min_fan else FAN_AUTO

        if self._hvac_fan_entity is not None:
            select_state = self.hass.states.get(self._hvac_fan_entity)
            return select_state.state

        return self.fan_mode