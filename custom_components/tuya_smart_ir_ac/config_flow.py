import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import TuyaClimateAPI, TuyaGenericAPI, TuyaSensorAPI
from .tuya_connector import TuyaOpenAPI
from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_CLIMATE_UPDATE_INTERVAL,
    CONF_COMPATIBILITY_OPTIONS,
    CONF_DEVICE_ID,
    CONF_DRY_MIN_FAN,
    CONF_DRY_MIN_TEMP,
    CONF_ENABLE_PULSAR,
    CONF_FAN_MODES,
    CONF_FAN_POWER_ON,
    CONF_HUMIDITY_SENSOR,
    CONF_HVAC_MODES,
    CONF_HVAC_POWER_ON,
    CONF_HVAC_PRESETS,
    CONF_INFRARED_ID,
    CONF_OPTIONAL_ENTITIES,
    CONF_SENSOR_TYPES,
    CONF_SENSOR_UPDATE_INTERVAL,
    CONF_TEMPERATURE_SENSOR,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    CONF_TEMP_POWER_ON,
    CONF_TEMP_STEP,
    CONF_TEMP_UNIT,
    CONF_TUYA_COUNTRY,
    DEFAULT_DRY_MIN_FAN,
    DEFAULT_DRY_MIN_TEMP,
    DEFAULT_ENABLE_PULSAR,
    DEFAULT_FAN_POWER_ON,
    DEFAULT_HVAC_POWER_ON,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_PRECISION,
    DEFAULT_TEMP_POWER_ON,
    DEVICE_TYPE_CLIMATES,
    DEVICE_TYPE_GENERICS,
    DEVICE_TYPE_SENSORS,
    DOMAIN,
    ENTITY_SENSOR_BATTERY,
    ENTITY_SENSOR_HUMIDITY,
    ENTITY_SENSOR_TEMPERATURE,
    SUPPORTED_FAN_MODES,
    SUPPORTED_HVAC_MODES,
    SUPPORTED_HVAC_PRESETS,
    SUPPORTED_OPTIONAL_ENTITIES,
    SUPPORTED_POWER_ON_MODES,
    TUYA_API_ENDPOINTS,
    UPDATE_INTERVAL,
)
from .models import (
    TuyaSensorData,
    TuyaAPIResult
)

_LOGGER = logging.getLogger(__package__)


