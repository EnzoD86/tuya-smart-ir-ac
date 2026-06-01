# Home Assistant Tuya Smart IR Air Conditioner Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![Stable](https://img.shields.io/github/v/release/EnzoD86/tuya-smart-ir-ac)](https://github.com/EnzoD86/tuya-smart-ir-ac/releases/latest)
[![Donate](https://img.shields.io/badge/donate-BuyMeCoffee-yellow.svg)](https://www.buymeacoffee.com/enzod86)

This custom integration brings advanced local-like responsiveness to your Tuya-based Infrared (IR) devices in Home Assistant, combining high-speed cloud status push with robust fallback mechanisms.

With this integration, you can easily control and manage:
- **Infrared Air Conditioners**
- **Generic Infrared Devices**
- **Temperature & Humidity Sensors**

> 💡 **Note:** This repository is an evolved, fully optimized continuation of the original [DavidIlie's project](https://github.com/DavidIlie/tuya-smart-ir-ac). It features a complete architectural rewrite, shifting entirely away from legacy `configuration.yaml` setup to modern **UI Configuration (Config Flow)**, and introduces real-time updates via **Tuya Pulsar WebSocket stream** to avoid unnecessary API throttling.


## Installation using HACS

We recommend installing via the Home Assistant Community Store (HACS) to receive updates automatically.

1. Open **HACS** in your Home Assistant instance.
2. Go to **Integrations** and search for `Tuya Smart IR AC`.
3. Click **Download** and restart Home Assistant.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=EnzoD86&repository=tuya-smart-ir-ac&category=integration)

---

## Prerequisites: Retrieve Tuya IoT Credentials

Before configuring the integration via the UI, you need to collect your cloud credentials from the Tuya IoT Platform and enable the real-time event service.

### 1. Cloud Project Credentials
1. Connect to the [Tuya IoT Development Platform](https://platform.tuya.com).
2. From the left-hand menu, navigate to **Cloud** -> **Development**.
3. Create a new Cloud Project (or select an existing one), ensuring that it is successfully linked to your SmartLife or Tuya mobile app account.
4. From the project **Overview** tab, copy your **Access ID**, **Access Secret**, and identify your **Data Center** region (e.g., Europe, Western America).
5. Go to the **Service API** tab, click **View Details**, and verify that the following APIs are authorized and marked as **In Service**:
   - **IoT Core**
   - **IR Control Hub Open Service**

### 2. Enable Tuya Pulsar & Messaging Rules (Required for Real-Time Updates)
By default, Tuya Cloud does not forward event messages to the WebSocket queue unless explicitly instructed. You **must** configure these settings, otherwise the real-time PUSH stream will remain completely silent.

1. On the [Tuya IoT Platform](https://platform.tuya.com), look at the left main sidebar and navigate to **Cloud** -> **Message Service**.
2. If prompted, select your newly created Cloud Project from the dropdown at the top.
3. Locate the **Pulsar** status toggle on the screen and ensure it is **Enabled / Active**.
4. Switch to the **Messaging Rules** tab right next to it.
5. Click **Create Rule** (or click edit on your default rule) and ensure the main switch for the rule is turned **ON**.
6. Under the **Message Type / Event Filtering** settings, make sure that at least the **`statusReport`** checkbox is selected. 
7. Save the changes and verify that the rule status reads **Enabled**.

---

## Configuration

This integration is configured **exclusively via the Home Assistant User Interface**. No changes to `configuration.yaml` are needed for setup.

### Initial Setup
1. In Home Assistant, go to **Settings** -> **Devices & Services**.
2. Click **Add Integration** in the bottom right corner.
3. Search for **Tuya Smart IR AC** and follow the prompt.
4. Enter your Tuya Cloud Project credentials (**Access ID**, **Access Secret**, and **Country region**).

[![Add Integration to your Home Assistant instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tuya_smart_ir_ac)

### Options and Tuning
Once installed, you can click **Configure / Options** on the integration card anytime to:
- Adjust independent update intervals for your Climate entities.
- Adjust independent update intervals for your Temperature/Humidity Sensor entities.
- Add, update, or remove mapped device IDs.

---

## Debugging

If you encounter issues or want to inspect the real-time WebSocket connection traffic, you can enable detailed debug logging by adding the following block to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.tuya_smart_ir_ac: debug
```
Home Assistant needs to be restarted after this change.

## Contributions are welcome!
If you have ideas to contribute to the project, open a pull request and we will evaluate together how to implement the improvement. Thanks!

## Support me
I dedicate my free time to the development and support for this integration, if you appreciate my work and want to support me, you can buy me a coffee. Thanks!

<a href="https://www.buymeacoffee.com/enzod86" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>
