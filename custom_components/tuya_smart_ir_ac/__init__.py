import voluptuous as vol
import logging
import homeassistant.helpers.config_validation as cv
from .tuya_connector import TuyaOpenAPI
from .const import (
    DOMAIN,
    PLATFORMS,
    CLIENT,
    CLIMATE_COORDINATOR,
    SENSOR_COORDINATOR,
    SERVICE,
    DEVICE_TYPE_CLIMATE,
    DEVICE_TYPE_SENSOR,
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_TUYA_COUNTRY,
    CONF_UPDATE_INTERVAL,
    CONF_DEVICE_TYPE,
    UPDATE_INTERVAL,
    TUYA_ENDPOINTS
)
from .coordinator import TuyaClimateCoordinator, TuyaSensorCoordinator
from .service import TuyaService

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
        _LOGGER.error(f"Tuya Open API login error: {str(res.get("msg"))}")
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][CLIENT] = client
    hass.data[DOMAIN][CLIMATE_COORDINATOR] = TuyaClimateCoordinator(hass, update_interval)
    hass.data[DOMAIN][SENSOR_COORDINATOR] = TuyaSensorCoordinator(hass)
    hass.data[DOMAIN][SERVICE] = TuyaService(hass)
    return True

async def async_setup_entry(hass, config_entry):
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(async_update_entry))
    device_type = config_entry.data.get(CONF_DEVICE_TYPE, None)
    if device_type == DEVICE_TYPE_CLIMATE:
        climate_coordinator = hass.data.get(DOMAIN).get(CLIMATE_COORDINATOR)
        climate_coordinator.init_interval()
    if device_type == DEVICE_TYPE_SENSOR:
        sensor_coordinator = hass.data.get(DOMAIN).get(SENSOR_COORDINATOR)
        sensor_coordinator.init_interval()
    return True

async def async_unload_entry(hass, config_entry):
    await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    return True

async def async_update_entry(hass, config_entry):
    await hass.config_entries.async_reload(config_entry.entry_id)