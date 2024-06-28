# Home Assistant Tuya IR Air Conditioner Integration

Tested with the following devices:

![image](https://github.com/EnzoD86/tuya-smart-ir-ac/assets/61162811/d887c8a1-9e66-4552-835e-bbe333482a85)


This is a custom integration to control IR-based air conditioners from Tuya via Home Assistant.

![image](https://github.com/EnzoD86/tuya-smart-ir-ac/assets/61162811/271d82ba-d460-4352-9a4d-054e7e607758)


> > **WARNING:** This is by no means a custom component which I can assure works with everything, this is tailored to my needs and is a fork of [DavidIlie's](https://github.com/DavidIlie) project (which I thank for the idea and inspiration).

## Adding it to Home Assistant via yaml configuration

```yaml
climate:
   - platform: tuya_smart_ir_ac
     unique_id: conditioner_id
     name: "conditioner name"
     access_id: ""
     access_secret: ""
     remote_id: ""
     ac_id: ""
     sensor: "sensor.whatever_sensor_you_have"
     min_temp: 18
     max_temp: 30
     temp_step: 1
```

**You can find the IDs from the Tuya Iot Website!**

## Contributions are welcome!

Open a pull request, every contribution is welcome.
