from homeassistant.exceptions import ServiceValidationError
from .const import DOMAIN
from .api import TuyaGenericAPI


class TuyaService():
    def __init__(self, hass):
        self._api = TuyaGenericAPI(hass)

    async def async_fetch_data(self, infrared_id, device_id):
        data = await self._api.async_fetch_data(infrared_id, device_id)
        return TuyaData().parse_data(data)

    async def async_send_command(self, infrared_id, device_id, category_id, key_id, key):
        try:
            await self._api.async_send_command(infrared_id, device_id, category_id, key_id, key)
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="device_error_send_command")


class TuyaData(object):
    def parse_data(self, data):
        self.category_id = data.get("category_id")
        self.key_list = self.parse_keys(data.get("key_list"))
        return self
         
    def parse_keys(self, key_list):
        keys_data = []
        for key_data in key_list:
            keys_data.append(TuyaKeyData().parse_data(key_data))
        return keys_data


class TuyaKeyData(object):
    def parse_data(self, data):
        self.key = data.get("key")
        self.key_id = data.get("key_id")
        self.key_name = data.get("key_name")
        return self