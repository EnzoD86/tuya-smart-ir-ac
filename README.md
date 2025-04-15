# Home Assistant Tuya Smart IR Air Conditioner Integration
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Stable](https://img.shields.io/github/v/release/EnzoD86/tuya-smart-ir-ac)](https://github.com/EnzoD86/tuya-smart-ir-ac/releases/latest)
[![Donate](https://img.shields.io/badge/donate-BuyMeCoffee-yellow.svg)](https://www.buymeacoffee.com/enzod86)

This is a custom integration to control IR-based air conditioners and generic devices from Tuya via Home Assistant tested with the following devices:

![344095726-d887c8a1-9e66-4552-835e-bbe333482a85](https://github.com/user-attachments/assets/0c1ed6ea-a2b7-43ca-a979-94ff6e3499dc)

![349898076-b50941eb-8681-4425-ba35-86eafa2ae182](https://github.com/user-attachments/assets/c811bdf9-c9cf-4df3-a1b8-fd4cc7152db9)

The main purpose of the integration is to manage air conditioners; the integration also partially supports generic devices that are imported as simple buttons.

>  **This repository was cloned from [DavidIlie's project](https://github.com/DavidIlie/tuya-smart-ir-ac) because it had not been updated for some time.**

## Installation using HACS
We recommend installing via Home Assistant Community Store (HACS) to always receive the latest integration updates.
Add this [repository](https://github.com/EnzoD86/tuya-smart-ir-ac) to your custom repositories or click the button below (requires My Homeassistant setup).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=EnzoD86&repository=tuya-smart-ir-ac&category=integration)

## Retrieve correct information from Tuya IoT website
Before you start setting up the integration, you will need some information that can be retrieved from the Tuya IoT platform.
The steps to retrieve the information you need are the following:
- connect to https://platform.tuya.com ;
- from the left menu select Cloud -> Development;
- create a project or select the existing one (making sure it is connected to SmartLife/Tuya app);
- from the Overview tab retrieve the Access ID, Access Secret and Data Center data of the project (which will be used for the installation of the platform);
- from the Service API tab, verify that the following APIs are active (verify by clicking on View details, the API status is In Service for each of them):
  - IoT Core;
  - IR Control Hub Open Service.
- from the Devices tab you will see all your devices connected to SmartLife/Tuya app and you will have to search for the following devices:
  - the HUB IR device (called InfraredID by the integration);
  - the air conditioner connected to the HUB (called ClimateID or DeviceID by the integration).

The last point must be repeated for each air conditioner or generic device that must be configured.

## Platform configuration
Add the following sections in your configuration.yaml and restart HA (Tuya Access ID, Tuya Access Secret can be found on the [Tuya IoT Website](https://platform.tuya.com/)):

| Name                 | Type      | Description                                                         | Required | Default |
| -------------------- | --------- | ------------------------------------------------------------------- | -------- | ------- |
| access_id            | `string`  | Tuya access ID.                                                     | Yes      |         |
| access_secret        | `string`  | Tuya access secret.                                                 | Yes      |         |
| country              | `string`  | Tuya country API: EU (Europe), US (America), IN (India), CN (China) | Yes      |         |
| update_interval      | `integer` | Update interval (in seconds) from tuya server                       | No       | 60      |

### Example
```yaml
tuya_smart_ir_ac:
  access_id: "tuya_access_id_example"
  access_secret: "tuya_access_secret_example"
  country: "EU"
```

## Integration configuration
After the platform has been configured, you can add air conditioners using the Integrations configuration UI.
Go to Settings / Devices & Services and press the Add Integration button, or click the shortcut button below (requires My Homeassistant configured).

[![Add Integration to your Home Assistant
instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tuya_smart_ir_ac)

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
If you have ideas to contribute to the project, open a pull request and we will evaluate together how to implement the improvement. Thanks!

## Support me
I dedicate my free time to the development and support for this integration, if you appreciate my work and want to support me, you can buy me a coffee. Thanks!

<a href="https://www.buymeacoffee.com/enzod86" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>
