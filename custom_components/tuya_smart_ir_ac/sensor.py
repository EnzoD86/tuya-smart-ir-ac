from homeassistant.core import callback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass
)
from homeassistant.const import (
    EVENT_STATE_CHANGED,
    PERCENTAGE,
    UnitOfTemperature
)
from .const import (
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR
)
from .helpers import valid_sensor_state
from .entity import TuyaEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    temperature_sensor = config_entry.data.get(CONF_TEMPERATURE_SENSOR, None)
    if temperature_sensor:
        async_add_entities([TuyaTemperatureSensor(config_entry.data)])
        
    humidity_sensor = config_entry.data.get(CONF_HUMIDITY_SENSOR, None)
    if humidity_sensor:
        async_add_entities([TuyaHumiditySensor(config_entry.data)])


class TuyaTemperatureSensor(SensorEntity, TuyaEntity):
    def __init__(self, config):
        TuyaEntity.__init__(self, config)

    @property
    def has_entity_name(self):
        return True

    @property
    def unique_id(self):
        return self.temperature_sensor_unique_id()

    @property
    def device_info(self):
        return self.tuya_device_info()

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property    
    def native_unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    @property
    def native_value(self):
        sensor_state = self.hass.states.get(self._temperature_sensor) if self._temperature_sensor is not None else None
        return float(sensor_state.state) if valid_sensor_state(sensor_state) else None

    async def async_added_to_hass(self):
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._async_handle_event)

    @callback
    async def _async_handle_event(self, event):
        if event.data.get("entity_id") == self._temperature_sensor:
            self.async_write_ha_state()


class TuyaHumiditySensor(SensorEntity, TuyaEntity):
    def __init__(self, config):
        TuyaEntity.__init__(self, config)

    @property
    def has_entity_name(self):
        return True

    @property
    def unique_id(self):
        return self.humidity_sensor_unique_id()

    @property
    def device_info(self):
        return self.tuya_device_info()

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property    
    def native_unit_of_measurement(self):
        return PERCENTAGE

    @property
    def native_value(self):
        sensor_state = self.hass.states.get(self._humidity_sensor) if self._humidity_sensor is not None else None
        return float(sensor_state.state) if valid_sensor_state(sensor_state) else None

    async def async_added_to_hass(self):
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._async_handle_event)

    @callback
    async def _async_handle_event(self, event):
        if event.data.get("entity_id") == self._humidity_sensor:
            self.async_write_ha_state()