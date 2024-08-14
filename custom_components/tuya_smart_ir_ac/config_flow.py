import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant import config_entries
from homeassistant.const import (
    CONF_NAME,
    Platform
)
from homeassistant.components.climate.const import (
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP
)
from .const import (
    DOMAIN,
    CLIENT,
    CONF_INFRARED_ID,
    CONF_CLIMATE_ID,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_TEMP_MIN,
    CONF_TEMP_MAX,
    CONF_TEMP_STEP,
    CONF_HVAC_MODES,
    CONF_FAN_MODES,
    DEFAULT_PRECISION,
    DEFAULT_HVAC_MODES,
    DEFAULT_FAN_MODES
)
from .api import TuyaAPI


class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
    
    async def async_step_user(self, user_input):
        errors = {}

        domain_config  = self.hass.data.get(DOMAIN, {})
        client = domain_config.get(CLIENT, None)
        if client is None:
            return self.async_abort(reason="credentials")

        if user_input is not None:
            infrared_id = user_input.get(CONF_INFRARED_ID)
            climate_id = user_input.get(CONF_CLIMATE_ID)
            
            if await TuyaAPI(self.hass, client).async_fetch_data(infrared_id, climate_id):
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
            else:
                errors["base"] = "connection"

        data = {}
        data.update(required_data())
        data.update(optional_data())
        data_schema = vol.Schema(data)
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input):
        return await self.async_step_user(user_input)
        
    async def async_step_user(self, user_input):
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=self.config_entry.data | user_input
            )
            return self.async_create_entry(title="", data={})

        config = {**self.config_entry.data, **self.config_entry.options}
        data_schema = vol.Schema(optional_data(config))
        return self.async_show_form(step_id="user", data_schema=data_schema)


def required_data():
    return {
        vol.Required(CONF_INFRARED_ID): cv.string,
        vol.Required(CONF_CLIMATE_ID): cv.string,
        vol.Required(CONF_NAME): cv.string
    }
    
def optional_data(config=None):
    if config is None:
        temperature_sensor = vol.Optional(CONF_TEMPERATURE_SENSOR)
        humidity_sensor = vol.Optional(CONF_HUMIDITY_SENSOR)
        default_temp_min = DEFAULT_MIN_TEMP
        default_temp_max = DEFAULT_MAX_TEMP
        default_temp_step = DEFAULT_PRECISION
        default_hvac_modes = DEFAULT_HVAC_MODES
        default_fan_modes = DEFAULT_FAN_MODES
    else:
        if config.get(CONF_TEMPERATURE_SENSOR, None) is None:
            temperature_sensor = vol.Optional(CONF_TEMPERATURE_SENSOR)
        else:
            temperature_sensor = vol.Optional(CONF_TEMPERATURE_SENSOR, default=config.get(CONF_TEMPERATURE_SENSOR))
        
        if config.get(CONF_TEMPERATURE_SENSOR, None) is None:
            humidity_sensor = vol.Optional(CONF_HUMIDITY_SENSOR)
        else:
            humidity_sensor = vol.Optional(CONF_HUMIDITY_SENSOR, default=config.get(CONF_HUMIDITY_SENSOR))

        default_temp_min = config.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP)
        default_temp_max = config.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP)
        default_temp_step = config.get(CONF_TEMP_STEP, DEFAULT_PRECISION)
        default_hvac_modes = config.get(CONF_HVAC_MODES, DEFAULT_HVAC_MODES)
        default_fan_modes = config.get(CONF_FAN_MODES, DEFAULT_FAN_MODES)

    return {
        temperature_sensor: selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=Platform.SENSOR,
                device_class="temperature",
                multiple=False
            )
        ),
        humidity_sensor: selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=Platform.SENSOR,
                device_class="humidity",
                multiple=False
            )
        ),
        vol.Optional(CONF_TEMP_MIN, default=default_temp_min): vol.Coerce(float),
        vol.Optional(CONF_TEMP_MAX, default=default_temp_max): vol.Coerce(float),
        vol.Optional(CONF_TEMP_STEP, default=default_temp_step): vol.Coerce(float),
        vol.Optional(CONF_HVAC_MODES, default=default_hvac_modes): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=DEFAULT_HVAC_MODES, 
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN
            )
        ),
        vol.Optional(CONF_FAN_MODES, default=default_fan_modes): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=DEFAULT_FAN_MODES, 
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN
            )
        )
    }