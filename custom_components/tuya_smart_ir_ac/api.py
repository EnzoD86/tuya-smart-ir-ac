import logging

_LOGGER = logging.getLogger(__package__)


class TuyaAPI:
    def __init__(self, hass, client):
        self._hass = hass
        self._client = client

    async def async_fetch_all_data(self, climate_ids):
        try:
            url = f"/v1.0/cloud/rc/infrared/ac/status/batch?device_ids={",".join(climate_ids)}"
            _LOGGER.debug(f"API fetch_all_data url: {url}")
            result = await self._hass.async_add_executor_job(self._client.get, url)
            _LOGGER.debug(f"API fetch_all_data response: {str(result)}")
            if result.get("success"):
                return result.get("result")
            raise Exception(TuyaDetails(url, "", result).to_dict())
        except Exception as e:
            _LOGGER.error(f"Error fetching all data for climates {str(climate_ids)}: {e}")
            raise Exception(e)

    async def async_fetch_data(self, infrared_id, climate_id):
        try:
            url = f"/v2.0/infrareds/{infrared_id}/remotes/{climate_id}/ac/status"
            _LOGGER.debug(f"API fetch_data url: {url}")
            result = await self._hass.async_add_executor_job(self._client.get, url)
            _LOGGER.debug(f"API fetch_data response: {str(result)}")
            if result.get("success"):
                return result.get("result")
            raise Exception(TuyaDetails(url, "", result).to_dict())
        except Exception as e:
            _LOGGER.error(f"Error fetching data for climate {climate_id}: {e}")
            raise Exception(e)

    async def async_send_command(self, infrared_id, climate_id, code, value):
        try:
            url = f"/v2.0/infrareds/{infrared_id}/air-conditioners/{climate_id}/command"
            _LOGGER.debug(f"API send_command url: {url}")
            command = { "code": code, "value": value }
            _LOGGER.debug(f"API send_command request: {command}")
            result = await self._hass.async_add_executor_job(self._client.post, url, command)
            _LOGGER.debug(f"API send_command response: {str(result)}")
            if not result.get("success"):
                raise Exception(TuyaDetails(url, command, result).to_dict())
        except Exception as e:
            _LOGGER.error(f"Error sending command to climate {climate_id}: {e}")
            raise Exception(e)

    async def async_send_multiple_command(self, infrared_id, climate_id, power, mode, temp, wind):
        try:
            url = f"/v2.0/infrareds/{infrared_id}/air-conditioners/{climate_id}/scenes/command"
            _LOGGER.debug(f"API send_multiple_command url: {url}")
            command = { "power": power, "mode": mode, "temp": temp, "wind": wind }
            _LOGGER.debug(f"API send_multiple_command request: {command}")
            result = await self._hass.async_add_executor_job(self._client.post, url, command)
            _LOGGER.debug(f"API send_multiple_command response: {str(result)}")
            if not result.get("success"):
                raise Exception(TuyaDetails(url, command, result).to_dict())
        except Exception as e:
            _LOGGER.error(f"Error sending multiple command to climate {climate_id}: {e}")
            raise Exception(e)


class TuyaDetails(object):
    def __init__(self, url, request, response):
        self.url = url
        self.request = request
        self.response = response
        
    def to_dict(self):
        return vars(self)
