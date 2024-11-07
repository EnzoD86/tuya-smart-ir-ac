import voluptuous as vol
import logging
import homeassistant.helpers.config_validation as cv
from tuya_connector import TuyaOpenAPI
from .const import (
    DOMAIN,
    PLATFORMS,
    CLIENT,
    COORDINATOR,
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_TUYA_COUNTRY,
    CONF_UPDATE_INTERVAL,
    CONF_COMPATIBILITY_OPTIONS,
    CONF_HVAC_POWER_ON,
    CONF_DRY_MIN_TEMP,
    CONF_DRY_MIN_FAN,
    UPDATE_INTERVAL,
    TUYA_ENDPOINTS,
    HVAC_POWER_ON_NEVER,
    HVAC_POWER_ON_ALWAYS
)
from .api import TuyaAPI
from .coordinator import TuyaCoordinator

_LOGGER = logging.getLogger(__package__)


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_ACCESS_ID): cv.string,
        vol.Required(CONF_ACCESS_SECRET): cv.string,
        vol.Required(CONF_TUYA_COUNTRY): vol.In(TUYA_ENDPOINTS.keys()),
        vol.Optional(CONF_UPDATE_INTERVAL, default=UPDATE_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600))
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
    update_interval = domain_config.get(CONF_UPDATE_INTERVAL)
    
    client = TuyaOpenAPI(api_endpoint, access_id, access_secret)
    res = await hass.async_add_executor_job(client.connect)
    if not res.get("success"):
        _LOGGER.error("Tuya Open API login error")
        return False

    api = TuyaAPI(hass, client)
    coordinator = TuyaCoordinator(hass, api, update_interval)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][CLIENT] = client
    hass.data[DOMAIN][COORDINATOR] = coordinator
    return True

async def async_setup_entry(hass, config_entry):
    await update_entry_configuration(hass, config_entry)
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(async_update_entry))
    return True

async def async_unload_entry(hass, config_entry):
    await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    return True

async def async_update_entry(hass, config_entry):
    await hass.config_entries.async_reload(config_entry.entry_id)

async def update_entry_configuration(hass, config_entry):
    data = {**config_entry.data}

    if (data.get(CONF_HVAC_POWER_ON, None) is not None or
        data.get(CONF_DRY_MIN_TEMP, None) is not None or
        data.get(CONF_DRY_MIN_FAN, None) is not None):
        _LOGGER.debug("Update configuration")

        if data.get(CONF_COMPATIBILITY_OPTIONS, None) is None:
            data[CONF_COMPATIBILITY_OPTIONS] = {}

        if data.get(CONF_HVAC_POWER_ON, None) is not None:
            data[CONF_COMPATIBILITY_OPTIONS][CONF_HVAC_POWER_ON] = data[CONF_HVAC_POWER_ON]
            del data[CONF_HVAC_POWER_ON]

        if data.get(CONF_DRY_MIN_TEMP, None) is not None:
            data[CONF_COMPATIBILITY_OPTIONS][CONF_DRY_MIN_TEMP] = data[CONF_DRY_MIN_TEMP]
            del data[CONF_DRY_MIN_TEMP]

        if data.get(CONF_DRY_MIN_FAN, None) is not None:
            data[CONF_COMPATIBILITY_OPTIONS][CONF_DRY_MIN_FAN] = data[CONF_DRY_MIN_FAN]
            del data[CONF_DRY_MIN_FAN]

        hass.config_entries.async_update_entry(config_entry, data=data, minor_version=1, version=1)
        hass.config_entries._async_schedule_save()
        _LOGGER.debug("Update configuration successful")
        
    if data.get(CONF_COMPATIBILITY_OPTIONS, {}).get(CONF_HVAC_POWER_ON, None) is not None:
        if data[CONF_COMPATIBILITY_OPTIONS][CONF_HVAC_POWER_ON] is False:
            data[CONF_COMPATIBILITY_OPTIONS][CONF_HVAC_POWER_ON] = HVAC_POWER_ON_NEVER
            hass.config_entries.async_update_entry(config_entry, data=data, minor_version=1, version=1)
            hass.config_entries._async_schedule_save()
            _LOGGER.debug("Update configuration successful")
        
        if data[CONF_COMPATIBILITY_OPTIONS][CONF_HVAC_POWER_ON] is True:
            data[CONF_COMPATIBILITY_OPTIONS][CONF_HVAC_POWER_ON] = HVAC_POWER_ON_ALWAYS
            hass.config_entries.async_update_entry(config_entry, data=data, minor_version=1, version=1)
            hass.config_entries._async_schedule_save()
            _LOGGER.debug("Update configuration successful")

    return True