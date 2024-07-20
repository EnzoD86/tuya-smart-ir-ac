# Home Assistant Tuya IR Air Conditioner Integration

This is a custom integration to control IR-based air conditioners from Tuya via Home Assistant tested with the following devices:


![344095726-d887c8a1-9e66-4552-835e-bbe333482a85](https://github.com/user-attachments/assets/0c1ed6ea-a2b7-43ca-a979-94ff6e3499dc)

![349898076-b50941eb-8681-4425-ba35-86eafa2ae182](https://github.com/user-attachments/assets/c811bdf9-c9cf-4df3-a1b8-fd4cc7152db9)

>  **This repository was cloned from [DavidIlie's project](https://github.com/DavidIlie/tuya-smart-ir-ac) because it had not been updated for some time.**


## Adding it to Home Assistant via yaml configuration

```yaml
climate:
   - platform: tuya_smart_ir_ac
     access_id: ""
     access_secret: ""
     climate_id: ""
     infrared_id: ""
     name: "conditioner name"
     unique_id: conditioner_id
     temperature_sensor: sensor.temperature_name
     humidity_sensor: sensor.humidity_name
     min_temp: 18
     max_temp: 30
     temp_step: 1
     country: "EU"
```

**You can find the IDs from the Tuya Iot Website!**

## Contributions are welcome!

If this repository can help anyone, any contribution is welcome.
