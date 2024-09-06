import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant import config_entries
from homeassistant.const import (
    CONF_NAME,
    Platform
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
    CONF_HVAC_POWER_ON,
    CONF_DRY_MIN_TEMP,
    CONF_DRY_MIN_FAN,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_PRECISION,
    DEFAULT_HVAC_MODES,
    DEFAULT_FAN_MODES,
    DEFAULT_HVAC_POWER_ON,
    DEFAULT_DRY_MIN_TEMP,
    DEFAULT_DRY_MIN_FAN
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
        temp_min = vol.Optional(CONF_TEMP_MIN, default=DEFAULT_MIN_TEMP)
        temp_max = vol.Optional(CONF_TEMP_MAX, default=DEFAULT_MAX_TEMP)
        temp_step = vol.Optional(CONF_TEMP_STEP, default=DEFAULT_PRECISION)
        hvac_modes = vol.Optional(CONF_HVAC_MODES, default=DEFAULT_HVAC_MODES)
        fan_modes = vol.Optional(CONF_FAN_MODES, default=DEFAULT_FAN_MODES)
        hvac_power_on = vol.Optional(CONF_HVAC_POWER_ON, default=DEFAULT_HVAC_POWER_ON)
        dry_min_temp = vol.Optional(CONF_DRY_MIN_TEMP, default=DEFAULT_DRY_MIN_TEMP)
        dry_min_fan = vol.Optional(CONF_DRY_MIN_FAN, default=DEFAULT_DRY_MIN_FAN)
    else:
        if config.get(CONF_TEMPERATURE_SENSOR, None) is None:
            temperature_sensor = vol.Optional(CONF_TEMPERATURE_SENSOR)
        else:
            temperature_sensor = vol.Optional(CONF_TEMPERATURE_SENSOR, default=config.get(CONF_TEMPERATURE_SENSOR))
        
        if config.get(CONF_TEMPERATURE_SENSOR, None) is None:
            humidity_sensor = vol.Optional(CONF_HUMIDITY_SENSOR)
        else:
            humidity_sensor = vol.Optional(CONF_HUMIDITY_SENSOR, default=config.get(CONF_HUMIDITY_SENSOR))
        
        temp_min = vol.Optional(CONF_TEMP_MIN, default=config.get(CONF_TEMP_MIN, DEFAULT_MIN_TEMP))
        temp_max = vol.Optional(CONF_TEMP_MAX, default=config.get(CONF_TEMP_MAX, DEFAULT_MAX_TEMP))
        temp_step = vol.Optional(CONF_TEMP_STEP, default=config.get(CONF_TEMP_STEP, DEFAULT_PRECISION))
        hvac_modes = vol.Optional(CONF_HVAC_MODES, default=config.get(CONF_HVAC_MODES, DEFAULT_HVAC_MODES))
        fan_modes = vol.Optional(CONF_FAN_MODES, default=config.get(CONF_FAN_MODES, DEFAULT_FAN_MODES))
        hvac_power_on = vol.Optional(CONF_HVAC_POWER_ON, default=config.get(CONF_HVAC_POWER_ON, DEFAULT_HVAC_POWER_ON))
        dry_min_temp = vol.Optional(CONF_DRY_MIN_TEMP, default=config.get(CONF_DRY_MIN_TEMP, DEFAULT_DRY_MIN_TEMP))
        dry_min_fan = vol.Optional(CONF_DRY_MIN_FAN, default=config.get(CONF_DRY_MIN_FAN, DEFAULT_DRY_MIN_FAN))

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
        temp_min: selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=DEFAULT_MIN_TEMP,
                max=DEFAULT_MAX_TEMP,
                step=1,
                mode=selector.NumberSelectorMode.BOX
            )
        ),
        temp_max: selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=DEFAULT_MIN_TEMP,
                max=DEFAULT_MAX_TEMP,
                step=1,
                mode=selector.NumberSelectorMode.BOX
            )
        ),
        temp_step: selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1,
                max=1,
                step=0.1,
                mode=selector.NumberSelectorMode.BOX
            )
        ),
        hvac_modes: selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=DEFAULT_HVAC_MODES, 
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN
            )
        ),
        fan_modes: selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=DEFAULT_FAN_MODES, 
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN
            )
        ),
        hvac_power_on: selector.BooleanSelector(),
        dry_min_temp: selector.BooleanSelector(),
        dry_min_fan: selector.BooleanSelector()
    }