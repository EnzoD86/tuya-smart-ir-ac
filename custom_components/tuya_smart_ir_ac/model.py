from .helpers import (
    hass_temperature,
    hass_fan_mode,
    hass_hvac_mode,
    hass_battery_state,
    hass_temp_unit
)


class TuyaAPIData(object):
    def __init__(self, url, request, response):
        self.url = url
        self.request = request
        self.response = response

    def to_dict(self):
        return vars(self)


class TuyaClimateData(object):
    def parse_data(self, data):
        self.power = data.get("powerOpen")
        self.hvac_mode = hass_hvac_mode(data.get("mode"))
        self.temperature = hass_temperature(data.get("temp"))
        self.fan_mode = hass_fan_mode(data.get("fan"))
        return self

    def __eq__(self, data):
        return (
            self.power == data.power and
            self.hvac_mode == data.hvac_mode and 
            self.temperature == data.temperature and
            self.fan_mode == data.fan_mode
        )


class TuyaGenericData(object):
    def parse_data(self, data):
        self.category_id = data.get("category_id")
        self.key_list = self.parse_keys(data.get("key_list"))
        return self
         
    def parse_keys(self, key_list):
        keys_data = []
        for key_data in key_list:
            keys_data.append(TuyaGenericKeyData().parse_data(key_data))
        return keys_data


class TuyaGenericKeyData(object):
    def parse_data(self, data):
        self.key = data.get("key")
        self.key_id = data.get("key_id")
        self.key_name = data.get("key_name")
        return self


class TuyaSensorData(object):
    def parse_data(self, data):
        properties = data.get("properties")   
        self.temp_unit_convert = hass_temp_unit(self.get_property(properties, "temp_unit_convert"))
        self.temp_current = hass_temperature(self.get_property(properties, "temp_current"), convert = True)
        self.humidity_value = self.get_property(properties, "humidity_value")
        self.battery_state = hass_battery_state(self.get_property(properties, "battery_state"))
        return self
        
    def get_property(self, properties, key):
        for prop in properties:
            if prop.get("code") == key:
                return prop.get("value")