# Changelog

All notable changes to Device Emulator are documented here, newest first.

## 5.2.2

### Fixed
- Weather forecasts (`async_forecast_daily`/`async_forecast_hourly`) ignored
  the "Weather condition" override entirely, always showing auto-cycled
  conditions even while the current condition correctly showed the
  override - forecast tiles on a weather card no longer contradict the
  condition you set.
- The weather override didn't reliably survive a restart. It depended on
  the companion select restoring its own value and pushing it over to the
  weather entity - but weather and select are separate platforms set up
  concurrently with no guaranteed order, so the push was silently lost
  whenever weather finished setting up after the select did. The weather
  entity now restores its own override directly, independent of the
  select's timing.

## 5.2.1

### Fixed
- Added the missing `clear-night` condition to the weather "Weather
  condition" dropdown - all 15 real Home Assistant conditions are now
  selectable.

## 5.2.0

### Added
- **Remove an entity** - a device's "Configure" option now offers Add or
  Remove. Removing an entity also removes everything created alongside
  it (a battery sensor's Charging switch, Charging binary_sensor, and
  Replace battery button; an outlet's power sensor; etc.), since every
  entity for a component shares that component's id as its unique_id
  prefix.

### Removed
- **Empty Device** - since any domain can now be created directly and
  added to later, a dedicated "start with nothing" container no longer
  pulled its weight. A device can still end up with zero entities (if
  you remove everything from it) and is handled the same way as before.

### Fixed
- A real crash when adding a component that needed new platforms (e.g.
  adding a Battery sensor, which pulls in `binary_sensor`, `switch`, and
  `button`) to an existing device. `async_unload_entry` recomputed which
  platforms to unload from `entry.data` - but by the time a reload tears
  down the old setup, `entry.data` already reflects the *new* component
  list, so it tried to unload platforms that were never actually
  forwarded in the original setup. Fixed by recording exactly which
  platforms were forwarded at setup time and unloading precisely those.

## 5.1.0

### Added
- The main "Add integration" flow now has an **"Add to a device?"** step
  for every domain, not just each device's own "Configure" option -
  choose an existing device and it's added as a new component there
  (via `ConfigFlow.async_update_reload_and_abort`), instead of creating a
  new entry.

## 5.0.0

### Changed
- **Major architecture change: composed devices.** A device (config
  entry) now holds a list of components instead of exactly one fixed
  type. Adding an entity via a device's **Configure** option appends a
  component to that same entry and reloads it - no new config entry, no
  clutter in the integrations list.
- Removed the old cross-entry "attach" mechanism entirely (see 4.1.0) in
  favor of this - it's no longer needed once components live inside one
  entry to begin with.
- One **"Simulated status"** control now genuinely covers every entity on
  a composed device, since the override system was already keyed by
  entry id - this fell out of the new architecture for free.
- Every entity's name folds in its show-as label (e.g. "Temperature",
  "Temperature Value") so a composed device with several similar
  entities stays distinguishable.
- Sibling-entity lookups (a switch finding its power sensor, a battery
  sensor finding its charging switch, etc.) are now keyed per-component
  rather than per-device, so two components needing the same kind of
  helper entity on one composed device never cross-wire.

## 4.1.0

### Fixed
- The 4.0.0 "attach to a device" feature didn't actually attach anything.
  It relied on two different config entries sharing the same
  `DeviceInfo.identifiers` to merge onto one device - which no longer
  works in current Home Assistant; identifier matching is scoped to the
  registering config entry only. Rebuilt using the entity registry's own
  `device_id` field instead - the same mechanism behind the "select a
  device" dropdown on a template helper - which was later replaced
  entirely by the 5.0.0 architecture change.

## 4.0.0

### Added
- **Compose a device from multiple entities**: an **Empty Device** type
  creates a bare container; an **"Attach to a device?"** step lets any
  new entity join an existing device instead of creating its own.
