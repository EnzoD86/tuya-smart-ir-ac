from homeassistant.components.number import RestoreNumber
from homeassistant.components.number.const import (
    NumberDeviceClass,
    NumberMode
)
from homeassistant.const import (
    EntityCategory,
    UnitOfTemperature
)
from .const import (
    DEVICE_TYPE_CLIMATE,
    CONF_DEVICE_TYPE,
    CONF_TEMP_HVAC_MODE,
    DEFAULT_TEMP_HVAC_MODE,
    DEFAULT_TEMP_HVAC_MODES
)
from .helpers import valid_number_data
from .entity import TuyaClimateEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    device_type = config_entry.data.get(CONF_DEVICE_TYPE, None)
    if device_type == DEVICE_TYPE_CLIMATE: 
        temp_hvac_mode = config_entry.data.get(CONF_TEMP_HVAC_MODE, DEFAULT_TEMP_HVAC_MODE)
        if temp_hvac_mode:
            async_add_entities(TuyaNumber(config_entry.data, temp_hvac_mode) for temp_hvac_mode in DEFAULT_TEMP_HVAC_MODES)


class TuyaNumber(RestoreNumber, TuyaClimateEntity):
    def __init__(self, config, temp_hvac_mode):
        RestoreNumber.__init__(self)
        TuyaClimateEntity.__init__(self, config)
        self._temp_hvac_mode = temp_hvac_mode

    @property
    def has_entity_name(self):
        return True

    @property
    def translation_key(self):
        return f"{CONF_TEMP_HVAC_MODE}_{self._temp_hvac_mode}"

    @property
    def unique_id(self):
        return self.number_unique_id(self._temp_hvac_mode)

    @property
    def device_info(self):
        return self.tuya_device_info()

    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    @property
    def device_class(self):
        return NumberDeviceClass.TEMPERATURE

    @property
    def mode(self):
        return NumberMode.SLIDER

    @property
    def native_min_value(self):
        return self._min_temp

    @property
    def native_max_value(self):
        return self._max_temp

    @property
    def native_step(self):
        return self._temp_step

    @property
    def native_unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    async def async_added_to_hass(self):
        last_number = await self.async_get_last_number_data()
        self._attr_native_value = last_number.native_value if valid_number_data(last_number) else (self._min_temp + self._max_temp) / 2

    async def async_set_native_value(self, value):
        self._attr_native_value = value