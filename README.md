<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/banner_dark.png">
  <source media="(prefers-color-scheme: light)" srcset=".github/assets/banner_light.png">
  <img alt="OpenCarWings — Home Assistant Integration" src=".github/assets/banner_light.png" width="760">
</picture>

<br />
<br />

[![GitHub Release](https://img.shields.io/github/v/release/drrcastro/OCW?style=for-the-badge&logo=github)](https://github.com/drrcastro/OCW/releases)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/drrcastro/OCW?style=for-the-badge&logo=git)](https://github.com/drrcastro/OCW/commits/main)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=white)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.3%2B-18BCF2?style=for-the-badge&logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=drrcastro&repository=OCW&category=integration)

</div>

---

## ✨ Highlights

- **🚗 Remote Vehicle Control:** Start/stop charging, control climate (A/C), lock/unlock doors, flash lights, sound the horn, and remote start/stop.
- **📊 Rich Telemetry & Diagnostics:** State of Charge (SoC), State of Health (SoH), GIDs, remaining energy (kWh), range estimates, TPMS tyre pressures, and Diagnostic Trouble Codes (DTCs).
- **⏰ Native Timer Management:** View active vehicle timers via a `select` entity and create, update, pause, or delete schedules through Home Assistant services.
- **📍 GPS Tracking:** Real-time vehicle location tracking on your Home Assistant map.
- **🗺️ Built-in ABRP Live Telemetry Bridge:** Optionally enter your *A Better Routeplanner* User Token in the integration settings to automatically stream live battery, charging, power, speed, temperature, and GPS telemetry to ABRP—no external scripts or cron jobs required.
- **🔑 Simple UI Setup:** Quick authentication using your Personal API Token with configurable polling intervals.

---

## 📦 Supported Entities

### 📊 Sensors (`sensor`)
- **🔋 Battery & Range:** State of Charge (SoC), State of Charge Display, Range (A/C on / A/C off), Remaining Energy (kWh), Battery Health (SoH), Charge Bars, Capacity Bars, Available GIDs, Maximum GIDs, Battery Counter, Battery Parameter 21, Forced SOC Display, and Battery Lease Contract.
- **⚡ Charging:** Charge Cable (`plugged` / `unplugged`), Charging status, Quick Charging, Charge Finish, Full Charge Time, Limit Charge Time, OBC 6kW time, and OBC 6kW Available.
- **❄️ Climate & Thermal:** Cabin Temperature (°C), AC Status, Battery Heater Available, and Battery Heater Active.
- **🚘 Vehicle State:** Status (`charging`, `running`, `ac_on`, `idle`), Running, Eco Mode, Gear (`Parked`, `Drive`, `Reverse`), Odometer (km), Last Updated, and Last Requested.
- **🛞 Health & TPMS:** Tyre Pressure for all four wheels (FL, FR, RL, RR in kPa), TPMS Warning, Maintenance Alert, Health Report Mileage, and Diagnostic Trouble Codes (`DTCs`, with full trouble code details in attributes).
- **📡 TCU & Connectivity:** Signal Level, Mobile Carrier, TCU Model, TCU Serial, TCU Firmware, TCU Type, TCU Version, Navigation Version, and Map Version.
### 🔌 Binary Sensors (`binary_sensor`)
- **⚡ Power Available:** Indicates whether external charging power is available to the vehicle.
- **⚠️ Charging Interrupted:** Alerts when an active charging session has been unexpectedly interrupted.

### 📍 Location (`device_tracker`)
- **🗺️ Car Location:** Tracks the vehicle's physical GPS coordinates (`latitude` / `longitude`), movement state, speed, and heading.

### 🎛️ Controls (`switch`, `button`, `select`)
- **❄️ Climate (`switch`):** Turn A/C On or Off (automatically polls for vehicle confirmation).
- **⏰ Timer Selector (`select`):** Select an active vehicle timer (`Timer ID`) and view all configured timers in its state attributes.
- **🔄 Refresh (`button`):**
  - **OpenCARWINGS Refresh:** Immediately refresh coordinator data from the OpenCARWINGS server.
  - **Refresh Data:** Request an immediate wakeup and data sync directly from the vehicle TCU.
- **🔋 Charging (`button`):** Start Charge (100%), Start Charge 80%.
- **🔊 Horn & Lights (`button`):** Horn, Lights, Horn & Lights, Stop Horn & Lights.
- **🚪 Doors (`button`):** Unlock Doors, Lock Doors *(Requires PIN 🔒)*.
- **🚗 Engine (`button`):** Remote Start, Remote Stop *(Requires PIN 🔒)*.

> [!IMPORTANT]
> Commands marked with *(Requires PIN 🔒)* require a **Command PIN** configured in your OpenCARWINGS account portal and entered in the integration settings.

---

## 🔧 Installation

### Option 1: HACS (Recommended)

1. Click the button below or manually add `https://github.com/drrcastro/OCW` as a **Custom Repository** (Category: **Integration**) in HACS:

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=drrcastro&repository=OCW&category=integration)

2. Search for **OpenCarWings** in HACS and click **Download**.
3. **Restart Home Assistant**.
4. Go to **Settings → Devices & Services → Add Integration** and search for **OpenCarWings**.

### Option 2: Manual Installation

1. Download or clone this repository.
2. Copy the `custom_components/ocw_integration` folder into your Home Assistant `<config>/custom_components/` directory.
3. **Restart Home Assistant**.
4. Go to **Settings → Devices & Services → Add Integration** and search for **OpenCarWings**.

---

## ⚙️ Configuration

Configuration is managed entirely through the Home Assistant UI (and can be updated anytime via the **Configure** button on the integration entry):

- **🔑 API Key** *(Required)*: Your personal API token from the [OpenCARWINGS Portal](https://opencarwings.viaaq.eu) → *Account Settings* → *API Token* (copy the full string in the format `Token xxxxxxxxxxxxxx`).
- **🔒 Command PIN** *(Optional)*: Required only for security-sensitive commands (Doors Lock/Unlock and Remote Start/Stop).
- **🗺️ ABRP User Token** *(Optional)*: Your generic telemetry token from [A Better Routeplanner](https://abetterrouteplanner.com/) (*Car Settings → Live Data → Generic*). When provided and the vehicle is **ON (driving) or charging**, the integration requests 1-minute updates from the vehicle and forwards live telemetry (SoC, SoH, SoE, degraded usable capacity, power, speed, temperatures, odometer, TPMS, and GPS) to ABRP every 30 seconds, stopping automatically once the vehicle is parked and off. When left blank, updates follow your configured Scan Interval and OpenCARWINGS server schedule.
- **⏱️ Scan Interval** *(Default: `15 minutes`)*: Cloud polling interval (`1 min`, `5 min`, `10 min`, `15 min`, `30 min`, `1 h`, `3 h`, `6 h`, `12 h`, or `1 day`).
- **🌐 API Base URL** *(Default: `https://opencarwings.viaaq.eu`)*: Base URL of your OpenCARWINGS server instance.

> [!NOTE]
> All sensors report native metric units (`km`, `kWh`, `°C`, `kPa`) and Home Assistant automatically converts them to match your profile's unit system.

---

## ⏰ Services & Timers

The integration provides four services under the `ocw_integration` domain:

- `ocw_integration.refresh` — Force an immediate refresh of the integration coordinator.
- `ocw_integration.create_timer` — Create a one-time or recurring weekly vehicle timer.
- `ocw_integration.update_timer` — Modify an existing timer or pause/resume it (`enabled: false` / `true`).
- `ocw_integration.delete_timer` — Permanently delete a timer by its `timer_id`.

<details>
<summary><b>📄 View YAML Service Examples</b></summary>

### Create a Weekly Climate Timer (Mon–Fri at 07:30)
```yaml
action: ocw_integration.create_timer
data:
  name: "Morning Cabin Pre-heat"
  time: "07:30:00"
  command_type: "3"       # 3 = Turn A/C on, 2 = Start charging, 6 = Charge to 80%
  timer_type: "1"         # 0 = One time, 1 = Weekly
  enabled: true
  weekday_mon: true
  weekday_tue: true
  weekday_wed: true
  weekday_thu: true
  weekday_fri: true
```

### Pause an Existing Timer Without Deleting It
```yaml
action: ocw_integration.update_timer
data:
  timer_id: 12
  enabled: false
```

### Delete a Timer
```yaml
action: ocw_integration.delete_timer
data:
  timer_id: 12
```

</details>

---

## 🙏 Credits & Acknowledgements

- Original integration base by **@czapeczek** and **@tomeczko**.
- Special thanks to the [OpenCARWINGS](https://github.com/developerfromjokela/opencarwings) project by **@developerfromjokela** for reverse-engineering and maintaining the API that makes this integration possible.
