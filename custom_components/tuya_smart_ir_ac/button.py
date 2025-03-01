from homeassistant.components.button import ButtonEntity
from homeassistant.const import (
    CONF_NAME
)
from .const import (
    DOMAIN,
    SERVICE,
    MANUFACTURER,
    DEVICE_TYPE_GENERIC,
    CONF_DEVICE_TYPE,
    CONF_INFRARED_ID,
    CONF_DEVICE_ID,
    CONF_RC_DATA,
    CONF_KEY_LIST,
    CONF_KEY,
    CONF_KEY_ID,
    CONF_KEY_NAME,
    CONF_CATEGORY_ID
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    device_type = config_entry.data.get(CONF_DEVICE_TYPE, None)
    if device_type == DEVICE_TYPE_GENERIC: 
        entity_data = config_entry.data.get(CONF_RC_DATA, {})
        async_add_entities(
            TuyaButton(hass, config_entry.data, idx) for idx, key_data in enumerate(entity_data.get(CONF_KEY_LIST, []))
        )


class TuyaButton(ButtonEntity):
    def __init__(self, hass, config, idx):
        self._service = hass.data.get(DOMAIN).get(SERVICE)
        self._infrared_id = config.get(CONF_INFRARED_ID)
        self._device_id = config.get(CONF_DEVICE_ID)
        self._name = config.get(CONF_NAME)

        rc_data = config.get(CONF_RC_DATA, {})
        self._category_id = rc_data.get(CONF_CATEGORY_ID)

        key_data = rc_data.get(CONF_KEY_LIST, [])[idx]
        self._key = key_data.get(CONF_KEY)
        self._key_id = key_data.get(CONF_KEY_ID)
        self._key_name = key_data.get(CONF_KEY_NAME)

    @property
    def name(self):
        return f"{self._name} {self._key_name}"

    @property
    def unique_id(self):
        return f"{self._infrared_id}_{self._device_id}_{self._key_id}"

    @property
    def device_info(self):
        return {
            "name": self._name,
            "identifiers": {(DOMAIN, self._name)},
            "manufacturer": MANUFACTURER
        }

    async def async_press(self):
        await self._service.async_send_command(self._infrared_id, self._device_id, self._category_id, self._key_id , self._key)