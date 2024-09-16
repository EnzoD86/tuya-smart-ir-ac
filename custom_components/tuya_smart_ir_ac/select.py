from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.select import SelectEntity
from homeassistant.const import (
    EntityCategory,
    STATE_UNKNOWN, 
    STATE_UNAVAILABLE
)
from .const import (
    CONF_FAN_HVAC_MODE,
    DEFAULT_FAN_HVAC_MODE
)
from .helpers import valid_sensor_state
from .entity import TuyaEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    fan_hvac_mode = config_entry.data.get(CONF_FAN_HVAC_MODE, DEFAULT_FAN_HVAC_MODE)
    if fan_hvac_mode:
        async_add_entities([TuyaSelect(config_entry.data)])


class TuyaSelect(SelectEntity, RestoreEntity, TuyaEntity):
    def __init__(self, config):
        TuyaEntity.__init__(self, config)

    @property
    def has_entity_name(self):
        return True

    @property
    def translation_key(self):
        return f"{CONF_FAN_HVAC_MODE}"

    @property
    def unique_id(self):
        return self.select_unique_id()

    @property
    def device_info(self):
        return self.tuya_device_info()

    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    @property
    def icon(self):
        return "mdi:fan"

    @property
    def options(self):
        return self._fan_modes

    async def async_added_to_hass(self):
        last_state = await self.async_get_last_state()
        self._attr_current_option = last_state.state if valid_sensor_state(last_state) else self._fan_modes[0]

    async def async_select_option(self, option):
        self._attr_current_option = option