- **Battery show-as gets real charging behavior**: a hidden "Charging"
  switch, a paired real "Charging" `binary_sensor` (device_class
  `battery_charging`), and a "Replace battery" button that resets to
  100%. The battery value drains while not charging and climbs toward
  100% (auto-stopping there) while charging.
- Fixed the vacuum/lawn mower "Battery level" number control never
  tracking the entity's own automatic drain/charge - it now polls and
  stays live instead of going stale after being set once.
- **Update domain**: `UpdateDeviceClass.FIRMWARE` when attached to
  another device, no device_class (representing software) when
  standalone. Versions switched to a `YYYY.MM.DD.HHMMSS` timestamp
  format (later simplified in this same version's follow-up work to
  `YYYY.MM.DD.N`, a date plus a plain daily counter).

## 3.0.0

### Changed
- **Renamed the project from "Fake Devices" to "Device Emulator"**,
  including the integration domain, folder, and all branding.
- Device type names now use only real Home Assistant domain names (e.g.
  "Binary Sensor" instead of "Sensor (motion, door, smoke, etc.)"), with
  a **"Show as"** step for domains covering multiple device classes
  (Switch → Outlet, Cover → 10 classes, etc.).
- The suggested device name is now generated dynamically from the domain
  and "show as" choice (e.g. "Blind Emulator", "Outlet Emulator")
  instead of a generic default.
- Added the integration's logo/icon, served locally via Home Assistant
  2026.3's new custom-integration `brand/` folder support.

### Added
- New domains: **Lawn Mower**, **Camera** (live/still image from a URL or
  local `/local/` path), **Image** (same sources, fetched once, manual
  refresh), **Device Tracker** (zone picker gathered from your actual
  `zone.*` entities, refreshable on demand), **Air Quality** (legacy but
  still functional).
- **Button** domain redesigned around the `event` domain: reports
  single/double/long press via three separate trigger buttons, since a
  single physical press has no way to distinguish click patterns on its
  own.

## 2.2.0

### Added
- Every device gets a **"Simulated status"** control (Normal /
  Unavailable / Unknown) - built by overriding `available`/`state` at
  the base Entity level rather than per-domain, so it works identically
  across every domain without special-casing.
- A hidden "Battery level" number control for the vacuum, so you can set
  the percentage directly instead of waiting for the drain simulation.

## 2.1.0

### Fixed
- The vacuum platform referenced `VacuumEntityFeature.BATTERY`, which no
  longer exists in current Home Assistant - battery reporting moved to a
  dedicated sensor entity - and was missing the now-required `STATE`
  feature flag.
- The water heater platform imported `STATE_ECO`/`STATE_ELECTRIC`/etc.
  from the wrong module (`homeassistant.const` instead of
  `homeassistant.components.water_heater`), which threw an `ImportError`
  the moment the platform loaded.

### Added
- A hidden "Simulate new update" button so the update entity's
  "available" flow can be re-tested repeatedly without restarting HA.
- A "Weather condition" dropdown to force a specific condition, with an
  "Auto (cycling)" option to hand control back to the simulation.

## 2.0.0

### Added
- Major domain expansion: **Vacuum**, **Water Heater**, **Humidifier**,
  **Media Player**, **Alarm Control Panel**, **Siren**, **Valve**,
  **Button**, **Update**, and **Weather**.
- Realistic cover movement: each cover type gets its own travel time
  (2-18s) and animates through opening/closing instead of jumping
  straight to the requested position; blinds and shutters also get tilt.
- Fan controls unified around percentage: `turn_on`/`turn_off` just move
  the percentage, so there's no separate toggle that can desync from the
  slider (0% is off).
- Light supports brightness, color temperature, and full RGB color at
  once.

## 1.0.0

### Added
- Initial release (as "Fake Devices"): Thermostat, Switch, Smart Plug,
  Light, and Fan, each with realistic simulated behavior (temperature
  drift, simulated power draw, etc.) instead of static values, for
  testing dashboards and automations without real hardware.
