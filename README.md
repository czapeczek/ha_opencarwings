# OpenCARWINGS Home Assistant Integration

[![Install in Home Assistant](https://my.home-assistant.io/badges/installer.svg)](https://my.home-assistant.io/redirect/integration_start?domain=ha_opencarwings)  [![HACS](https://img.shields.io/badge/HACS-Integration-blue?logo=home-assistant)](https://hacs.xyz)  [![Repository](https://img.shields.io/badge/repo-gh-blue.svg)](https://github.com/czapeczek/ha_opencarwings)

Nice, lightweight Home Assistant integration that connects to the OpenCARWINGS API to expose your Nissan (or compatible) cars as devices in Home Assistant.

---

## Support the project ☕

This is my first integration for HA. If you find it useful I'd really appreciate if you buy me a coffe:
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/czapeczek)


---

## What it supports ✅

Per car the integration currently exposes:

- Sensors
  - Battery level / State of Charge
  - Range (A/C on / A/C off)
  - Charge cable plugged in (plugged / unplugged)
  - High-level status (charging / running / ac_on / idle)
  - **Per-car "Last Updated"** (diagnostic): reports the ISO 8601 timestamp of the last direct reading from the car. The sensor is created per VIN, shows the most recent timestamp found in `ev_info.last_updated`, `location.last_updated`, or `last_connection`, and has the unique id pattern `ha_opencarwings_last_updated_<VIN>`.
  - A top-level `OpenCARWINGS Cars` sensor listing your cars and VINs
- Device tracker: car GPS (uses `last_location` / `location` returned by the API). The tracker/visible name prefers the car's `nickname` if present, otherwise it falls back to `model_name`. The visible name intentionally excludes the VIN and the "Car" prefix (for example, "MyCar Tracker"). The tracker entity keeps a stable `unique_id` of the form `ha_opencarwings_tracker_<VIN>`.
- Switch: A/C control (on/off) — sends commands to the car via the OpenCARWINGS command endpoint
- Button: **Manual refresh** — a per-integration button is available to force an immediate refresh from the OpenCARWINGS service (unique id: `ha_opencarwings_refresh_<entry_id>`).
- Button: **Per-car "Request refresh"** — each car also has a per-vehicle button that sends a "Refresh data" command to OpenCARWINGS (unique id: `ha_opencarwings_car_refresh_<VIN>`).

---

## History & Recorder ⚠️

The per-car **Last Updated** sensors are marked as diagnostic (they're metadata, not a regularly changing state) and are typically not recorded by Home Assistant's Recorder. If you want to ensure these sensors are excluded from history/recorder, add an exclusion to your `configuration.yaml`:

```yaml
recorder:
  exclude:
    entity_globs:
      - "sensor.ha_opencarwings_last_updated_*"
```

This will prevent per-car `Last Updated` sensors from being stored in your database and showing up in history charts.

---

## Entity names & unique IDs 🔎

A few helpful naming/ID patterns to identify entities created by the integration:

- Device tracker name: uses `nickname` when available, otherwise `model_name`. Visible name example: `MyCar Tracker`.
- Tracker unique_id: `ha_opencarwings_tracker_<VIN>`
- Per-car "Last Updated" sensor: `ha_opencarwings_last_updated_<VIN>`
- Battery sensor: `ha_opencarwings_battery_<VIN>`
- A/C switch: `ha_opencarwings_ac_<VIN>`

These stable IDs are useful when excluding entities from the recorder or when writing automations targeting specific cars.

These entities are created per-VIN and appear as devices in the Integrations UI.

---

## Installation 🔧

Choose one of the options below:

1. HACS (recommended)
   - In HACS: Integrations → three dots → Custom repositories → Add this repository as category "Integration" → Install → Restart Home Assistant
2. Manual
   - Copy the `custom_components/ha_opencarwings` directory into `<config>/custom_components/` on your Home Assistant host
   - Restart Home Assistant
   - Go to Settings → Devices & Services → Add Integration → search for **OpenCARWINGS** and follow the setup flow

---

## Configuration ⚙️

Setup is done via the UI. You will need:

- **Username** and **Password** for your OpenCARWINGS account
- **Scan interval** (polling frequency, default: 15 minutes)
- **API base URL** (optional — defaults to the known OpenCARWINGS endpoint)

The integration obtains JWT tokens (access & refresh) during setup and refreshes tokens automatically.

---

## Development & Tests 🧪

- Run tests with: `pytest`
- The repository includes Home Assistant test stubs under `tests/stubs/` to make running unit tests easier.

---

## Reporting issues & Contributing 🤝

Found a bug or want a feature? Please open an issue or a PR at: https://github.com/czapeczek/ha_opencarwings

Contributions, fixes and improvements are welcome!

---

## Thank you 🙏

A big thank you to the OpenCARWINGS project for providing the reverse-engineered API that makes this integration possible: https://github.com/developerfromjokela/opencarwings

