# Device Emulator

A Home Assistant custom integration that creates virtual/fake devices with
no real hardware behind them, so you can test dashboards, cards, and
automations without needing the physical device.

Every emulated device is added and configured entirely through the UI -
**Settings > Devices & Services > Add Integration > Device Emulator** - no
YAML required.

## Currently supported device types

- **Light** - on/off + brightness
- **Switch** - on/off
- **Sensor** - a numeric or text value you set on demand
- **Binary sensor** - an on/off state you set on demand (e.g. simulated motion, door contact)

Each config entry is one emulated device, so add the integration again for
each additional fake device you want. The integration is structured so more
device types (cover, climate, fan, lock, etc.) can be added later without
changing how existing devices work - see [Extending](#extending) below.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=drmogie&repository=ha-device-emulator&category=integration)

1. In HACS, go to **Integrations** > menu (top right) > **Custom repositories**.
2. Add this repository URL, category **Integration**.
3. Install **Device Emulator** and restart Home Assistant.

### Manual

[![Open your Home Assistant instance and show your dashboard resources.](https://my.home-assistant.io/badges/lovelace_resources.svg)](https://my.home-assistant.io/redirect/lovelace_resources/)

1. Copy `custom_components/device_emulator/` into your Home Assistant `config/custom_components/` folder.
2. Restart Home Assistant.

## Adding an emulated device

1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for **Device Emulator**.
3. Pick a name and a device type.
4. Fill in the options for that type (device class / unit / initial value or state).

## Setting sensor and binary sensor values

Since these have no real hardware to report a value, use these actions from
**Developer Tools > Actions** (or in an automation) to change them:

- `device_emulator.set_sensor_value` - target a sensor entity, pass a `value`.
- `device_emulator.set_binary_sensor_state` - target a binary sensor entity, pass a `state` (`true`/`false`).

## Extending

Adding a new device type (e.g. `cover`) means:

1. Add the type to `DEVICE_TYPES` / `PLATFORMS_BY_TYPE` in `const.py`.
2. Add a `configure` schema branch for it in `config_flow.py`.
3. Add a `cover.py` platform file following the pattern in `light.py` / `switch.py`.

The `__init__.py` setup/unload logic and the config flow's first step
already work generically across every type in `DEVICE_TYPES`.

## Versioning

Releases are tagged `YYYY.MM.DD.#` (e.g. `2026.09.12.1`).

## License

MIT - see [LICENSE](LICENSE).
