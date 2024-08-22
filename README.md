# Home Assistant Tuya Smart IR Air Conditioner Integration

This is a custom integration to control IR-based air conditioners from Tuya via Home Assistant tested with the following devices:


![344095726-d887c8a1-9e66-4552-835e-bbe333482a85](https://github.com/user-attachments/assets/0c1ed6ea-a2b7-43ca-a979-94ff6e3499dc)

![349898076-b50941eb-8681-4425-ba35-86eafa2ae182](https://github.com/user-attachments/assets/c811bdf9-c9cf-4df3-a1b8-fd4cc7152db9)

>  **This repository was cloned from [DavidIlie's project](https://github.com/DavidIlie/tuya-smart-ir-ac) because it had not been updated for some time.**


## Platform configuration

Add the following sections in your configuration.yaml and restart HA (Tuya Access ID, Tuya Access Secret can be found on the Tuya IoT Website):

| Name                 | Type     | Description                      | Required |
| -------------------- | -------- | -------------------------------- | -------- |
| access_id            | `string` | Tuya access ID.                  | Yes      |
| access_secret        | `string` | Tuya access secret.              | Yes      |
| country              | `string` | Tuya country API: EU, US, IN, CN | Yes      |


### Country/Data center API

| ID    | Data center |
| ----- | ----------- | 
| EU    | Europe      |
| US    | America     |
| IN    | India       |
| CN    | China       |


### Example

```yaml
tuya_smart_ir_ac:
  access_id: "tuya_access_id_example"
  access_secret: "tuya_access_secret_example"
  country: "EU"
```

Then you can add the "Tuya Smart IR Air Conditioners" integration from the web interface to configure your air conditioners. 
You need to retrieve your Climate ID (Device ID of your air conditioning) and Infrared ID (Device ID of your IR HUB) on the Tuya IoT website.

### Steps to retrieve the information needed for correct configuration
- connect to https://platform.tuya.com/
- from the left menu select Cloud -> Development
- open your cloud project (which you will have previously created and connected to the SmartLife app) by clicking on the "Open Project" button
- in the "Overview" tab you have the "Authorization Key" section where you will find the Access ID and the Access Secret that you must enter in the configuration.yaml
- select the "Devices" tab and you will see the list of all your devices connected to SmartLife
- search in the list of your devices the ID of the infrared hub and the ID of the air conditioner (which you will have previously created on SmartLife)
- in the "Service API" tab make sure that the "IR Control Hub Open Service" API is active;

# Debug
It is possible to activate debug mode by adding the following lines in your configuration.yaml file:

```yaml
logger:
  # Begging of lines to add
  logs:
    custom_components.tuya_smart_ir_ac: debug
  # End of lines to add
```
Home Assistant needs to be restarted after this change.


## Contributions are welcome!

If this repository can help anyone, any contribution is welcome.
