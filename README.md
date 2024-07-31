# Home Assistant Tuya Smart IR Air Conditioner Integration

This is a custom integration to control IR-based air conditioners from Tuya via Home Assistant tested with the following devices:


![344095726-d887c8a1-9e66-4552-835e-bbe333482a85](https://github.com/user-attachments/assets/0c1ed6ea-a2b7-43ca-a979-94ff6e3499dc)

![349898076-b50941eb-8681-4425-ba35-86eafa2ae182](https://github.com/user-attachments/assets/c811bdf9-c9cf-4df3-a1b8-fd4cc7152db9)

>  **This repository was cloned from [DavidIlie's project](https://github.com/DavidIlie/tuya-smart-ir-ac) because it had not been updated for some time.**


## Configuration

Add the following sections in your configuration.yaml and restart HA (Access ID, Access Secret can be found on the Tuya IoT Website):

```yaml
tuya_smart_ir_ac:
  access_id: "tuya_access_id_example"
  access_secret: "tuya_access_secret_example"
  country: "EU"
```

Then you can add the "Tuya Smart IR Air Conditioners" integration from the web interface to configure your air conditioners. You need to retrieve your Climate ID and Infrared ID on the Tuya IoT website.

## Third-party libraries
The integration uses a modified version of the [Tuya connector python library](https://github.com/tuya/tuya-connector-python) to resolve some issues related to token renewal.


## Contributions are welcome!

If this repository can help anyone, any contribution is welcome.
