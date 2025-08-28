from homeassistant.core import callback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass
)
from homeassistant.const import (
    EVENT_STATE_CHANGED,
    PERCENTAGE,
    ATTR_ENTITY_ID
)
from .const import (
    DEVICE_TYPE_CLIMATE,
    CONF_DEVICE_TYPE,
    CONF_EXTRA_SENSORS,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    DEFAULT_EXTRA_SENSORS
)
from .entity import TuyaClimateEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    device_type = config_entry.data.get(CONF_DEVICE_TYPE, None)
    if device_type == DEVICE_TYPE_CLIMATE: 
        extra_sensors = config_entry.data.get(CONF_EXTRA_SENSORS, DEFAULT_EXTRA_SENSORS)
        if extra_sensors:
            temperature_sensor = config_entry.data.get(CONF_TEMPERATURE_SENSOR, None)
            if temperature_sensor:
                async_add_entities([TuyaTemperatureSensor(config_entry.data)])
                
            humidity_sensor = config_entry.data.get(CONF_HUMIDITY_SENSOR, None)
            if humidity_sensor:
                async_add_entities([TuyaHumiditySensor(config_entry.data)])


class TuyaTemperatureSensor(SensorEntity, TuyaClimateEntity):
    def __init__(self, config):
        TuyaClimateEntity.__init__(self, config)

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
        return self.get_temperature_unit_of_measurement()

    @property
    def native_value(self):
        return self.get_temperature_value()

    async def async_added_to_hass(self):
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._async_handle_event)

    @callback
    async def _async_handle_event(self, event):
        if event.data.get(ATTR_ENTITY_ID) == self._temperature_sensor:
            self.async_write_ha_state()


class TuyaHumiditySensor(SensorEntity, TuyaClimateEntity):
    def __init__(self, config):
        TuyaClimateEntity.__init__(self, config)

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
        return self.get_humidity_value()

    async def async_added_to_hass(self):
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._async_handle_event)

    @callback
    async def _async_handle_event(self, event):
        if event.data.get(ATTR_ENTITY_ID) == self._humidity_sensor:
            self.async_write_ha_state()