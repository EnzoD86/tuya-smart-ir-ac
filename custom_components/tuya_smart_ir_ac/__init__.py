import asyncio
import logging
import voluptuous as vol
from datetime import timedelta
import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.components import persistent_notification
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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
    CONF_ENABLE_PULSAR,
    CONF_TUYA_COUNTRY,
    CONF_CLIMATE_UPDATE_INTERVAL,
    CONF_SENSOR_UPDATE_INTERVAL,
    CONF_GLOBAL_PRESETS,
    UPDATE_INTERVAL,
    TUYA_API_ENDPOINTS,
    TUYA_PULSAR_ENDPOINTS,
    DEFAULT_ENABLE_PULSAR,
    DEFAULT_GLOBAL_PRESETS,
    DEVICE_TYPE_CLIMATES,
    DEVICE_TYPE_SENSORS,
    DEVICE_TYPE_GENERICS
)
from .helpers import merge_presets_with_defaults
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

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data=config[DOMAIN],
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
    enable_pulsar = data.get(CONF_ENABLE_PULSAR, DEFAULT_ENABLE_PULSAR)
    
    session = async_get_clientsession(hass)

    # Initialize API client
    api_client = TuyaOpenAPI(
        endpoint=TUYA_API_ENDPOINTS.get(country, ""), 
        access_id=data[CONF_ACCESS_ID], 
        access_secret=data[CONF_ACCESS_SECRET],
        session=session
    )

    res = await api_client.connect()
    if not res.get("success"):
        _LOGGER.error("Tuya Hub Login Error: %s", res.get("msg"))
        await api_client.close()
        raise ConfigEntryAuthFailed(f"Tuya authentication failed: {res.get('msg')}")    
    
    pulsar_client = None
    pulsar_bridge = None
    
    if enable_pulsar:
        # Initialize Pulsar client
        pulsar_client = TuyaOpenPulsar(
            ws_endpoint=TUYA_PULSAR_ENDPOINTS.get(country, ""),
            access_id=data[CONF_ACCESS_ID],
            access_secret=data[CONF_ACCESS_SECRET],
            topic=TuyaCloudPulsarTopic.PROD,
            session=session
        )

        # Initialize Pulsar bridge
        pulsar_bridge = TuyaPulsarBridge(hass, pulsar_client)

    try:
        # Initialize API
        climate_api = TuyaClimateAPI(hass, client=api_client, log_prefix=f"[{entry.title}]")
        sensor_api = TuyaSensorAPI(hass, client=api_client, log_prefix=f"[{entry.title}]")

        # Initialize coordinators
        climate_coordinator = TuyaClimateCoordinator(hass, entry, climate_api, pulsar_bridge, climate_interval)
        sensor_coordinator = TuyaSensorCoordinator(hass, entry, sensor_api, pulsar_bridge, sensor_interval)

        # Perform initial data fetch to populate coordinators before platform setup
        await climate_coordinator.async_config_entry_first_refresh()
        await sensor_coordinator.async_config_entry_first_refresh()

        # Start Pulsar bridge after coordinators are ready to handle incoming messages
        if enable_pulsar:
            await pulsar_client.start()
            hass.async_create_task(async_check_pulsar_connection(hass, entry, pulsar_client))

        # Save Runtime Data
        runtime_presets = merge_presets_with_defaults(
            saved_presets=entry.options.get(CONF_GLOBAL_PRESETS, {}),
            defaults=DEFAULT_GLOBAL_PRESETS
        )

        entry.runtime_data = RuntimeData(
            api_client=api_client,
            pulsar_client=pulsar_client,
            climate_coordinator=climate_coordinator,
            sensor_coordinator=sensor_coordinator,
            ir_manager=TuyaIRManager(hass, entry, api_client),
            global_presets=runtime_presets
        )

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception as ex:
        _LOGGER.error("[%s] Error during Hub initialization, cleaning up sessions: %s", entry.title, ex)

        try:
            if api_client:
                await api_client.close()
        except Exception as api_err:
            _LOGGER.debug("[%s] Failed to close Tuya API client during abort: %s", entry.title, api_err)

        try:
            if pulsar_client:
                await pulsar_client.stop()
        except Exception as pulsar_err:
            _LOGGER.debug("[%s] Failed to stop Tuya Pulsar client during abort: %s", entry.title, pulsar_err)

        raise

    _LOGGER.debug("[%s] Hub initialization completed", entry.title)
    entry.async_on_unload(entry.add_update_listener(async_update_entry))
    return True