class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tuya Smart IR Hub."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step when adding the integration via the UI."""
        return await self.async_step_hub_settings(user_input)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> FlowResult:
        """Handle fallback authentication recovery trigger."""
        return await self.async_step_hub_settings()

    async def async_step_hub_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Single step handler for both initial setup and re-authentication."""
        errors: dict[str, str] = {}
        
        entry_id = self.context.get("entry_id")
        entry = self.hass.config_entries.async_get_entry(entry_id) if entry_id else None

        if user_input is not None:
            if entry and user_input.get(CONF_ACCESS_ID) != entry.data.get(CONF_ACCESS_ID):
                errors[CONF_ACCESS_ID] = "cannot_change_access_id"

            if not errors:
                new_data = {**entry.data, **user_input} if entry else user_input
                
                if not entry:
                    access_id = user_input[CONF_ACCESS_ID]
                    await self.async_set_unique_id(f"tuya_hub_{access_id}")
                    self._abort_if_unique_id_configured()
                
                errors = await async_validate_and_connect(new_data)
                if not errors:
                    if entry:
                        return self.async_update_reload_and_abort(entry, data=new_data)
                    
                    return self.async_create_entry(
                        title=f"Tuya Smart IR Hub ({access_id})",
                        data=user_input,
                        options={
                            DEVICE_TYPE_CLIMATES: [],
                            DEVICE_TYPE_GENERICS: [],
                            DEVICE_TYPE_SENSORS: [],
                        },
                    )

        current_data = {**(entry.data if entry else {}), **(user_input or {})}
        schema = self.add_suggested_values_to_schema(
            vol.Schema(hub_data_schema()), current_data
        )

        return self.async_show_form(
            step_id="hub_settings", 
            data_schema=schema, 
            errors=errors
        )
    
    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """Handle migration and import from old YAML configuration schemas."""
        _LOGGER.debug("Old YAML configuration detected: %s", import_config)
        
        access_id = import_config.get(CONF_ACCESS_ID)
        await self.async_set_unique_id(f"tuya_hub_{access_id}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Tuya Smart IR Hub ({access_id})",
            data={
                CONF_ACCESS_ID: access_id,
                CONF_ACCESS_SECRET: import_config.get("access_secret"),
                CONF_TUYA_COUNTRY: import_config.get("country"),
                CONF_CLIMATE_UPDATE_INTERVAL: import_config.get("update_interval") or UPDATE_INTERVAL,
                CONF_SENSOR_UPDATE_INTERVAL: UPDATE_INTERVAL
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow management for runtime sub-devices adjustments."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Initialize the option flow branch and show initial routing menu."""
        self._selected_device_id = None
        self._next_action = None
        return self.async_show_menu(
            step_id="init",
            menu_options=["device_management", "hub_settings"]
        )

    async def async_step_device_management(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Display sub-menu filtering specific device category platforms."""
        return self.async_show_menu(
            step_id="device_management",
            menu_options=["climate_management", "generic_management", "sensor_management", "back_to_init"]
        )
        
    async def async_step_back_to_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Route the user backward to the core root entry menu."""
        return await self.async_step_init()

    async def async_step_climate_management(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Display management sub-menu for dynamic HVAC air conditioners."""
        return self.async_show_menu(
            step_id="climate_management",
            menu_options=["add_climate", "edit_climate", "remove_climate", "back_to_devices"]
        )
        
    async def async_step_generic_management(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Display management sub-menu for IR generic remotes."""
        return self.async_show_menu(
            step_id="generic_management",
            menu_options=["add_generic", "remove_generic", "back_to_devices"]
        )
        
    async def async_step_sensor_management(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Display management sub-menu for TH environmental hardware sensors."""
        return self.async_show_menu(
            step_id="sensor_management",
            menu_options=["add_sensor", "remove_sensor", "back_to_devices"]
        )

    async def async_step_back_to_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Route the user backward to the device category selection menu."""
        return await self.async_step_device_management()

    async def async_step_hub_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Expose core system settings and parameters update options form."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get(CONF_ACCESS_ID) != self.config_entry.data.get(CONF_ACCESS_ID):
                errors[CONF_ACCESS_ID] = "cannot_change_access_id"

            if not errors:
                new_data = {**self.config_entry.data, **user_input}
                
                errors = await async_validate_and_connect(new_data)
                if not errors:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, 
                        data=new_data
                    )
                    return self.async_create_entry(
                        title="",
                        data=self.config_entry.options
                    )

        current_data = {
            **self.config_entry.data, 
            **self.config_entry.options, 
            **(user_input or {})
        }
        schema = self.add_suggested_values_to_schema(
            vol.Schema(hub_data_schema()), current_data
        )

        return self.async_show_form(
            step_id="hub_settings",
            data_schema=schema,
            errors=errors
        )

    async def async_step_add_climate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle option step for attaching a new climate device mapping."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            overwrite_invalid_user_input(user_input)

            infrared_id = user_input.get(CONF_INFRARED_ID)
            climate_id = user_input.get(CONF_DEVICE_ID)
            name = user_input.get(CONF_NAME)

            for entry in self.hass.config_entries.async_entries(DOMAIN):
                for cat in [DEVICE_TYPE_CLIMATES, DEVICE_TYPE_GENERICS, DEVICE_TYPE_SENSORS]:
                    if any(d.get(CONF_DEVICE_ID) == climate_id for d in entry.options.get(cat, [])):
                        if entry.entry_id == self.config_entry.entry_id:
                            errors["base"] = "device_already_configured"
                        else:
                            errors["base"] = "device_already_configured_on_other_hub"
                        _LOGGER.debug("[%s] Aborting climate addition: device ID %s is already registered", name, climate_id)
                        break
                if errors:
                    break

            if not errors:
                client = self.config_entry.runtime_data.api_client
                result = await async_get_climate_device(self.hass, client, infrared_id, climate_id)
                
                if not result.success:
                    errors["base"] = "tuya_api_error"
                    placeholders["error_info"] = result.error_info
                    _LOGGER.debug("[%s] Tuya API rejection validation failed for climate target %s: %s", name, climate_id, result.error_info)
                else:
                    current_options = dict(self.config_entry.options)
                    climates = list(current_options.get(DEVICE_TYPE_CLIMATES, []))
                    climates.append(user_input)
                    return self.async_create_entry(
                        title="", 
                        data={**current_options, DEVICE_TYPE_CLIMATES: climates}
                    )

        return self.async_show_form(
            step_id="add_climate",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({**device1_data(), **climate_data()}), user_input or {}
            ),
            errors=errors,
            description_placeholders=placeholders
        )

    async def async_step_edit_climate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle modification step for a previously initialized climate entry."""
        if not getattr(self, "_selected_device_id", None):
            self._next_action = "async_step_edit_climate"
            return await self.async_step_select_climate()

        climates = self._get_climates_list()
        index = next((i for i, c in enumerate(climates) if self._get_device_id_pair(c) == self._selected_device_id), None)
        
        if index is None:
            _LOGGER.debug("Requested modification failed: Device pairing signature %s not found", self._selected_device_id)
            return self.async_abort(reason="device_not_found")

        if user_input is not None:
            overwrite_invalid_user_input(user_input)
            climates[index] = {**climates[index], **user_input}
            self._selected_device_id = None
            return self.async_create_entry(
                title="",
                data={**self.config_entry.options, DEVICE_TYPE_CLIMATES: climates}
            )

        schema = self.add_suggested_values_to_schema(
            vol.Schema(climate_data()), climates[index]
        )

        return self.async_show_form(
            step_id="edit_climate",
            data_schema=schema
        )

    async def async_step_remove_climate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle deletion flow removing targeted climate configuration array."""
        if not getattr(self, "_selected_device_id", None):
            self._next_action = "async_step_remove_climate"
            return await self.async_step_select_climate()

        remaining = [c for c in self._get_climates_list() if self._get_device_id_pair(c) != self._selected_device_id]
        self._selected_device_id = None
        return self.async_create_entry(
            title="",
            data={**self.config_entry.options, DEVICE_TYPE_CLIMATES: remaining}
        )

    async def async_step_select_climate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Intermediate routing step ensuring proper climate sub-entity identification."""
        climates = self._get_climates_list()
        if not climates:
            return self.async_abort(reason="device_not_found")

        if user_input is not None:
            self._selected_device_id = user_input["climate_id"]
            return await getattr(self, self._next_action)()

        options = {
            self._get_device_id_pair(c): f"{c.get(CONF_NAME)} ({c.get(CONF_DEVICE_ID)})" 
            for c in climates
        }

        return self.async_show_form(
            step_id="select_climate",
            data_schema=vol.Schema({vol.Required("climate_id"): vol.In(options)})
        )
    
    async def async_step_add_generic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle option schema step adding an infrared remote controller mapper."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            infrared_id = user_input.get(CONF_INFRARED_ID)
            device_id = user_input.get(CONF_DEVICE_ID)
            name = user_input.get(CONF_NAME)
            
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                for cat in [DEVICE_TYPE_CLIMATES, DEVICE_TYPE_GENERICS, DEVICE_TYPE_SENSORS]:
                    if any(d.get(CONF_DEVICE_ID) == device_id for d in entry.options.get(cat, [])):
                        if entry.entry_id == self.config_entry.entry_id:
                            errors["base"] = "device_already_configured"
                        else:
                            errors["base"] = "device_already_configured_on_other_hub"
                        _LOGGER.debug("[%s] Aborting generic addition: device ID %s is already registered", name, device_id)
                        break
                if errors:
                    break

            if not errors:
                client = self.config_entry.runtime_data.api_client
                result = await async_get_generic_device(self.hass, client, infrared_id, device_id)
                
                if not result.success:
                    errors["base"] = "tuya_api_error"
                    placeholders["error_info"] = result.error_info
                    _LOGGER.debug("[%s] Tuya API rejection validation failed for generic target %s: %s", name, device_id, result.error_info)
                else:
                    current_options = dict(self.config_entry.options)
                    generics = list(current_options.get(DEVICE_TYPE_GENERICS, []))
                    generics.append(user_input)
                    return self.async_create_entry(
                        title="",
                        data={**current_options, DEVICE_TYPE_GENERICS: generics}
                    )

        return self.async_show_form(
            step_id="add_generic",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(device1_data()), user_input or {}
            ),
            errors=errors,
            description_placeholders=placeholders
        )

    async def async_step_remove_generic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle option configuration drop actions for generic IR remotes."""
        if not getattr(self, "_selected_device_id", None):
            self._next_action = "async_step_remove_generic"
            return await self.async_step_select_generic()

        current_options = dict(self.config_entry.options)
        generics = list(current_options.get(DEVICE_TYPE_GENERICS, []))
        
        remaining_generics = [
            g for g in generics 
            if self._get_device_id_pair(g) != self._selected_device_id
        ]
        
        self._selected_device_id = None
        return self.async_create_entry(
            title="", 
            data={**current_options, DEVICE_TYPE_GENERICS: remaining_generics}
        )

    async def async_step_select_generic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Selection form routing identifier values to requested generic flows."""
        generics = self._get_generics_list()
        if not generics:
            return self.async_abort(reason="device_not_found")

        if user_input is not None:
            self._selected_device_id = user_input["generic_id"]
            return await getattr(self, self._next_action)()

        options = {
            self._get_device_id_pair(g): f"{g.get(CONF_NAME)} ({g.get(CONF_DEVICE_ID)})" 
            for g in generics
        }

        return self.async_show_form(
            step_id="select_generic",
            data_schema=vol.Schema({vol.Required("generic_id"): vol.In(options)})
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle discovery and validation sequence mapping for temperature/humidity sensors."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input.get(CONF_DEVICE_ID)
            name = user_input.get(CONF_NAME)
            
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                for cat in [DEVICE_TYPE_CLIMATES, DEVICE_TYPE_GENERICS, DEVICE_TYPE_SENSORS]:
                    if any(d.get(CONF_DEVICE_ID) == device_id for d in entry.options.get(cat, [])):
                        if entry.entry_id == self.config_entry.entry_id:
                            errors["base"] = "device_already_configured"
                        else:
                            errors["base"] = "device_already_configured_on_other_hub"
                        _LOGGER.debug("[%s] Aborting: Temperature/Humidity sensor ID %s is already registered", name, device_id)
                        break
                if errors:
                    break

            if not errors:
                client = self.config_entry.runtime_data.api_client
                result = await async_get_sensor_device(self.hass, client, device_id)
                
                if not result.success:
                    errors["base"] = "tuya_api_error"
                    placeholders["error_info"] = result.error_info
                    _LOGGER.debug("[%s] Tuya API validation failed for environmental sensor %s: %s", name, device_id, result.error_info)
                else:
                    sensor_data: TuyaSensorData = result.data

                    if sensor_data.temp_current is None and sensor_data.humidity_value is None:
                        errors["base"] = "invalid_sensor_type"
                    else:
                        if sensor_data.temp_unit_convert is not None:
                            user_input[CONF_TEMP_UNIT] = sensor_data.temp_unit_convert
                            
                        user_input[CONF_SENSOR_TYPES] = []
                        if sensor_data.temp_current is not None:
                            user_input[CONF_SENSOR_TYPES].append(ENTITY_SENSOR_TEMPERATURE)
                        if sensor_data.humidity_value is not None:
                            user_input[CONF_SENSOR_TYPES].append(ENTITY_SENSOR_HUMIDITY)
                        if sensor_data.battery_state is not None:
                            user_input[CONF_SENSOR_TYPES].append(ENTITY_SENSOR_BATTERY)                    
                    
                        current_options = dict(self.config_entry.options)
                        sensors = list(current_options.get(DEVICE_TYPE_SENSORS, []))
                        sensors.append(user_input)
                        return self.async_create_entry(
                            title="",
                            data={**current_options, DEVICE_TYPE_SENSORS: sensors}
                        )

        return self.async_show_form(
            step_id="add_sensor",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(device2_data()), user_input or {}
            ),
            errors=errors,
            description_placeholders=placeholders
        )

    async def async_step_remove_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Drop targeted temperature/humidity tracking hardware mapping."""
        if not getattr(self, "_selected_device_id", None):
            self._next_action = "async_step_remove_sensor"
            return await self.async_step_select_sensor()

        current_options = dict(self.config_entry.options)
        sensors = list(current_options.get(DEVICE_TYPE_SENSORS, []))
        
        remaining_sensors = [
            s for s in sensors 
            if str(s.get(CONF_DEVICE_ID)) != self._selected_device_id
        ]
        
        self._selected_device_id = None
        return self.async_create_entry(
            title="", 
            data={**current_options, DEVICE_TYPE_SENSORS: remaining_sensors}
        )

    async def async_step_select_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Intermediate sensor parsing matching schema strings to device instances."""
        sensors = self._get_sensors_list()
        if not sensors:
            return self.async_abort(reason="device_not_found")

        if user_input is not None:
            self._selected_device_id = user_input["sensor_id"]
            return await getattr(self, self._next_action)()

        options = {
            str(s.get(CONF_DEVICE_ID)): f"{s.get(CONF_NAME)} ({s.get(CONF_DEVICE_ID)})" 
            for s in sensors
        }

        return self.async_show_form(
            step_id="select_sensor",
            data_schema=vol.Schema({vol.Required("sensor_id"): vol.In(options)})
        )

    def _get_device_id_pair(self, device: dict[str, Any]) -> str:
        """Combine specific infrared proxy id with child sub device id string."""
        return f"{device.get(CONF_INFRARED_ID)}_{device.get(CONF_DEVICE_ID)}"

    def _get_climates_list(self) -> list[dict[str, Any]]:
        """Fetch references to assigned Climate domain arrays from options schema."""
        return list(self.config_entry.options.get(DEVICE_TYPE_CLIMATES, []))
        
    def _get_generics_list(self) -> list[dict[str, Any]]:
        """Fetch references to assigned Generic domain arrays from options schema."""
        return list(self.config_entry.options.get(DEVICE_TYPE_GENERICS, []))
        
    def _get_sensors_list(self) -> list[dict[str, Any]]:
        """Fetch references to assigned Standalone Sensor domain arrays from options."""
        return list(self.config_entry.options.get(DEVICE_TYPE_SENSORS, []))


def hub_data_schema() -> dict[vol.Marker, Any]:
    """Generate configuration schema layout defining core Tuya API credentials."""
    return {
        vol.Required(CONF_ACCESS_ID): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
        vol.Required(CONF_ACCESS_SECRET): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
        vol.Required(CONF_TUYA_COUNTRY): SelectSelector(
            SelectSelectorConfig(
                options=list(TUYA_API_ENDPOINTS.keys()),
                multiple=False,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=CONF_TUYA_COUNTRY
            )
        ),
        vol.Required(CONF_CLIMATE_UPDATE_INTERVAL, default=UPDATE_INTERVAL): NumberSelector(
            NumberSelectorConfig(
                min=10, max=3600, step=1, mode=NumberSelectorMode.BOX
            )
        ),
        vol.Required(CONF_SENSOR_UPDATE_INTERVAL, default=UPDATE_INTERVAL): NumberSelector(
            NumberSelectorConfig(
                min=10, max=3600, step=1, mode=NumberSelectorMode.BOX
            )
        ),
        vol.Required(CONF_ENABLE_PULSAR, default=DEFAULT_ENABLE_PULSAR): BooleanSelector()
    }
    
def device1_data() -> dict[vol.Marker, Any]:
    """Return identification schema layout for basic complex IR sub devices."""
    return {
        vol.Required(CONF_INFRARED_ID): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
        vol.Required(CONF_DEVICE_ID): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
        vol.Required(CONF_NAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        )
    }
    
def device2_data() -> dict[vol.Marker, Any]:
    """Return identification schema layout required for hardware physical sensors."""
    return {
        vol.Required(CONF_DEVICE_ID): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
        vol.Required(CONF_NAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        )
    }

def climate_data() -> dict[vol.Marker, Any]:
    """Generate options parameter validation schema exclusively matching Climate limits."""
    return {
        vol.Optional(CONF_TEMPERATURE_SENSOR): EntitySelector(
            EntitySelectorConfig(
                domain=Platform.SENSOR,
                device_class=SensorDeviceClass.TEMPERATURE,
                multiple=False,
            )
        ),
        vol.Optional(CONF_HUMIDITY_SENSOR): EntitySelector(
            EntitySelectorConfig(
                domain=Platform.SENSOR,
                device_class=SensorDeviceClass.HUMIDITY,
                multiple=False,
            )
        ),
        vol.Required(CONF_TEMP_MIN, default=DEFAULT_MIN_TEMP): NumberSelector(
            NumberSelectorConfig(
                min=DEFAULT_MIN_TEMP,
                max=DEFAULT_MAX_TEMP,
                step=1,
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_TEMP_MAX, default=DEFAULT_MAX_TEMP): NumberSelector(
            NumberSelectorConfig(
                min=DEFAULT_MIN_TEMP,
                max=DEFAULT_MAX_TEMP,
                step=1,
                mode=NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_TEMP_STEP, default=DEFAULT_PRECISION): NumberSelector(
            NumberSelectorConfig(
                min=0.1, max=1, step=0.1, mode=NumberSelectorMode.BOX
            )
        ),
        vol.Required(CONF_HVAC_MODES, default=SUPPORTED_HVAC_MODES): SelectSelector(
            SelectSelectorConfig(
                options=SUPPORTED_HVAC_MODES,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=CONF_HVAC_MODES,
            )
        ),
        vol.Required(CONF_FAN_MODES, default=SUPPORTED_FAN_MODES): SelectSelector(
            SelectSelectorConfig(
                options=SUPPORTED_FAN_MODES,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=CONF_FAN_MODES,
            )
        ),
        vol.Optional(CONF_HVAC_PRESETS, default=[]): SelectSelector(
            SelectSelectorConfig(
                options=SUPPORTED_HVAC_PRESETS,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=CONF_HVAC_PRESETS,
            )
        ),
        vol.Optional(CONF_OPTIONAL_ENTITIES, default=[]): SelectSelector(
            SelectSelectorConfig(
                options=SUPPORTED_OPTIONAL_ENTITIES,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=CONF_OPTIONAL_ENTITIES,
            )
        ),
        vol.Required(CONF_COMPATIBILITY_OPTIONS): data_entry_flow.section(
            vol.Schema(
                {
                    vol.Optional(
                        CONF_HVAC_POWER_ON, default=DEFAULT_HVAC_POWER_ON
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=SUPPORTED_POWER_ON_MODES,
                            multiple=False,
                            mode=SelectSelectorMode.LIST,
                            translation_key=CONF_HVAC_POWER_ON,
                        )
                    ),
                    vol.Optional(
                        CONF_TEMP_POWER_ON, default=DEFAULT_TEMP_POWER_ON
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=SUPPORTED_POWER_ON_MODES,
                            multiple=False,
                            mode=SelectSelectorMode.LIST,
                            translation_key=CONF_TEMP_POWER_ON,
                        )
                    ),
                    vol.Optional(
                        CONF_FAN_POWER_ON, default=DEFAULT_FAN_POWER_ON
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=SUPPORTED_POWER_ON_MODES,
                            multiple=False,
                            mode=SelectSelectorMode.LIST,
                            translation_key=CONF_FAN_POWER_ON,
                        )
                    ),
                    vol.Optional(
                        CONF_DRY_MIN_TEMP, default=DEFAULT_DRY_MIN_TEMP
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_DRY_MIN_FAN, default=DEFAULT_DRY_MIN_FAN
                    ): BooleanSelector(),
                }
            ),
            {"collapsed": True},
        ),
    }


async def async_validate_and_connect(data: dict[str, Any]) -> dict[str, str]:
    """Validate credentials against the Tuya OpenAPI backend."""
    errors: dict[str, str] = {}
    
    api_endpoint = TUYA_API_ENDPOINTS.get(data.get(CONF_TUYA_COUNTRY))
    client = TuyaOpenAPI(api_endpoint, data[CONF_ACCESS_ID], data[CONF_ACCESS_SECRET])
    
    try:
        res = await client.connect()
        if not res.get("success"):
            errors["base"] = "invalid_auth"
            _LOGGER.debug("Tuya authentication failed: %s", res.get("msg"))
    except Exception as err:
        errors["base"] = "cannot_connect_to_tuya"
        _LOGGER.debug("Unexpected error connecting to Tuya API: %s", err)
    finally:
        await client.close()
            
    return errors

async def async_get_climate_device(
    hass: HomeAssistant, client: TuyaOpenAPI, infrared_id: str, climate_id: str
) -> TuyaAPIResult:
    """Validate external hardware communication for climate targets via central API."""
    return await TuyaClimateAPI(hass, client).async_fetch_data(infrared_id, climate_id)


async def async_get_generic_device(
    hass: HomeAssistant, client: TuyaOpenAPI, infrared_id: str, device_id: str
) -> TuyaAPIResult:
    """Validate external hardware communication for generic device via central API."""
    return await TuyaGenericAPI(hass, client).async_fetch_data(infrared_id, device_id)
        

async def async_get_sensor_device(
    hass: HomeAssistant, client: TuyaOpenAPI, device_id: str
) -> TuyaAPIResult:
    """Validate external hardware communication for temperature/humidity sensor via central API."""
    return await TuyaSensorAPI(hass, client).async_fetch_data(device_id)


def overwrite_invalid_user_input(user_input: dict[str, Any]) -> None:
    """Enforce fallback lists matching integration defaults on empty arrays."""
    hvac_modes = user_input.get(CONF_HVAC_MODES)
    if hvac_modes is not None and len(hvac_modes) == 0:
        user_input[CONF_HVAC_MODES] = SUPPORTED_HVAC_MODES

    fan_modes = user_input.get(CONF_FAN_MODES)
    if fan_modes is not None and len(fan_modes) == 0:
        user_input[CONF_FAN_MODES] = SUPPORTED_FAN_MODES