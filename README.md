# Home Assistant Tuya Smart IR Air Conditioner Integration

This is a custom integration to control IR-based air conditioners from Tuya via Home Assistant tested with the following devices:


![344095726-d887c8a1-9e66-4552-835e-bbe333482a85](https://github.com/user-attachments/assets/0c1ed6ea-a2b7-43ca-a979-94ff6e3499dc)

![349898076-b50941eb-8681-4425-ba35-86eafa2ae182](https://github.com/user-attachments/assets/c811bdf9-c9cf-4df3-a1b8-fd4cc7152db9)

>  **This repository was cloned from [DavidIlie's project](https://github.com/DavidIlie/tuya-smart-ir-ac) because it had not been updated for some time.**


## Adding it to Home Assistant via yaml configuration

Add the following section in your configuration.yaml & restart HA (Access ID and Access Secret can be found on the Tuya IoT Website):

```yaml
tuya_smart_ir_ac:
  access_id: "tuya_access_id_example"
  access_secret: "tuya_access_secret_example"
  country: "EU"
```

```yaml
climate:
   - platform: tuya_smart_ir_ac
     climate_id: "climate_id_example"
     infrared_id: "infrared_id_example"
     name: "conditioner name"
     unique_id: conditioner_id
     temperature_sensor: sensor.temperature_name_example
     humidity_sensor: sensor.humidity_name_example
     min_temp: 18
     max_temp: 30
     temp_step: 1
     hvac_modes: ["auto", "cool", "dry", "fan_only", "heat", "off"]
     fan_modes: ["auto", "high", "low", "medium"] 
```


## Contributions are welcome!

If this repository can help anyone, any contribution is welcome.
