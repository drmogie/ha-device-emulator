# Changelog

All notable changes to Device Emulator are documented here, newest first.

## 5.5.1

### Added
- Both "Import from YAML" forms (the main Add-integration flow's "Import
  a composed device from YAML", and any device's "Import entities from
  YAML") now also accept a `.yaml`/`.yml` **file** - drag one onto the
  form or click to browse for one - alongside the original paste-a-block
  text box. Either one works on its own; if you fill in both, the chosen
  file wins. Needs the built-in `file_upload` integration, which Home
  Assistant now sets up automatically as this integration's dependency.

## 5.5.0

### Added
- **YAML import can now name and configure individual entities**, so a
  composed device can carry a real device's exact names and value
  ranges instead of generic labels and one-size-fits-all values:
  - Every item in `components:` accepts an optional **`name:`** that
    overrides its default label - the fix that lets two entities of
    the same type on one device (two `light`s, two `number`s, ...)
    stay distinguishable instead of colliding on an identical generic
    name, and lets a composed device use the real device's own entity
    names (e.g. "PIR" instead of "Motion").
  - **Number**, **Text**, **Select**, **Date**, **Time**, and
    **Date & Time** now accept the same config fields their matching
    Home Assistant Helper does: `unit`/`min`/`max`/`step`/`mode` for
    Number, `min`/`max`/`pattern`/`mode` for Text, and an `initial`
    starting value for any of the six. Left out, every field falls
    back exactly the way it always has (no unit, 0-100 step-1 number,
    today/now for date/time/datetime, first option for Select) - none
    of this is required.
  - Same validation approach as the rest of YAML import: bad values
    (min without max, an out-of-range initial, an invalid regex
    pattern, a mode that isn't one of the real options, ...) are
    rejected right on the form with a specific reason, and fields that
    don't apply to a component's `device_type` are simply ignored
    rather than rejected.
  - README's worked "Basement Bathroom EPO (Fake)" example now uses
    real per-entity names and real number ranges/units/starting values
    pulled from an actual Everything Presence One, instead of generic
    placeholders - directly resolving the caveat the old example used
    to carry about not being able to match a real device closely.

## 5.4.0

### Added
- **Import a whole composed device from YAML**, in both places you'd
  normally build one entity at a time:
  - **Add integration → Device Emulator** now opens with a choice
    between "Pick one domain" (the existing wizard, unchanged) and
    "Import a composed device from YAML" - paste a `name:` plus a
    `components:` list and every entity in it is created together, as
    one new device, in a single step.
  - Any existing device's **Configure** option gets a matching "Import
    entities from YAML" choice alongside Add/Remove, for adding several
    entities onto that SAME device at once (no `name:` needed there -
    the device already has one).
  - Each list item takes the same fields the wizard would ask for -
    `device_type` (a domain this integration supports), and
    `show_as` / `image_source` / `options` for the domains that need
    one (defaults apply the same way the wizard's own defaults do if
    left out). Bad YAML, an unknown `device_type`, an invalid
    `show_as`, or a missing required field is rejected with a specific
    reason shown right on the form - nothing partially imports.
  - This doesn't change what a composed device IS (still one config
    entry with a list of components) or how existing devices behave -
    it's a second way to populate that same list, for when you're
    recreating something with a lot of entities (a real multi-sensor
    device you want a fake stand-in for, say) rather than always
    clicking through one entity at a time.

## 5.3.0

### Added
- Six new standalone domains, matching the value-holding domains behind
  Home Assistant's own "Helpers" (input_text/input_number/input_select/
  input_datetime): **Text** (a settable string), **Number** (a settable
  0-100 value), **Select** (a settable dropdown - you choose its
  comma-separated options when adding it, via a new "Options" config
  flow step), **Date**, **Time**, and **Date & Time** (each defaulting
  to today/now). All six are simple settable values that hold whatever
  you last set them to, restore across restarts, and respect the
  device's "Simulated status" control like every other domain.
- Considered but not added: `counter`, `timer`, and `schedule`. Unlike
  every domain above, these are self-contained Home Assistant helper
  integrations with no public Entity base class for a third-party
  integration to subclass - there's no `counter.py`/`timer.py`/
  `schedule.py` platform file this integration (or any custom
  integration) could add to make Home Assistant treat them as
  emulated devices, the way it does for every other domain in this
  list.

## 5.2.3

### Fixed
- The weather condition override could still get silently lost (falling
  back to auto-cycling, and "sunny" specifically since it's first in the
  cycle) or fail to show up immediately when changed. The root cause:
  the override was kept as two independently-restored copies of the
  same value - one on the "Weather condition" select, one on the
  weather entity itself (added in 5.2.2) - with no guaranteed order
  between their restores, so they could disagree or one could
  overwrite the other with a stale value. The override now lives in
  exactly one place (owned by the select), which the weather entity
  reads live on every state and forecast computation instead of
  keeping its own copy - so changing the select is reflected
  immediately and there's nothing left to fall out of sync after a
  restart.

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
