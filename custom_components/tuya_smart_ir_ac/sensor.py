from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass
)
from homeassistant.const import (
    EVENT_STATE_CHANGED,
    PERCENTAGE,
    ATTR_ENTITY_ID,
    UnitOfTemperature,
    EntityCategory
)
from .const import (
    DOMAIN,
    SENSOR_COORDINATOR,
    DEVICE_TYPE_CLIMATE,
    DEVICE_TYPE_SENSOR,
    CONF_DEVICE_TYPE,
    CONF_EXTRA_SENSORS,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_SENSOR_TYPES,
    DEFAULT_EXTRA_SENSORS,
    SENSOR_TEMPERATURE,
    SENSOR_HUMIDITY,
    SENSOR_BATTERY
)
from .entity import TuyaClimateEntity, TuyaSensorEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    device_type = config_entry.data.get(CONF_DEVICE_TYPE, None)
    if device_type == DEVICE_TYPE_CLIMATE:
        extra_sensors = config_entry.data.get(CONF_EXTRA_SENSORS, DEFAULT_EXTRA_SENSORS)
        if extra_sensors:
            temperature_sensor = config_entry.data.get(CONF_TEMPERATURE_SENSOR, None)
            if temperature_sensor:
                async_add_entities([TuyaClimateTemperatureSensor(config_entry.data)])
                
            humidity_sensor = config_entry.data.get(CONF_HUMIDITY_SENSOR, None)
            if humidity_sensor:
                async_add_entities([TuyaClimateHumiditySensor(config_entry.data)])
    elif device_type == DEVICE_TYPE_SENSOR:
        coordinator = hass.data.get(DOMAIN).get(SENSOR_COORDINATOR)
        sensor_types = config_entry.data.get(CONF_SENSOR_TYPES, [])

        if SENSOR_TEMPERATURE in sensor_types:
            async_add_entities([TuyaSensorTemperatureSensor(config_entry.data, coordinator)])

        if SENSOR_HUMIDITY in sensor_types:
            async_add_entities([TuyaSensorHumiditySensor(config_entry.data, coordinator)])

        if SENSOR_BATTERY in sensor_types:
            async_add_entities([TuyaSensorBatterySensor(config_entry.data, coordinator)])


class TuyaClimateTemperatureSensor(SensorEntity, TuyaClimateEntity):
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


class TuyaClimateHumiditySensor(SensorEntity, TuyaClimateEntity):
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
            
            
class TuyaSensorTemperatureSensor(SensorEntity, CoordinatorEntity, TuyaSensorEntity):
    def __init__(self, config, coordinator):
        TuyaSensorEntity.__init__(self, config, SENSOR_TEMPERATURE)
        super().__init__(coordinator, context=self._device_id)

    @property
    def has_entity_name(self):
        return True

    @property
    def unique_id(self):
        return self.tuya_unique_id()

    @property
    def device_info(self):
        return self.tuya_device_info()

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE
        
    @property
    def available(self):
        return self.coordinator.is_available(self._device_id)

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property    
    def native_unit_of_measurement(self):
        return self._unit_of_measurement

    @callback
    def _handle_coordinator_update(self):
        data = self.coordinator.data.get(self._device_id)
        if data:
            self._attr_native_value = data.temp_current
            self.async_write_ha_state()


class TuyaSensorHumiditySensor(SensorEntity, CoordinatorEntity, TuyaSensorEntity):
    def __init__(self, config, coordinator):
        TuyaSensorEntity.__init__(self, config, SENSOR_HUMIDITY)
        super().__init__(coordinator, context=self._device_id)

    @property
    def has_entity_name(self):
        return True

    @property
    def unique_id(self):
        return self.tuya_unique_id()

    @property
    def device_info(self):
        return self.tuya_device_info()
        
    @property
    def available(self):
        return self.coordinator.is_available(self._device_id)

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property    
    def native_unit_of_measurement(self):
        return PERCENTAGE

    @callback
    def _handle_coordinator_update(self):
        data = self.coordinator.data.get(self._device_id)
        if data:
            self._attr_native_value = data.humidity_value
            self.async_write_ha_state()


class TuyaSensorBatterySensor(SensorEntity, CoordinatorEntity, TuyaSensorEntity):
    def __init__(self, config, coordinator):
        TuyaSensorEntity.__init__(self, config, SENSOR_BATTERY)
        super().__init__(coordinator, context=self._device_id)

    @property
    def has_entity_name(self):
        return True

    @property
    def unique_id(self):
        return self.tuya_unique_id()

    @property
    def device_info(self):
        return self.tuya_device_info()
        
    @property
    def available(self):
        return self.coordinator.is_available(self._device_id)

    @property
    def device_class(self):
        return SensorDeviceClass.BATTERY
    
    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT
    
    @property
    def entity_category(self):
        return EntityCategory.DIAGNOSTIC

    @property    
    def native_unit_of_measurement(self):
        return PERCENTAGE

    @callback
    def _handle_coordinator_update(self):
        data = self.coordinator.data.get(self._device_id)
        if data:
            self._attr_native_value = data.battery_state
            self.async_write_ha_state()