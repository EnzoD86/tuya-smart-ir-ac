import logging
from requests import session
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed

from .tuya_connector import (
    TuyaOpenAPI,
    TuyaOpenPulsar,
    TuyaCloudPulsarTopic
)
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_TUYA_COUNTRY,
    CONF_CLIMATE_UPDATE_INTERVAL,
    CONF_SENSOR_UPDATE_INTERVAL,
    UPDATE_INTERVAL,
    TUYA_API_ENDPOINTS,
    TUYA_PULSAR_ENDPOINTS,
    DEVICE_TYPE_CLIMATES,
    DEVICE_TYPE_SENSORS,
    DEVICE_TYPE_GENERICS
)
from .coordinator import TuyaClimateCoordinator, TuyaSensorCoordinator
from .manager import TuyaIRManager
from .models import HubConfigEntry, RuntimeData
from .api import TuyaClimateAPI, TuyaSensorAPI
from .bridge import TuyaPulsarBridge

_LOGGER = logging.getLogger(__package__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required("access_id"): cv.string,
        vol.Required("access_secret"): cv.string,
        vol.Required("country"): vol.All(vol.Coerce(str), str.lower, vol.In(TUYA_API_ENDPOINTS.keys())),
        vol.Optional("update_interval", default=UPDATE_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600))
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Tuya Smart IR Hub component from YAML configuration."""
    if DOMAIN not in config:
        return True

    if hass.config_entries.async_entries(DOMAIN):
        _LOGGER.warning(
            "Legacy YAML configuration detected under '%s:', but the integration is already configured via UI. "
            "Please remove the YAML lines from your configuration.yaml to prevent this warning.",
            DOMAIN
        )
        return True

    domain_config = config[DOMAIN]
    _LOGGER.info("First-time YAML configuration detected, initiating import into UI")

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data=domain_config,
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: HubConfigEntry) -> bool:
    """Set up Tuya Smart IR Hub from a config entry."""
    _LOGGER.debug("[%s] Starting Hub initialization", entry.title)
    data = entry.data
    
    if CONF_ACCESS_ID not in data:
        _LOGGER.debug("Legacy standalone entry '%s' detected. Skipping.", entry.title)
        return False

    if not all(key in entry.options for key in [DEVICE_TYPE_CLIMATES, DEVICE_TYPE_GENERICS, DEVICE_TYPE_SENSORS]):
        await _async_migrate_old_entries(hass, entry)

    country = data.get(CONF_TUYA_COUNTRY, "")
    climate_interval = data.get(CONF_CLIMATE_UPDATE_INTERVAL, UPDATE_INTERVAL)
    sensor_interval = data.get(CONF_SENSOR_UPDATE_INTERVAL, UPDATE_INTERVAL)
    
    session = async_get_clientsession(hass)

    # Initialize API client
    api_client = TuyaOpenAPI(
        endpoint=TUYA_API_ENDPOINTS.get(country, ""), 
        access_id=data[CONF_ACCESS_ID], 
        access_secret=data[CONF_ACCESS_SECRET],
        session=session  # <--- Assicurati che sia passato come argomento nominativo
    )

    res = await api_client.connect()
    if not res.get("success"):
        _LOGGER.error("Tuya Hub Login Error: %s", res.get("msg"))
        await api_client.close()
        raise ConfigEntryAuthFailed(f"Tuya authentication failed: {res.get('msg')}")    
    
    pulsar_client = TuyaOpenPulsar(
        ws_endpoint=TUYA_PULSAR_ENDPOINTS.get(country, ""),
        access_id=data[CONF_ACCESS_ID],
        access_secret=data[CONF_ACCESS_SECRET],
        topic=TuyaCloudPulsarTopic.PROD,
        session=session
    )

    try:
        # Initialize API
        climate_api = TuyaClimateAPI(hass, client=api_client, log_prefix=f"[{entry.title}]")
        sensor_api = TuyaSensorAPI(hass, client=api_client, log_prefix=f"[{entry.title}]")

        # Initialize Pulsar bridge
        pulsar_bridge = TuyaPulsarBridge(hass, pulsar_client)

        # Initialize coordinators
        climate_coordinator = TuyaClimateCoordinator(hass, entry, climate_api, pulsar_bridge, climate_interval)
        sensor_coordinator = TuyaSensorCoordinator(hass, entry, sensor_api, pulsar_bridge, sensor_interval)

        # Perform initial data fetch to populate coordinators before platform setup
        await climate_coordinator.async_config_entry_first_refresh()
        await sensor_coordinator.async_config_entry_first_refresh()

        # Start Pulsar bridge after coordinators are ready to handle incoming messages
        await pulsar_client.start()

        entry.runtime_data = RuntimeData(
            api_client=api_client,
            pulsar_client=pulsar_client,
            climate_coordinator=climate_coordinator,
            sensor_coordinator=sensor_coordinator,
            ir_manager=TuyaIRManager(hass, entry, api_client)
        )

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception as ex:
        _LOGGER.error("[%s] Error during Hub initialization, cleaning up sessions: %s", entry.title, ex)
        await api_client.close()
        await pulsar_client.stop()

    _LOGGER.debug("[%s] Hub initialization completed", entry.title)
    entry.async_on_unload(entry.add_update_listener(async_update_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HubConfigEntry) -> bool:
    """Unload a config entry and clean up active cloud sessions."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        if entry.runtime_data:
            if entry.runtime_data.api_client:
                await entry.runtime_data.api_client.close()
            
            if entry.runtime_data.pulsar_client:
                await entry.runtime_data.pulsar_client.stop() 

        if entry.disabled_by is None:
            device_registry = dr.async_get(hass)
            devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
            for device_entry in devices:
                device_registry.async_remove_device(device_entry.id)

    return unload_ok


