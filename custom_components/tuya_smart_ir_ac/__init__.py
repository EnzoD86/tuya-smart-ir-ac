"""Tuya Smart IR AC"""

import voluptuous as vol
import logging
import homeassistant.helpers.config_validation as cv
from homeassistant.const import Platform
from .tuya_connector import TuyaOpenAPI
from .const import (
    DOMAIN,
    PLATFORMS,
    CLIENT,
    COORDINATOR,
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_TUYA_COUNTRY,
    TUYA_ENDPOINTS
)
from .api import TuyaAPI
from .coordinator import TuyaCoordinator

_LOGGER = logging.getLogger(__package__)


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_ACCESS_ID): cv.string,
        vol.Required(CONF_ACCESS_SECRET): cv.string,
        vol.Required(CONF_TUYA_COUNTRY): vol.In(TUYA_ENDPOINTS.keys())
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    if DOMAIN not in config:
        _LOGGER.error(f"Cannot find {DOMAIN} platform on configuration.yaml")
        return False

    domain_config  = config.get(DOMAIN, {})
    tuya_country = domain_config.get(CONF_TUYA_COUNTRY)

    api_endpoint = TUYA_ENDPOINTS.get(tuya_country)
    access_id = domain_config.get(CONF_ACCESS_ID)
    access_secret = domain_config.get(CONF_ACCESS_SECRET)

    client = TuyaOpenAPI(api_endpoint, access_id, access_secret)
    res = await hass.async_add_executor_job(client.connect)
    if not res.get("success"):
        _LOGGER.error("Tuya Open API login error")
        return False

    api = TuyaAPI(hass, client)
    coordinator = TuyaCoordinator(hass, api)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][CLIENT] = client
    hass.data[DOMAIN][COORDINATOR] = coordinator
    return True

async def async_setup_entry(hass, config_entry):
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(async_update_entry))
    return True

async def async_unload_entry(hass, config_entry):
    await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    return True

async def async_update_entry(hass, config_entry):
    await hass.config_entries.async_reload(config_entry.entry_id)