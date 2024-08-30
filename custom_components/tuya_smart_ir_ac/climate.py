import logging
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_LOW,
    HVACMode,
    ClimateEntityFeature
)
from homeassistant.const import (
    UnitOfTemperature, 
    STATE_UNKNOWN, 
    STATE_UNAVAILABLE,
    CONF_NAME
)
from .const import (
    DOMAIN,
    MANUFACTURER,
    COORDINATOR,
    CONF_INFRARED_ID,
    CONF_CLIMATE_ID,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_TEMP_MIN,
    CONF_TEMP_MAX,
    CONF_TEMP_STEP,
    CONF_HVAC_MODES,
    CONF_FAN_MODES,
    CONF_DRY_MIN_TEMP,
    CONF_DRY_MIN_FAN,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_PRECISION,
    DEFAULT_HVAC_MODES,
    DEFAULT_FAN_MODES,
    DEFAULT_DRY_MIN_TEMP,
    DEFAULT_DRY_MIN_FAN
)

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data.get(DOMAIN).get(COORDINATOR)
    async_add_entities([TuyaClimate(hass, config_entry.data, coordinator)])


class TuyaClimate(ClimateEntity, RestoreEntity, CoordinatorEntity):
    def __init__(self, hass, config, coordinator):
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
        self._dry_min_temp = config.get(CONF_DRY_MIN_TEMP, DEFAULT_DRY_MIN_TEMP)
        self._dry_min_fan = config.get(CONF_DRY_MIN_FAN, DEFAULT_DRY_MIN_FAN)

        super().__init__(coordinator, context=self._climate_id)

        self._hvac_mode = HVACMode.OFF
        self._target_temperature = 0
        self._fan_mode = FAN_AUTO

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"{self._infrared_id}_{self._climate_id}"

    @property
    def device_info(self):
        return {
            "name": self._name,
            "identifiers": {(DOMAIN, self._climate_id)},
            "via_device": (DOMAIN, self._infrared_id),
            "manufacturer": MANUFACTURER
        }
        
    @property
    def available(self):
        return self.coordinator.is_available(self._climate_id)

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def supported_features(self):
        return ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    @property
    def min_temp(self):
        return self._min_temp

    @property
    def max_temp(self):
        return self._max_temp

    @property
    def target_temperature_step(self):
        return self._temp_step

    @property
    def current_temperature(self):
        sensor_state = self.hass.states.get(self._temperature_sensor) if self._temperature_sensor is not None else None
        return float(sensor_state.state) if sensor_state and sensor_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE] else None

    @property
    def current_humidity(self):
        sensor_state = self.hass.states.get(self._humidity_sensor) if self._humidity_sensor is not None else None
        return float(sensor_state.state) if sensor_state and sensor_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE] else None

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return self._hvac_modes

    @property
    def fan_mode(self):
        return self._fan_mode

    @property
    def fan_modes(self):
        return self._fan_modes

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
            self._hvac_mode = last_state.state
            self._target_temperature = last_state.attributes.get("temperature")
            self._fan_mode = last_state.attributes.get("fan_mode")

    @callback
    def _handle_coordinator_update(self):
        data = self.coordinator.data.get(self._climate_id)
        if data:
            self._hvac_mode = data.hvac_mode if data.power else HVACMode.OFF
            self._target_temperature = data.temperature
            self._fan_mode = data.fan_mode
            self.async_write_ha_state()

    async def async_turn_on(self):
        _LOGGER.info(f"{self.entity_id} turn on")
        await self.coordinator.async_turn_on(self._infrared_id, self._climate_id)
        self._handle_coordinator_update()

    async def async_turn_off(self):
        _LOGGER.info(f"{self.entity_id} turn off")
        await self.coordinator.async_turn_off(self._infrared_id, self._climate_id)
        self._handle_coordinator_update()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get("temperature")
        if temperature is not None:
            _LOGGER.info(f"{self.entity_id} setting temperature to {temperature}")
            await self.coordinator.async_set_temperature(self._infrared_id, self._climate_id, temperature)
            self._handle_coordinator_update()

    async def async_set_fan_mode(self, fan_mode):
        _LOGGER.info(f"{self.entity_id} setting fan mode to {fan_mode}")
        await self.coordinator.async_set_fan_mode(self._infrared_id, self._climate_id, fan_mode)
        self._handle_coordinator_update()

    async def async_set_hvac_mode(self, hvac_mode):
        _LOGGER.info(f"{self.entity_id} setting hvac mode to {hvac_mode}")
        temperature = (DEFAULT_MIN_TEMP if hvac_mode is HVACMode.DRY and self._dry_min_temp 
                       else (self._min_temp if self._target_temperature < self._min_temp else self._target_temperature))
        fan_mode = FAN_LOW if hvac_mode is HVACMode.DRY and self._dry_min_fan else FAN_AUTO
        await self.coordinator.async_set_hvac_mode(self._infrared_id, self._climate_id, hvac_mode, temperature, fan_mode)
        self._handle_coordinator_update()