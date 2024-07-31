import logging
from .const import DOMAIN, TUYA_API_CLIENT

_LOGGER = logging.getLogger(__package__)


class TuyaAPI:
    def __init__(self, hass, infrared_id, climate_id):
        self._hass = hass
        self._client = hass.data.get(DOMAIN).get(TUYA_API_CLIENT)
        self._infrared_id = infrared_id
        self._climate_id = climate_id

    async def async_fetch_status(self):
        url = f"/v2.0/infrareds/{self._infrared_id}/remotes/{self._climate_id}/ac/status"
        try:
            result = await self._hass.async_add_executor_job(self._client.get, url)
            _LOGGER.debug(f"Climate {self._climate_id} fetch status response: {str(result)}")
            if result.get("success"):
                return result.get("result")
            raise Exception(TuyaError("", result).to_dict())
        except Exception as e:
            _LOGGER.error(f"Error fetching status for climate {self._climate_id}: {e}")
            return None

    async def async_send_command(self, code, value):
        url = f"/v2.0/infrareds/{self._infrared_id}/air-conditioners/{self._climate_id}/command"
        command = { "code": code, "value": value }
        try:
            _LOGGER.debug(f"Climate {self._climate_id} send command request: {str(command)}")
            result = await self._hass.async_add_executor_job(self._client.post, url, command)
            _LOGGER.debug(f"Climate {self._climate_id} send command response: {str(result)}")
            if not result.get("success"):
                raise Exception(TuyaError(command, result).to_dict())
        except Exception as e:
            _LOGGER.error(f"Error sending command to climate {self._climate_id}: {e}")
            raise Exception(e)

    async def async_send_multiple_command(self, power, mode, temp, wind):
        url = f"/v2.0/infrareds/{self._infrared_id}/air-conditioners/{self._climate_id}/scenes/command"
        command = { "power": power, "mode": mode, "temp": temp, "wind": wind }
        try:
            _LOGGER.debug(f"Climate {self._climate_id} send multiple command request: {str(command)}")
            result = await self._hass.async_add_executor_job(self._client.post, url, command)
            _LOGGER.debug(f"Climate {self._climate_id} send multiple command response: {str(result)}")
            if not result.get("success"):
                raise Exception(TuyaError(command, result).to_dict())
            return result
        except Exception as e:
            _LOGGER.error(f"Error sending multiple command to climate {self._climate_id}: {e}")
            raise Exception(e)


class TuyaError(object):
    def __init__(self, request, response):
        self.request = request
        self.response = response
        
    def to_dict(self):
        return vars(self)