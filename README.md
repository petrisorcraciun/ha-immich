# Immich Home Assistant Integration

This is a custom integration for Home Assistant that allows you to monitor Immich statistics directly in Home Assistant.

![Sensors Example](sensors.png)

### HACS Installation

[![Add Integration in Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=petrisorcraciun&repository=ha-immich&category=integration)

## Custom Installation

1. **Copy** the `ha-immich` folder to your Home Assistant `custom_components` directory.
2. **Restart** Home Assistant.
3. **Add** the Immich integration from `Settings` → `Devices & Services` → `Add Integration` and search for `Immich`.
4. **Enter** your Immich server URL, API key, and scan interval.

## Requirements
- Home Assistant (core or OS)
- A running Immich server
- An API key generated from Immich ([see Immich documentation](https://immich.app/docs/features/command-line-interface/))

> **ℹ️ This integration requires no extra Python dependencies.**

## Uninstall
- Remove the integration from Home Assistant (`Settings` → `Devices & Services` → `Immich` → `Delete`).
- Delete the `custom_components/ha-immich` folder from your Home Assistant setup.
- Restart Home Assistant.

## Support
If you need help or encounter an issue, please open a ticket on GitHub.
