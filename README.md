# Device Emulator

A UI-driven Home Assistant integration that creates simulated devices for
testing dashboards and automations without real hardware. Every device type
maps to a real HA domain, has a "Simulated status" control to force
Unavailable/Unknown for testing, and comes with whatever hidden controls it
needs to actually emulate its behavior - no YAML, nothing to touch after
setup.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=drmogie&repository=ha-device-emulator&category=integration)

1. In HACS, go to **Integrations** > menu (top right) > **Custom repositories**.
2. Add this repository URL, category **Integration**.
3. Install **Device Emulator** and restart Home Assistant.

### Manual

[![Open your Home Assistant instance and show your dashboard resources.](https://my.home-assistant.io/badges/lovelace_resources.svg)](https://my.home-assistant.io/redirect/lovelace_resources/)

1. Copy `custom_components/device_emulator` into your HA config's
   `custom_components` directory, so you end up with:
   `config/custom_components/device_emulator/manifest.json`
2. Restart Home Assistant.

### Adding a device

1. Go to **Settings → Devices & services → Add integration**, search for
   **Device Emulator**. Its icon (built from the logo you provided) should
   show up automatically - Home Assistant 2026.3+ reads brand images
   straight out of the integration's own `brand/` folder.
2. Pick a domain, then (if it has more than one real device class) pick
   what to **show it as**, and (Camera/Image only) give an image source.
   Next, **"Add to a device?"** - create it as its own new device, or add
   it onto an existing one (see below). If creating new, name it - the
   field is pre-filled with something like "Blind Emulator" or "Battery
   Emulator" based on what you picked, so you can usually just hit Submit.
3. Repeat for every device you want.

## Building (and un-building) a composed device

There are two ways to add an entity onto an existing device instead of
creating a new one - both end up doing exactly the same thing (adding a
component to that device's own config entry, not creating anything new):

- From **Settings → Add integration → Device Emulator**, pick a domain,
  then at the **"Add to a device?"** step choose an existing device
  instead of "Create a new device."
- From that device's own **Configure** option (Settings → Devices &
  services → Device Emulator → the device → Configure → "Add an entity").

Either path is how you build something like a "Temperature/Humidity"
device: create a Temperature sensor as its own device, then add a
Humidity sensor and a Battery sensor onto it, each landing on that same
device page - not three separate integration entries.

To remove one again, use **Configure → "Remove an entity"** and pick it
from the list. Anything that was only ever created alongside it - a
battery sensor's hidden Charging switch, Charging binary_sensor, and
Replace battery button, or an outlet's power sensor - is removed with it,
since none of those exist independently of the component they belong to.

Every entity added this way gets the show-as label folded into its own
name (e.g. "Temperature", "Humidity Value") so a composed device with
several similar entities stays distinguishable, and they all share the
one "Simulated status" control below - adding more entities never adds
more status controls.

## Importing a composed device from YAML

Building a device with a lot of entities one at a time gets slow, so
there's a second way in: paste a `name:` plus a `components:` list and
every entity in it is created together, in one step.

- **Add integration → Device Emulator** now asks "Pick one domain" (the
  wizard above, unchanged) or **"Import a composed device from YAML"** -
  the second option creates a whole new device from what you paste.
- Any existing device's **Configure** option has a matching **"Import
  entities from YAML"** choice next to Add/Remove, for adding several
  entities onto that *same* device at once (no `name:` needed there).

Each item in `components:` takes the same fields the wizard itself would
ask for - `device_type` (any domain from the table below), and
`show_as` / `image_source` / `options` for the domains that need one
(left out, they default the same way the wizard's own defaults do - the
first "show as" choice, `Option 1, Option 2, Option 3` for Select).
Invalid YAML, an unknown `device_type`, a `show_as` that domain doesn't
have, or a missing required field is rejected right on the form with a
specific reason - nothing partially imports.

```yaml
name: My Composed Device
components:
  - device_type: binary_sensor
    show_as: motion
  - device_type: sensor
    show_as: temperature
  - device_type: select
    options: "Low, Medium, High"
```

A larger, real-world example - a fake stand-in for a multi-sensor
presence device (PIR, mmWave, occupancy, temperature/humidity/
illuminance, status LEDs, a firmware update entity, and its config
numbers/selects) for testing dashboards without needing that hardware
on hand:

```yaml
name: Basement Bathroom EPO (Fake)
components:
  - device_type: binary_sensor
    show_as: motion       # PIR
  - device_type: binary_sensor
    show_as: occupancy    # Occupancy
  - device_type: binary_sensor
    show_as: presence     # mmWave
  - device_type: light    # ESP32 status LED
  - device_type: light    # mmWave LED
  - device_type: sensor
    show_as: temperature
  - device_type: sensor
    show_as: illuminance
  - device_type: sensor
    show_as: humidity
  - device_type: switch   # mmWave sensor enable
  - device_type: button   # Safe mode
  - device_type: button   # Restart
  - device_type: update   # Firmware update
  - device_type: select
    options: "Disabled, Enabled"   # Bluetooth Proxy
  - device_type: select
    options: "Disabled, Enabled"   # CO2 Sensor
  - device_type: number   # Occupancy off latency
  - device_type: number   # PIR off latency
  - device_type: number   # PIR on latency
  - device_type: number   # Temperature offset
  - device_type: number   # Humidity offset
  - device_type: number   # Illuminance offset
  - device_type: number   # mmWave distance
  - device_type: number   # mmWave off latency
  - device_type: number   # mmWave on latency
  - device_type: number   # mmWave sensitivity
```

Two things worth knowing: every `number` here is the same generic
0-100 settable value (Device Emulator doesn't model each real device's
actual min/max/unit), and two identically-typed components with no
`show_as` to tell them apart (like the two `light` entries above) get
the same generic label - fine for exercising a dashboard/automation,
but they won't carry a real device's exact ranges or per-entity names.

## Every device gets a "Simulated status" control

Every device, regardless of domain, gets a hidden **Simulated status**
dropdown: **Normal**, **Unavailable**, or **Unknown** - Home Assistant's two
real special states. It's built by hooking `available`/`state` at the base
Entity level rather than per-domain, so it works identically everywhere,
and it covers every entity on the device no matter how many you've added
via Configure. This control (and every other hidden control) is never
itself affected by the override, so you can always click back to Normal.

## Domains

| Domain | Show as | Entities | Notes |
|---|---|---|---|
| `climate` | - | `climate`, `number` | Heat/cool/heat-cool/fan-only, presets, fan speed. Current temperature drifts toward target automatically, or set it directly with the hidden "Current temperature" number. |
| `switch` | Switch, Outlet | `switch` (+`sensor` if Outlet) | Outlet adds a Power sensor with realistic small fluctuation around a settable base wattage. |
| `light` | - | `light` | Brightness, color temperature, and full RGB color all at once. |
| `fan` | - | `fan` | Percentage-only (0% = off), plus oscillation, direction, and presets. |
| `cover` | 10 device classes | `cover` | Each with real travel time (2-18s) and animated open/close; blinds/shutters get tilt. |
| `lock` | - | `lock` | Lock/unlock. |
| `binary_sensor` | 18 device classes | `binary_sensor` + hidden `switch` | Flip the hidden "Simulate ..." switch to trip it. Momentary classes (motion, occupancy, presence, sound, vibration) auto-clear after ~30s. |
| **`sensor`** | 12 device classes | `sensor` + hidden `number` (+`binary_sensor`, `switch`, `button` if Battery) | A generic settable sensor - temperature, humidity, illuminance, pressure, CO2, PM2.5, voltage, current, power, energy, battery, signal strength. Set it with the hidden "Value" number and it holds until changed - **except Battery**, which also drains/charges on its own: a hidden "Charging" switch (paired with a real "Charging" binary_sensor) starts it climbing toward 100% and auto-stops there, and a "Replace battery" button resets it to 100% instantly. The Value slider tracks the live number the whole time. |
| `vacuum` | - | `vacuum`, `sensor`, `number` | Start/pause/stop/return/locate, 4 fan speeds. Battery drains while cleaning, auto-returns when low, recharges docked - the hidden "Battery level" number tracks that live and can also set it directly. |
| `lawn_mower` | - | `lawn_mower`, `sensor`, `number` | Same shape as the vacuum: mow/pause/dock, battery drain/recharge/manual override, live-tracked slider. |
| `water_heater` | - | `water_heater`, `number` | Eco/electric/gas/heat-pump/high-demand modes, away mode, tank temp drifts toward target or set directly. |
| `humidifier` | Humidifier, Dehumidifier | `humidifier`, `number` | Target humidity, 5 modes, current humidity drifts toward target/ambient or set directly. |
| `media_player` | Speaker, TV, Receiver | `media_player` | Matching source list per type; play/pause/next/previous cycle a small built-in playlist with real position ticking. |
| `alarm_control_panel` | - | `alarm_control_panel` + hidden `switch` | Arm home/away/night/vacation/custom-bypass with exit delay. Hidden "Simulate breach" switch trips an entry-delay countdown to Triggered. |
| `siren` | - | `siren` | Tones, volume, auto-off duration. |
| `valve` | Water, Gas | `valve` | Animated open/close/set-position (~5s). |
| `button` | - | `event` + 3× `button` | The event entity reports single/double/long press; the three buttons each trigger one press type, since a real click has no way to tell them apart on its own. |
| `update` | - | `update` + hidden `button` | Firmware (`UpdateDeviceClass.FIRMWARE`) if this device has other entities alongside the update, software (no device_class) if it's the only thing on the device. Versions use a `YYYY.MM.DD.N` format - a calendar date plus a plain counter that increments each time you press "Simulate new update" that day, resetting to 1 on the next. Real incremental install progress (0-100%). |
| `weather` | - | `weather` + `select` | Conditions cycle every 15 min. "Weather condition" dropdown forces one of all 15 real HA conditions, or pick "Auto (cycling)" to resume. |
| `camera` | - | `camera` | Serves a URL or local `/local/` image as both the live view and the snapshot (no real stream - HA polls the same still image to fake it). |
| `image` | - | `image` + hidden `button` | Same source options as camera, but fetched once and held static until the hidden "Refresh image" button is pressed. |
| `device_tracker` | - | `device_tracker`, `select`, hidden `button` | "Zone" dropdown is populated from the zones actually defined in your Home Assistant (gathered on startup/creation, or on demand via the hidden "Refresh zones" button) - pick one, or "Not Home". |
| `air_quality` | - | `air_quality`, `number` | Legacy domain, still functional. Reports PM2.5, set directly with the hidden number. |
| `text` | - | `text` | A settable free-text value (up to 255 characters) - holds whatever you last typed into it. |
| `number` | - | `number` | A settable numeric value (0-100, step 1) - holds whatever you last set it to. |
| `select` | - | `select` | A settable dropdown. You choose its options (comma-separated) when adding it. |
| `date` | - | `date` | A settable date, defaulting to today. |
| `time` | - | `time` | A settable time of day, defaulting to now. |
| `datetime` | - | `datetime` | A settable date + time, defaulting to now. |

Image sources: type a full URL, or a filename relative to your `www` folder
(served at `/local/`) - e.g. `porch.jpg` for `config/www/porch.jpg`.

Select options: enter the choices separated by commas, e.g.
`Low, Medium, High` - the first one becomes the initial value.

## Uninstalling

Remove each device from **Settings → Devices & services → Device Emulator**,
then delete the `custom_components/device_emulator` folder and restart.

## Versioning

Releases are tagged `YYYY.MM.DD.##` (e.g. `2026.09.19.01`).

## License

MIT - see [LICENSE](LICENSE).