async def async_update_entry(hass: HomeAssistant, entry: HubConfigEntry) -> None:
    """Handle options update by reloading the entry integration flow."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_migrate_old_entries(hass: HomeAssistant, hub_entry: HubConfigEntry) -> None:
    """Migrate legacy independent device config entries into centralized Hub options dictionary."""
    _LOGGER.info("Checking for legacy devices to migrate under the centralized Hub architecture...")

    current_climates = list(hub_entry.options.get("climates", []))
    current_generics = list(hub_entry.options.get("generics", []))
    current_sensors = list(hub_entry.options.get("sensors", []))
    
    migrated_something = False
    entries_to_remove = []

    for old_entry in hass.config_entries.async_entries(DOMAIN):
        if CONF_ACCESS_ID in old_entry.data or old_entry.entry_id == hub_entry.entry_id:
            continue
            
        if "device_type" not in old_entry.data:
            continue

        old_type = old_entry.data.get("device_type")
        _LOGGER.info("Found legacy entity entry '%s' [%s]. Migrating preferences...", old_entry.title, old_type)

        device_payload = {
            "entry_id": old_entry.entry_id,
            "name": old_entry.title,
            "device_id": old_entry.data.get("device_id"),
        }

        if old_type == "climate":
            device_payload.update({
                "infrared_id": old_entry.data.get("infrared_id"),
                "temperature_sensor": old_entry.data.get("temperature_sensor"),
                "humidity_sensor": old_entry.data.get("humidity_sensor"),
                "min_temp": old_entry.data.get("min_temp"),
                "max_temp": old_entry.data.get("max_temp"),
                "temp_step": old_entry.data.get("temp_step"),
                "hvac_modes": old_entry.data.get("hvac_modes"),
                "fan_modes": old_entry.data.get("fan_modes"),
                "temp_hvac_mode": old_entry.data.get("temp_hvac_mode"),
                "fan_hvac_mode": old_entry.data.get("fan_hvac_mode"),
                "optional_entities": old_entry.data.get("extra_sensors"),
                "compatibility_options": old_entry.data.get("compatibility_options", {}),
            })
            
            hvac_presets = []
            if old_entry.data.get("temp_hvac_mode", False):
                hvac_presets.append("temp_hvac_mode")
            if old_entry.data.get("fan_hvac_mode", False):
                hvac_presets.append("fan_hvac_mode")
            
            optional_entities = []
            if old_entry.data.get("extra_sensors", False):
                optional_entities.extend(["current_temperature", "current_humidity"])
                
            device_payload.update({
                "hvac_presets": hvac_presets,
                "optional_entities": optional_entities
            })
            
            if not any(d["device_id"] == device_payload["device_id"] for d in current_climates):
                current_climates.append(device_payload)
                migrated_something = True

        elif old_type == "generic":
            device_payload.update({
                "infrared_id": old_entry.data.get("infrared_id"),
            })
            if not any(d["device_id"] == device_payload["device_id"] for d in current_generics):
                current_generics.append(device_payload)
                migrated_something = True

        elif old_type == "sensor":
            device_payload.update({
                "temp_unit": old_entry.data.get("temp_unit"),
                "sensor_types": old_entry.data.get("sensor_types", []),
            })
            if not any(d["device_id"] == device_payload["device_id"] for d in current_sensors):
                current_sensors.append(device_payload)
                migrated_something = True

        entries_to_remove.append(old_entry)

    _LOGGER.info("Committing updated and structured device arrays into Hub options dictionary.")
    hass.config_entries.async_update_entry(
        hub_entry, 
        options={
            **hub_entry.options, 
            "climates": current_climates,
            "generics": current_generics,
            "sensors": current_sensors
        }
    )

    for old_entry in entries_to_remove:
        hass.async_create_task(hass.config_entries.async_remove(old_entry.entry_id))
        _LOGGER.info("Legacy individual device entry '%s' permanently purged.", old_entry.title)
        
    if migrated_something:
        hass.async_create_task(
            hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Tuya Smart IR AC: Migration Completed",
                    "message": (
                        "Your legacy devices have been successfully migrated under the new centralized Hub.\n\n"
                        "**Action Required:** Please remove the old `tuya_smart_ir_ac:` YAML configuration from your "
                        "`configuration.yaml` file and restart Home Assistant to complete the cleanup process."
                    ),
                    "notification_id": "tuya_smart_ir_migration_warning",
                },
            )
        )