# Home Assistant Tuya IR Air Conditioner Integration

Tested with the following devices:

![image](https://github.com/EnzoD86/tuya-smart-ir-ac/assets/61162811/d887c8a1-9e66-4552-835e-bbe333482a85)


## Configuration:

```yaml
climate:
   - platform: tuya_smart_ir_ac
     access_id: ""
     access_secret: ""
     climate_id: ""
     infrared_id: ""
     unique_id: conditioner_id
     name: "conditioner name"
     temp_sensor: "sensor.temperature_name"
     min_temp: 18
     max_temp: 30
     temp_step: 1
```
