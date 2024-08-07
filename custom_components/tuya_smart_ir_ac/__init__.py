"""Tuya Smart IR AC"""

import voluptuous as vol
import logging
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import async_migrate_entries
from homeassistant.core import callback
from homeassistant.const import Platform
from .tuya_connector import TuyaOpenAPI
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_TUYA_COUNTRY,
    TUYA_API_CLIENT,
    TUYA_ENDPOINTS
)


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

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][TUYA_API_CLIENT] = client
    return True

async def async_setup_entry(hass, config_entry):
    #TODO: remove in next release!
    try:
        _LOGGER.debug("Update unique_id")
        
        infrared_id = config_entry.data.get("infrared_id")
        climate_id = config_entry.data.get("climate_id")
        new_unique_id = f"{infrared_id}_{climate_id}"
            
        @callback
        def update_unique_id(entity_entry):
            """Update unique ID of entity entry."""
            return {
                "new_unique_id": new_unique_id
            }
            
        await async_migrate_entries(hass, config_entry.entry_id, update_unique_id)
        hass.config_entries.async_update_entry(config_entry)
    except Exception as e:
        pass
    #################################
    
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(async_update_entry))
    return True

async def async_unload_entry(hass, config_entry):
    await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    return True

async def async_update_entry(hass, config_entry):
    await hass.config_entries.async_reload(config_entry.entry_id)