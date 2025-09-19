from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_NAME
from .const import (
    DOMAIN,
    SERVICE,
    MANUFACTURER,
    DEVICE_TYPE_GENERIC,
    CONF_DEVICE_TYPE,
    CONF_INFRARED_ID,
    CONF_DEVICE_ID
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    device_type = config_entry.data.get(CONF_DEVICE_TYPE, None)
    if device_type == DEVICE_TYPE_GENERIC:
        service = hass.data.get(DOMAIN).get(SERVICE)
        infrared_id = config_entry.data.get(CONF_INFRARED_ID)
        device_id = config_entry.data.get(CONF_DEVICE_ID)
        device_data = await service.async_fetch_data(infrared_id, device_id)
        async_add_entities(
            TuyaButton(hass, config_entry.data, service, device_data.category_id, key_data) for key_data in device_data.key_list
        )


class TuyaButton(ButtonEntity):
    def __init__(self, hass, config, service, category_id, key_data):
        self._service = service
        self._infrared_id = config.get(CONF_INFRARED_ID)
        self._device_id = config.get(CONF_DEVICE_ID)
        self._name = config.get(CONF_NAME)
        self._category_id = category_id
        self._key = key_data.key
        self._key_id = key_data.key_id
        self._key_name = key_data.key_name

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