"""Tuya Smart IR AC"""

import voluptuous as vol
import logging
import homeassistant.helpers.config_validation as cv
from tuya_connector import TuyaOpenAPI
from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_TUYA_COUNTRY,
    DEFAULT_TUYA_COUNTRY,
    DOMAIN,
    TUYA_API_CLIENT,
    TUYA_ENDPOINTS
)
from .api import TuyaAPI

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_ACCESS_ID): cv.string,
        vol.Required(CONF_ACCESS_SECRET): cv.string,
        vol.Optional(CONF_TUYA_COUNTRY, default=DEFAULT_TUYA_COUNTRY): vol.In(TUYA_ENDPOINTS.keys())
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    if DOMAIN not in config:
        _LOGGER.error(f"Cannot find {DOMAIN} platform on configuration.yaml")
        return False

    cfg = config.get(DOMAIN)
    tuya_country = cfg.get(CONF_TUYA_COUNTRY)
    
    api_endpoint = TUYA_ENDPOINTS.get(tuya_country)
    access_id = cfg.get(CONF_ACCESS_ID)
    access_secret = cfg.get(CONF_ACCESS_SECRET)

    client = TuyaOpenAPI(api_endpoint, access_id, access_secret)
    res = await hass.async_add_executor_job(client.connect)
    if not res.get("success"):
        _LOGGER.error("Tuya open API login error")
        return False

    hass.data[TUYA_API_CLIENT] = client
    return True