async def async_update_entry(hass: HomeAssistant, entry: HubConfigEntry) -> None:
    """Handles updating options without destroying API sessions."""
    _LOGGER.debug("[%s] Updating entry in progress...", entry.title)
    
    current_data = entry.runtime_data

    new_secret = entry.data.get(CONF_ACCESS_SECRET, "")
    expected_secret_bytes = new_secret.encode("utf-8")

    new_country = entry.data.get(CONF_TUYA_COUNTRY, "")
    expected_endpoint = TUYA_API_ENDPOINTS.get(new_country, "")

    expected_climate_interval = timedelta(seconds=entry.data.get(CONF_CLIMATE_UPDATE_INTERVAL, UPDATE_INTERVAL))
    expected_sensor_interval = timedelta(seconds=entry.data.get(CONF_SENSOR_UPDATE_INTERVAL, UPDATE_INTERVAL))

    expected_enable_pulsar = entry.data.get(CONF_ENABLE_PULSAR, DEFAULT_ENABLE_PULSAR)

    hub_changed = (
        expected_secret_bytes != current_data.api_client.access_secret_bytes or
        expected_endpoint != current_data.api_client.endpoint or
        expected_climate_interval != current_data.climate_coordinator.update_interval or
        expected_sensor_interval != current_data.sensor_coordinator.update_interval or
        expected_enable_pulsar != (current_data.pulsar_client is not None)
    )
    
    if hub_changed:
        _LOGGER.debug("[%s] Tuya Hub modification detected. Force a full reboot.", entry.title)
        await hass.config_entries.async_reload(entry.entry_id)
        return

    if entry.disabled_by is None:
        device_registry = dr.async_get(hass)
        devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
        for device_entry in devices:
            device_registry.async_remove_device(device_entry.id)

    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    runtime_presets = merge_presets_with_defaults(
        saved_presets=entry.options.get(CONF_GLOBAL_PRESETS, {}),
        defaults=DEFAULT_GLOBAL_PRESETS
    )

    entry.runtime_data = RuntimeData(
        api_client=current_data.api_client,       
        pulsar_client=current_data.pulsar_client, 
        climate_coordinator=current_data.climate_coordinator,
        sensor_coordinator=current_data.sensor_coordinator,
        ir_manager=current_data.ir_manager,
        global_presets=runtime_presets
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

async def async_unload_entry(hass: HomeAssistant, entry: HubConfigEntry) -> bool:
    """Unload a config entry and clean up active cloud sessions."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and entry.runtime_data:
        if entry.runtime_data.api_client:
            _LOGGER.debug("[%s] Closing Tuya API client session during unload.", entry.title)
            await entry.runtime_data.api_client.close()

        if entry.runtime_data.pulsar_client:
            _LOGGER.debug("[%s] Stopping Tuya Pulsar client session during unload.", entry.title)
            await entry.runtime_data.pulsar_client.stop() 

    return unload_ok

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
        persistent_notification.async_create(
            hass,
            title="Tuya Smart IR AC: Migration Completed",
            message=(
                "Your legacy devices have been successfully migrated under the new centralized Hub.\n\n"
                "**Action Required:** Please remove the old `tuya_smart_ir_ac:` YAML configuration from your "
                "`configuration.yaml` file and restart Home Assistant to complete the cleanup process."
            ),
            notification_id="tuya_smart_ir_migration_warning",
        )

async def async_check_pulsar_connection(hass: HomeAssistant, entry: HubConfigEntry, pulsar_client: TuyaOpenPulsar):
    for _ in range(5):
        if pulsar_client.is_connected():
            return True
        await asyncio.sleep(3)

    if not pulsar_client.is_connected():
        persistent_notification.async_create(
            hass,
            title=f"Tuya Smart IR AC [{entry.title}]: Tuya Pulsar Stream Inactive",
            message=(
                f"The **{entry.title}** integration established a network connection, but Home Assistant is receiving no data from the Tuya Pulsar stream.\n\n"
                "This is usually caused by an incomplete configuration on your **Tuya Developer Platform**. "
                "Please verify the following settings:\n\n"
                "### 1. Enable the Message Service\n"
                "* Go to **Cloud** -> **Development** -> Open your project -> **Message Service** tab.\n"
                "* Ensure that the main Message Service toggle switch at the top is turned **ON (Enabled)**.\n\n"
                "### 2. Configure the PRODUCTION Environment\n"
                "* Make sure you select the **Production Environment** tab. *Home Assistant completely ignores the Test Environment*.\n"
                "* Under the **Messaging Rules / Subscriptions** section, ensure you have explicitly enabled the following message types (**BizCode**):\n"
                "  * `devicePropertyMessage` (Device Property Message)\n"
                "  * `statusReport` (Status Report)\n"
                "  * `deviceEventMessage` (Device Event Message)\n"
                "  * `deviceActionResponseMessage` (Device Action Response Message)\n\n"
                "**Note:** If these are already checked but the stream is still silent, try unchecking them, saving, and re-checking them to force Tuya to rebuild the routing rules.\n\n"
                "The integration will automatically start processing data as soon as the cloud stream becomes active."
            ),
            notification_id=f"tuya_pulsar_connection_status_{entry.title.lower().replace(' ', '_')}"
        )

    return True