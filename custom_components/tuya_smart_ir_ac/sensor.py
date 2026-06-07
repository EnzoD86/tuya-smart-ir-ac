import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HUMIDITY_SENSOR,
    CONF_OPTIONAL_ENTITIES,
    CONF_SENSOR_TYPES,
    CONF_TEMPERATURE_SENSOR,
    DEVICE_TYPE_CLIMATES,
    DEVICE_TYPE_SENSORS,
    ENTITY_CURRENT_HUMIDITY,
    ENTITY_CURRENT_TEMPERATURE,
    ENTITY_SENSOR_BATTERY,
    ENTITY_SENSOR_HUMIDITY,
    ENTITY_SENSOR_TEMPERATURE,
)
from .entity import TuyaClimateEntity, TuyaSensorEntity
from .models import HubConfigEntry, RuntimeData

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: HubConfigEntry, 
    async_add_entities
) -> None:
    """Set up Tuya environmental and virtual sensors from a config entry."""
    active_entities = []
    runtime_data = config_entry.runtime_data

    climates_data = config_entry.options.get(DEVICE_TYPE_CLIMATES, [])
    for data in climates_data:
        optional_entities = data.get(CONF_OPTIONAL_ENTITIES, [])
        if optional_entities:
            if ENTITY_CURRENT_TEMPERATURE in optional_entities and data.get(CONF_TEMPERATURE_SENSOR):
                active_entities.append(TuyaClimateTemperatureSensor(data, runtime_data))

            if ENTITY_CURRENT_HUMIDITY in optional_entities and data.get(CONF_HUMIDITY_SENSOR):
                active_entities.append(TuyaClimateHumiditySensor(data, runtime_data))

    sensors_data = config_entry.options.get(DEVICE_TYPE_SENSORS, [])
    for data in sensors_data:
        sensor_types = data.get(CONF_SENSOR_TYPES, [])

        if ENTITY_SENSOR_TEMPERATURE in sensor_types:
            active_entities.append(TuyaSensorTemperatureSensor(data, runtime_data))

        if ENTITY_SENSOR_HUMIDITY in sensor_types:
            active_entities.append(TuyaSensorHumiditySensor(data, runtime_data))

        if ENTITY_SENSOR_BATTERY in sensor_types:
            active_entities.append(TuyaSensorBatterySensor(data, runtime_data))

    if active_entities:
        _LOGGER.debug(
            "[%s] Initialized %d sensor platform entities", 
            config_entry.title, 
            len(active_entities)
        )
        async_add_entities(active_entities)


class TuyaClimateTemperatureSensor(SensorEntity, TuyaClimateEntity):
    """Virtual temperature sensor tracking an external climate reference entity."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData) -> None:
        """Initialize the climate virtual temperature sensor."""
        TuyaClimateEntity.__init__(self, config_data, runtime_data, ENTITY_CURRENT_TEMPERATURE)
        
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement dynamically once hass is available."""
        return self.get_temperature_unit_of_measurement()

    @property
    def native_value(self) -> float | None:
        """Return the current temperature dynamic state value from the tracked entity."""
        return self.get_temperature_value()

    async def async_added_to_hass(self) -> None:
        """Register state tracker listener upon entity addition to Home Assistant."""
        self.async_track_sensor_states([self._temperature_sensor])

    @callback
    def _handle_sensor_state_change(self, event) -> None:
        """Trigger an internal state update when a monitored external sensor changes value."""
        if event.data.get("new_state") is not None:
            self.async_write_ha_state()


class TuyaClimateHumiditySensor(SensorEntity, TuyaClimateEntity):
    """Virtual humidity sensor tracking an external climate reference entity."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData) -> None:
        """Initialize the climate virtual humidity sensor."""
        TuyaClimateEntity.__init__(self, config_data, runtime_data, ENTITY_CURRENT_HUMIDITY)
        
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> float | None:
        """Return the current humidity dynamic state value from the tracked entity."""
        return self.get_humidity_value()

    async def async_added_to_hass(self) -> None:
        """Register state tracker listener upon entity addition to Home Assistant."""
        self.async_track_sensor_states([self._humidity_sensor])

    @callback
    def _handle_sensor_state_change(self, event) -> None:
        """Trigger an internal state update when a monitored external sensor changes value."""
        if event.data.get("new_state") is not None: 
            self.async_write_ha_state()
            

class TuyaSensorTemperatureSensor(SensorEntity, CoordinatorEntity, TuyaSensorEntity):
    """Temperature sensor entity updated via standalone Temperature/Humidity coordinator."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData) -> None:
        """Initialize the physical environmental temperature sensor."""
        TuyaSensorEntity.__init__(self, config_data, runtime_data, ENTITY_SENSOR_TEMPERATURE)
        super().__init__(runtime_data.sensor_coordinator)

        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = self._unit_of_measurement

    @property
    def native_value(self) -> float | None:
        """Fetch ambient temperature value directly from coordinator data cache."""
        return self._current_temperature

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle state changes notified by the Hub coordinator."""
        self.async_write_ha_state()


class TuyaSensorHumiditySensor(SensorEntity, CoordinatorEntity, TuyaSensorEntity):
    """Humidity sensor entity updated via standalone Temperature/Humidity coordinator."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData) -> None:
        """Initialize the physical environmental humidity sensor."""
        TuyaSensorEntity.__init__(self, config_data, runtime_data, ENTITY_SENSOR_HUMIDITY)
        super().__init__(runtime_data.sensor_coordinator)

        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> float | None:
        """Fetch ambient humidity value directly from coordinator data cache."""
        return self._current_humidity

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle state changes notified by the Hub coordinator."""
        self.async_write_ha_state()


class TuyaSensorBatterySensor(SensorEntity, CoordinatorEntity, TuyaSensorEntity):
    """Battery diagnostic sensor entity updated via standalone Temperature/Humidity coordinator."""

    def __init__(self, config_data: dict[str, Any], runtime_data: RuntimeData) -> None:
        """Initialize the physical environmental battery diagnostic sensor."""
        TuyaSensorEntity.__init__(self, config_data, runtime_data, ENTITY_SENSOR_BATTERY)
        super().__init__(runtime_data.sensor_coordinator)

        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> float | None:
        """Fetch environmental sensor battery charge percentage directly from coordinator data cache."""
        return self._battery_state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle state changes notified by the Hub coordinator."""
        self.async_write_ha_state()