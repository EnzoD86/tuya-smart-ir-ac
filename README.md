# Home Assistant Tuya IR Air Conditioner Integration

[![YouTube Video](https://img.youtube.com/vi/A8ICsEnGfkg/0.jpg)](https://www.youtube.com/watch?v=A8ICsEnGfkg)

This is a custom integration to control IR-based air conditioners from Tuya via Home Assistant.

![Example Image](https://github.com/DavidIlie/tuya-smart-ir-ac/assets/47594764/c91995e3-474c-47df-83f6-eaf64371a1d4)

> **WARNING:** This is by no means a custom component which I can assure works with everything, this is tailored to my needs as part of my initial project which you can find [here](https://davidilie.com) but I hope to work on making it more broad and also a standard repository with a good dev environment. Maybe someone can help me out here.

## Adding it to Home Assistant

I don't know how to create a UI (SOMETHING TODO) so here is the basic configuration for HA:

```yaml
climate:
   - platform: tuya_smart_ir_ac
     name: "Thermostat"
     sensor: "sensor.whatever_sensor_you_have"
     access_id: ""
     access_secret: ""
     remote_id: ""
     ac_id: ""
```

**You can find the IDs from the Tuya Iot Website!**

## Contributions are welcome!

Open a pull request, every contribution is welcome.
