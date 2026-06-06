# Tuya Smart IR AC Integration for Home Assistant

This integration allows you to control Air Conditioners and generic infrared devices managed via a Tuya Smart IR Hub using the Tuya IoT Cloud Platform. It provides real-time status updates and local-like responsiveness via the Tuya Pulsar messaging service.

With this integration, you can easily control and manage:
- **Infrared Air Conditioners**
- **Generic Infrared Devices**
- **Temperature & Humidity Sensors**

> 💡 **Note:** This repository is an evolved, fully optimized continuation of the original [DavidIlie's project](https://github.com/DavidIlie/tuya-smart-ir-ac). It features a complete architectural rewrite, shifting entirely away from legacy `configuration.yaml` setup to modern **UI Configuration (Config Flow)**, and introduces real-time updates via **Tuya Pulsar WebSocket stream** to avoid unnecessary API throttling.


---

## Installation

### Method 1: Via HACS (Recommended)
The easiest way to install this integration and receive automatic updates is through the [Home Assistant Community Store (HACS)](https://hacs.xyz/).

1. Open **HACS** in your Home Assistant instance.
2. Navigate to **Integrations** and click the three dots in the top right corner.
3. Select **Custom repositories** and add this repository URL with the category set to `Integration`.
4. Search for `Tuya Smart IR AC` and click **Download**.
5. **Restart** Home Assistant to apply the changes.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=EnzoD86&repository=tuya-smart-ir-ac&category=integration)

### Method 2: Manual Installation
1. Download the latest release from the GitHub repository.
2. Extract the `custom_components/tuya_smart_ir_ac` directory.
3. Copy this directory into your Home Assistant installation's `custom_components/` folder.
4. **Restart** Home Assistant.

---
## Setup

### Step 1: Tuya Cloud Project Setup

Before configuring the integration in Home Assistant, you must set up a cloud project on the Tuya IoT Platform to retrieve your API credentials.

### 1. Create a Cloud Project
1. Log into the [Tuya IoT Development Platform](https://platform.tuya.com).
2. From the left-hand sidebar, navigate to **Cloud** ➔ **Project Management**.
3. Click **Create Cloud Project** (or select an existing one).
4. Fill in the project details:
   * **Project Name / Description:** Enter any friendly name.
   * **Industry:** Select `Smart Home`.
   * **Development Method:** Select `Smart Home`.
   * **Data Center:** You **must** select the data center matching the country set in your Smart Life app account. Refer to the [Tuya Data Center Mapping Guide](https://developer.tuya.com/en/docs/iot/oem-app-data-center-distributed?id=Kafi0ku9l07qb) to find your correct region.
5. Click **Create**.
6. On the next screen (**Authorize API Services** wizard), ensure that **IoT Core** and **IR Control Hub Open Services** are checked.
7. Click **Authorize**.

### 2. Link your Smart Life App Account
To see your physical devices in the cloud project, you need to link your mobile application account.
1. On your project page, navigate to the **Devices** tab.
2. Click **Link App Account** (do *not* use "Link My App").
3. Click **Add App Account**. A QR code will be displayed.
4. Open the **Smart Life** app on your phone, tap the **[+]** or scan icon in the top right, and scan the QR code.
5. Confirm the authorization on your phone.
6. Your account is now linked. You will see a list of your devices under the project. **Take note of your Device IDs here**, as you will need them during the Home Assistant setup.

### 3. Retrieve Credentials
1. Navigate back to the project **Overview** tab.
2. Copy and save your **Access ID**, **Access Secret**, and your **Data Center** region (e.g., Europe, Western America).

---

## Step 2: Enable Tuya Pulsar Service (For Real-Time Updates)

By default, the Tuya Cloud does not forward real-time event messages to the integration unless explicitly instructed. If you skip this step, your entity states in Home Assistant will not update immediately when changes happen outside of HA.

1. In the **Tuya IoT Platform**, go to **Cloud** ➔ **Development** ➔ *Select your project* ➔ **Message Service** tab.
2. Ensure the main **Message Service** toggle switch at the top is turned **ON (Enabled)**.
3. Click on the **Production Environment** tab. 
   > ⚠️ **Important:** Home Assistant ignores the Test Environment entirely. All configurations must be done under Production.
4. Under the **Messaging Rules / Subscriptions** section, explicitly enable the following message types (**BizCode**):
   * `devicePropertyMessage` (Device Property Message) — *Crucial for climate state and telemetry updates.*
   * `statusReport` (Status Report) — *Crucial for real-time reporting.*
   * `deviceEventMessage` (Device Event Message)
   * `deviceActionResponseMessage` (Device Action Response Message)

> 💡 **Troubleshooting Tip:** If these are already checked but your entities aren't updating in real-time, uncheck them, save, and re-check them to force Tuya to rebuild its backend routing rules.

---

## Step 3: Home Assistant Configuration

Configuration is done **exclusively via the Home Assistant User Interface**. No changes to `configuration.yaml` are required.

 Setup follows a two-part flow: First, you add the **Tuya Smart IR Hub**, and then you add individual **AC / Generic Devices** to that hub.

### 1. Adding the Hub
1. In Home Assistant, navigate to **Settings** ➔ **Devices & Services**.
2. Click **Add Integration** in the bottom right corner.
3. Search for **Tuya Smart IR AC** and select it.
4. Enter your credentials collected in Step 1.3:
   * **Access ID**
   * **Access Secret**
   * **Country Region**
5. Leave intervals at their default values unless you have a specific optimization use-case. (The Tuya Pulsar stream toggle is optional and disabled by default).
6. Click **Submit**.

[![Add Integration to your Home Assistant instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tuya_smart_ir_ac)

### 2. Adding Air Conditioners and Devices
Once the main hub is added, you can populate it with your configured IR sub-devices:

1. Locate the **Tuya Smart IR Hub** in your **Devices & Services** dashboard.
2. Click the **Configure** (or gear icon) button on the integration card.
3. Select **Device Management** ➔ **Air Conditioner Management** ➔ **Add a new Air Conditioner**.
4. Configure the entity properties:
   * **Infrared Hub ID:** Paste the Device ID of the physical Tuya IR Hub itself (found in step 1.2).
   * **Air Conditioner ID:** Paste the Device ID of the virtual remote control added underneath the hub inside the Smart Life app.
   * **Air Conditioner Name:** Enter a friendly name for your new climate entity.
5. Adjust any optional performance tuning settings as needed and click **Submit**.

Your new climate entity is now ready for use! 

### Modifying Existing Devices
If you ever need to adjust names, IDs, or settings, simply re-run the configuration wizard by clicking **Configure** on the integration page and choosing the appropriate management sub-menu.
