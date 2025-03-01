from homeassistant.exceptions import ServiceValidationError
from .const import DOMAIN
from .api import TuyaGenericAPI


class TuyaService():
    def __init__(self, hass):
        self._api = TuyaGenericAPI(hass)

    async def async_send_command(self, infrared_id, device_id, category_id, key_id, key):
        try:
            await self._api.async_send_command(infrared_id, device_id, category_id, key_id, key)
        except Exception:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="device_error_send_command")