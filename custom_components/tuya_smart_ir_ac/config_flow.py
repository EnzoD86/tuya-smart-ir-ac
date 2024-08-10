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

        schema = vol.Schema(
            {
                vol.Required(CONF_INFRARED_ID): cv.string,
                vol.Required(CONF_CLIMATE_ID): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Optional(CONF_TEMPERATURE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=Platform.SENSOR, 
                        device_class="temperature",
                        multiple=False
                    )
                ),
                vol.Optional(CONF_HUMIDITY_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=Platform.SENSOR,
                        device_class="humidity",
                        multiple=False
                    )
                ),
                vol.Optional(CONF_TEMP_MIN, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
                vol.Optional(CONF_TEMP_MAX, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
                vol.Optional(CONF_TEMP_STEP, default=DEFAULT_PRECISION): vol.Coerce(float),
                vol.Optional(CONF_HVAC_MODES, default=DEFAULT_HVAC_MODES): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=DEFAULT_HVAC_MODES, 
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Optional(CONF_FAN_MODES, default=DEFAULT_FAN_MODES): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=DEFAULT_FAN_MODES, 
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN
                    )
                ) 
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

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

        #####################################################################################
        # WORKAROUND:                                                                       #
        # the EntitySelector does not work correctly with a default value of None or empty. #
        # Added this workaround to bypass the problem.... worth looking into in the future! #
        #####################################################################################

        schema_dict = conf_option_flow_temperature(config)
        schema_dict.update(conf_option_flow_umidity(config))
        schema_dict.update(conf_option_flow(config))
        schema = vol.Schema(schema_dict)

        # TODO: restore original schema!!!
        #schema = vol.Schema(
        #    {
        #        vol.Optional(CONF_TEMPERATURE_SENSOR, default={}): selector.EntitySelector(
        #            selector.EntitySelectorConfig(
        #                domain=Platform.SENSOR,
        #                device_class="temperature",
        #                multiple=False
        #            )
        #        ),
        #        vol.Optional(CONF_HUMIDITY_SENSOR, default=config.get(CONF_HUMIDITY_SENSOR, "")): selector.EntitySelector(
        #            selector.EntitySelectorConfig(
        #                domain=Platform.SENSOR, 
        #                device_class="humidity",
        #                multiple=False
        #            )
        #        ),
        #        vol.Optional(CONF_TEMP_MIN, default=config.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP)): vol.Coerce(float),
        #        vol.Optional(CONF_TEMP_MAX, default=config.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP)): vol.Coerce(float),
        #        vol.Optional(CONF_TEMP_STEP, default=config.get(CONF_TEMP_STEP, DEFAULT_PRECISION)): vol.Coerce(float),
        #        vol.Optional(CONF_HVAC_MODES, default=config.get(CONF_HVAC_MODES, DEFAULT_HVAC_MODES)): selector.SelectSelector(
        #            selector.SelectSelectorConfig(
        #                options=DEFAULT_HVAC_MODES, 
        #                multiple=True,
        #                mode=selector.SelectSelectorMode.DROPDOWN
        #            )
        #        ),
        #        vol.Optional(CONF_FAN_MODES, default=config.get(CONF_FAN_MODES, DEFAULT_FAN_MODES)): selector.SelectSelector(
        #            selector.SelectSelectorConfig(
        #                options=DEFAULT_FAN_MODES, 
        #                multiple=True,
        #                mode=selector.SelectSelectorMode.DROPDOWN
        #            )
        #        ) 
        #    }
        #)

        return self.async_show_form(step_id="user", data_schema=schema)


# TODO: to be removed when the bug is fixed!
def conf_option_flow_temperature(config):
    if config.get(CONF_TEMPERATURE_SENSOR, None) is None:
        return {
            vol.Optional(CONF_TEMPERATURE_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=Platform.SENSOR,
                    device_class="temperature",
                    multiple=False
                )
            )
        }
    else:
        return {
            vol.Optional(CONF_TEMPERATURE_SENSOR, default=config.get(CONF_TEMPERATURE_SENSOR)): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=Platform.SENSOR,
                    device_class="temperature",
                    multiple=False
                )
            )
        }

# TODO: to be removed when the bug is fixed!
def conf_option_flow_umidity(config):
    if config.get(CONF_HUMIDITY_SENSOR, None) is None:
        return {
            vol.Optional(CONF_HUMIDITY_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=Platform.SENSOR, 
                    device_class="humidity",
                    multiple=False
                )
            )
        }
    else:
        return {
            vol.Optional(CONF_HUMIDITY_SENSOR, default=config.get(CONF_HUMIDITY_SENSOR)): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=Platform.SENSOR,
                    device_class="humidity",
                    multiple=False
                )
            )
        }
     
# TODO: to be removed when the bug is fixed!
def conf_option_flow(config):
    return {
        vol.Optional(CONF_TEMP_MIN, default=config.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP)): vol.Coerce(float),
        vol.Optional(CONF_TEMP_MAX, default=config.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP)): vol.Coerce(float),
        vol.Optional(CONF_TEMP_STEP, default=config.get(CONF_TEMP_STEP, DEFAULT_PRECISION)): vol.Coerce(float),
        vol.Optional(CONF_HVAC_MODES, default=config.get(CONF_HVAC_MODES, DEFAULT_HVAC_MODES)): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=DEFAULT_HVAC_MODES, 
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN
            )
        ),
        vol.Optional(CONF_FAN_MODES, default=config.get(CONF_FAN_MODES, DEFAULT_FAN_MODES)): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=DEFAULT_FAN_MODES, 
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN
            )
        )
    }