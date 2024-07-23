from tuya_connector import TuyaOpenAPI
from homeassistant.core import HomeAssistant

import logging

_LOGGER = logging.getLogger(__package__)


class TuyaAPI:
    def __init__(
        self,
        hass: HomeAssistant,
        api_url,
        access_id,
        access_secret,
        climate_id,
        infrared_id
    ):
        self._hass = hass
        self._climate_id = climate_id
        self._infrared_id = infrared_id

        self._openapi = TuyaOpenAPI(api_url, access_id, access_secret)
        self._openapi.connect()

    async def async_get_status(self):
        status = await self.get_status()
        return TuyaData(status) if status else None
            
    async def async_turn_on(self):
        await self.send_command("power", "1")

    async def async_turn_off(self):
        await self.send_command("power", "0")

    async def async_set_fan_speed(self, fan_speed):
        await self.send_command("wind", str(fan_speed))

    async def async_set_temperature(self, temperature):
        await self.send_command("temp", str(temperature))

    async def async_set_hvac_mode(self, hvac_mode):
        await self.send_command("mode", str(hvac_mode))
        
    async def async_set_multiple(self, power, mode, temp, wind):
        await self.send_multiple_command(power, mode, temp, wind)

    async def get_status(self):
        url = f"/v2.0/infrareds/{self._infrared_id}/remotes/{self._climate_id}/ac/status"
        try:
            data = await self._hass.async_add_executor_job(self._openapi.get, url)
            _LOGGER.debug(f"Climate {self._climate_id} get status response: {str(data)}")
            if data.get("success"):
                return data.get("result")
            raise Exception(f"{data.get("code", None)} {data.get("msg", None)}")   
        except Exception as e:
            _LOGGER.error(f"Error getting status for climate {self._climate_id}: {e}")
            return None

    async def send_command(self, code, value):
        url = f"/v2.0/infrareds/{self._infrared_id}/air-conditioners/{self._climate_id}/command"
        command = { "code": code, "value": value }
        try:
            _LOGGER.debug(f"Climate {self._climate_id} send command request: {str(command)}")
            data = await self._hass.async_add_executor_job(self._openapi.post, url, command)
            _LOGGER.debug(f"Climate {self._climate_id} send command response: {str(data)}")
            if not data.get("success"):
                raise Exception(f"{data.get("code", None)} {data.get("msg", None)}")
            return data
        except Exception as e:
            _LOGGER.error(f"Error sending command to climate {self._climate_id}: {e}")
            return False

    async def send_multiple_command(self, power, mode, temp, wind):
        url = f"/v2.0/infrareds/{self._infrared_id}/air-conditioners/{self._climate_id}/scenes/command"
        command = { "power": power, "mode": mode, "temp": temp, "wind": wind }
        try:
            _LOGGER.debug(f"Climate {self._climate_id} send multiple command request: {str(command)}")
            data = await self._hass.async_add_executor_job(self._openapi.post, url, command)
            _LOGGER.debug(f"Climate {self._climate_id} send multiple command response: {str(data)}")
            if not data.get("success"):
                raise Exception(f"{data.get("code", None)} {data.get("msg", None)}")
            return data
        except Exception as e:
            _LOGGER.error(f"Error sending multiple command to climate {self._climate_id}: {e}")
            return False


class TuyaData(object):
    def __init__(self, status):
        self.temperature = status.get("temp")
        self.mode = status.get("mode")
        self.power = status.get("power")
        self.wind = status.get("wind")