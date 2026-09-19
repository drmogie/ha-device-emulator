"""Constants for the Device Emulator integration."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import yaml

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

DOMAIN = "device_emulator"

# Per-component config keys, used inside each dict in entry.data[CONF_COMPONENTS].
CONF_COMPONENT_ID = "id"
CONF_DEVICE_TYPE = "device_type"
CONF_SHOW_AS = "show_as"
CONF_IMAGE_SOURCE = "image_source"
CONF_OPTIONS = "options"

# Transient config-flow field for the "Import from YAML" form - never stored
# on the entry itself, just parsed into component dicts by
# parse_components_yaml() below.
CONF_YAML = "yaml"

# Entry-level config key: entry.data[CONF_COMPONENTS] is a list of component
# dicts. The first is created by the initial "Add integration" flow; more
# can be added afterward through the device's "Configure" (options) flow -
# that's how you build a composed device (e.g. a Temperature sensor, a
# Humidity sensor, and a Battery sensor all living on one device), without
# each one becoming its own separate config entry.
CONF_COMPONENTS = "components"

MANUFACTURER = "Device Emulator"

# --- Top-level device types -------------------------------------------------
# Every value here is a real Home Assistant domain name. The dropdown label
# is that domain, Title Cased - no invented product names. Where a domain
# covers several real device classes (a switch can be an outlet, a cover can
# be a blind or a garage door, ...), a second "Show as" step picks one.
DEVICE_TYPE_SWITCH = "switch"
DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_FAN = "fan"
DEVICE_TYPE_COVER = "cover"
DEVICE_TYPE_LOCK = "lock"
DEVICE_TYPE_BINARY_SENSOR = "binary_sensor"
DEVICE_TYPE_SENSOR = "sensor"
DEVICE_TYPE_CLIMATE = "climate"
DEVICE_TYPE_VACUUM = "vacuum"
DEVICE_TYPE_LAWN_MOWER = "lawn_mower"
DEVICE_TYPE_WATER_HEATER = "water_heater"
DEVICE_TYPE_HUMIDIFIER = "humidifier"
DEVICE_TYPE_MEDIA_PLAYER = "media_player"
DEVICE_TYPE_ALARM = "alarm_control_panel"
DEVICE_TYPE_SIREN = "siren"
DEVICE_TYPE_VALVE = "valve"
DEVICE_TYPE_BUTTON = "button"
DEVICE_TYPE_UPDATE = "update"
DEVICE_TYPE_WEATHER = "weather"
DEVICE_TYPE_CAMERA = "camera"
DEVICE_TYPE_IMAGE = "image"
DEVICE_TYPE_DEVICE_TRACKER = "device_tracker"
DEVICE_TYPE_AIR_QUALITY = "air_quality"
DEVICE_TYPE_TEXT = "text"
DEVICE_TYPE_NUMBER = "number"
DEVICE_TYPE_SELECT = "select"
DEVICE_TYPE_DATE = "date"
DEVICE_TYPE_TIME = "time"
DEVICE_TYPE_DATETIME = "datetime"

DEVICE_TYPE_LABELS = {
    DEVICE_TYPE_SWITCH: "Switch",
    DEVICE_TYPE_LIGHT: "Light",
    DEVICE_TYPE_FAN: "Fan",
    DEVICE_TYPE_COVER: "Cover",
    DEVICE_TYPE_LOCK: "Lock",
    DEVICE_TYPE_BINARY_SENSOR: "Binary Sensor",
    DEVICE_TYPE_SENSOR: "Sensor",
    DEVICE_TYPE_CLIMATE: "Climate",
    DEVICE_TYPE_VACUUM: "Vacuum",
    DEVICE_TYPE_LAWN_MOWER: "Lawn Mower",
    DEVICE_TYPE_WATER_HEATER: "Water Heater",
    DEVICE_TYPE_HUMIDIFIER: "Humidifier",
    DEVICE_TYPE_MEDIA_PLAYER: "Media Player",
    DEVICE_TYPE_ALARM: "Alarm Control Panel",
    DEVICE_TYPE_SIREN: "Siren",
    DEVICE_TYPE_VALVE: "Valve",
    DEVICE_TYPE_BUTTON: "Button",
    DEVICE_TYPE_UPDATE: "Update",
    DEVICE_TYPE_WEATHER: "Weather",
    DEVICE_TYPE_CAMERA: "Camera",
    DEVICE_TYPE_IMAGE: "Image",
    DEVICE_TYPE_DEVICE_TRACKER: "Device Tracker",
    DEVICE_TYPE_AIR_QUALITY: "Air Quality",
    DEVICE_TYPE_TEXT: "Text",
    DEVICE_TYPE_NUMBER: "Number",
    DEVICE_TYPE_SELECT: "Select",
    DEVICE_TYPE_DATE: "Date",
    DEVICE_TYPE_TIME: "Time",
    DEVICE_TYPE_DATETIME: "Date & Time",
}

# Every domain is addable as a component via "Configure" or the main
# flow's "add to a device" step - kept as its own name since call sites
# already refer to it, even though there's no longer anything to exclude.
ADDABLE_DEVICE_TYPE_LABELS = DEVICE_TYPE_LABELS

# --- "Show as" options (the second step) ------------------------------------
# Each of these is a real device_class (or, for humidifier/media_player, a
# genuinely different capability set) within its domain.

SWITCH_SHOW_AS = [
    {"value": "switch", "label": "Switch"},
    {"value": "outlet", "label": "Outlet"},
]

COVER_SHOW_AS = [
    {"value": "awning", "label": "Awning"},
    {"value": "blind", "label": "Blind"},
    {"value": "curtain", "label": "Curtain"},
    {"value": "damper", "label": "Damper"},
    {"value": "door", "label": "Door"},
    {"value": "garage", "label": "Garage Door"},
    {"value": "gate", "label": "Gate"},
    {"value": "shade", "label": "Shade"},
    {"value": "shutter", "label": "Shutter"},
    {"value": "window", "label": "Window"},
]

# Capability + travel-time profile per cover show_as. Types without position
# support (garage/gate/door) still animate opening and closing, they just
# don't expose a stop-anywhere percentage - matching real hardware.
COVER_PROFILES = {
    "awning": {"position": True, "tilt": False, "seconds": 12},
    "blind": {"position": True, "tilt": True, "seconds": 4},
    "curtain": {"position": True, "tilt": False, "seconds": 8},
    "damper": {"position": True, "tilt": False, "seconds": 2},
    "door": {"position": False, "tilt": False, "seconds": 3},
    "garage": {"position": False, "tilt": False, "seconds": 14},
    "gate": {"position": False, "tilt": False, "seconds": 18},
    "shade": {"position": True, "tilt": False, "seconds": 5},
    "shutter": {"position": True, "tilt": True, "seconds": 8},
    "window": {"position": True, "tilt": False, "seconds": 6},
}

BINARY_SENSOR_SHOW_AS = [
    {"value": "motion", "label": "Motion"},
    {"value": "occupancy", "label": "Occupancy"},
    {"value": "presence", "label": "Presence"},
    {"value": "door", "label": "Door"},
    {"value": "garage_door", "label": "Garage Door"},
    {"value": "window", "label": "Window"},
    {"value": "opening", "label": "Opening (generic)"},
    {"value": "moisture", "label": "Moisture / Leak"},
    {"value": "smoke", "label": "Smoke"},
    {"value": "gas", "label": "Gas"},
    {"value": "safety", "label": "Safety"},
    {"value": "problem", "label": "Problem"},
    {"value": "tamper", "label": "Tamper"},
    {"value": "vibration", "label": "Vibration"},
    {"value": "sound", "label": "Sound"},
    {"value": "cold", "label": "Cold"},
    {"value": "heat", "label": "Heat"},
    {"value": "light", "label": "Light"},
]

# These clear themselves automatically after tripping, like a real PIR or
# mic-based sensor would. Everything else (door, smoke, moisture, ...) stays
# tripped until the "Simulate" switch is flipped back manually.
BINARY_SENSOR_AUTO_CLEAR = {"motion", "occupancy", "presence", "sound", "vibration"}
BINARY_SENSOR_AUTO_CLEAR_SECONDS = 30

BINARY_SENSOR_TRIGGER_LABELS = {
    "motion": "Simulate motion",
    "occupancy": "Simulate occupied",
    "presence": "Simulate present",
    "door": "Simulate open",
    "garage_door": "Simulate open",
    "window": "Simulate open",
    "opening": "Simulate open",
    "moisture": "Simulate wet",
    "smoke": "Simulate smoke",
    "gas": "Simulate gas detected",
    "safety": "Simulate unsafe",
    "problem": "Simulate problem",
    "tamper": "Simulate tamper",
    "vibration": "Simulate vibration",
    "sound": "Simulate sound",
    "cold": "Simulate cold",
    "heat": "Simulate heat",
    "light": "Simulate light detected",
}

# Generic settable sensor - device_class -> (label, unit, default, min, max, step)
SENSOR_SHOW_AS_SPECS = {
    "temperature": ("Temperature", "°F", 70.0, -20.0, 130.0, 0.5),
    "humidity": ("Humidity", "%", 45.0, 0.0, 100.0, 1.0),
    "illuminance": ("Illuminance", "lx", 200.0, 0.0, 10000.0, 10.0),
    "pressure": ("Pressure", "inHg", 29.9, 25.0, 32.0, 0.01),
    "carbon_dioxide": ("CO2", "ppm", 600.0, 0.0, 5000.0, 10.0),
    "pm25": ("PM2.5", "µg/m³", 12.0, 0.0, 500.0, 1.0),
    "voltage": ("Voltage", "V", 120.0, 0.0, 480.0, 0.5),
    "current": ("Current", "A", 2.5, 0.0, 100.0, 0.1),
    "power": ("Power", "W", 60.0, 0.0, 5000.0, 1.0),
    "energy": ("Energy", "kWh", 10.0, 0.0, 100000.0, 0.1),
    "battery": ("Battery", "%", 100.0, 0.0, 100.0, 1.0),
    "signal_strength": ("Signal Strength", "dB", -60.0, -120.0, 0.0, 1.0),
}
SENSOR_SHOW_AS = [
    {"value": key, "label": label} for key, (label, *_rest) in SENSOR_SHOW_AS_SPECS.items()
]

VALVE_SHOW_AS = [
    {"value": "water", "label": "Water"},
    {"value": "gas", "label": "Gas"},
]

HUMIDIFIER_SHOW_AS = [
    {"value": "humidifier", "label": "Humidifier"},
    {"value": "dehumidifier", "label": "Dehumidifier"},
]

MEDIA_PLAYER_SHOW_AS = [
    {"value": "speaker", "label": "Speaker"},
    {"value": "tv", "label": "TV"},
    {"value": "receiver", "label": "Receiver"},
]

# device_type -> its list of "show as" options. A device type appearing here
# gets a second config-flow step; anything not listed is created directly.
SHOW_AS_OPTIONS = {
    DEVICE_TYPE_SWITCH: SWITCH_SHOW_AS,
    DEVICE_TYPE_COVER: COVER_SHOW_AS,
    DEVICE_TYPE_BINARY_SENSOR: BINARY_SENSOR_SHOW_AS,
    DEVICE_TYPE_SENSOR: SENSOR_SHOW_AS,
    DEVICE_TYPE_VALVE: VALVE_SHOW_AS,
    DEVICE_TYPE_HUMIDIFIER: HUMIDIFIER_SHOW_AS,
    DEVICE_TYPE_MEDIA_PLAYER: MEDIA_PLAYER_SHOW_AS,
}

# Device types that need a third "image source" step (a URL or a /local/ path).
IMAGE_SOURCE_TYPES = (DEVICE_TYPE_CAMERA, DEVICE_TYPE_IMAGE)

# Device types that need an "options" step (a comma-separated list of
# choices for the standalone Select device - see FakeStandaloneSelect).
OPTIONS_ENTRY_TYPES = (DEVICE_TYPE_SELECT,)
DEFAULT_SELECT_OPTIONS = "Option 1, Option 2, Option 3"

# Sentinel option for the device_tracker zone picker, mapped to an empty
# in_zones list (device_tracker.py) rather than any real zone entity_id.
DEVICE_TRACKER_NOT_HOME_OPTION = "Not Home"

# Weather condition override options - "Auto" hands control back to the
# entity's own cycling simulation.
WEATHER_AUTO_OPTION = "Auto (cycling)"
WEATHER_CONDITION_OPTIONS = [
    WEATHER_AUTO_OPTION,
    "clear-night",
    "cloudy",
    "exceptional",
    "fog",
    "hail",
    "lightning",
    "lightning-rainy",
    "partlycloudy",
    "pouring",
    "rainy",
    "snowy",
    "snowy-rainy",
    "sunny",
    "windy",
    "windy-variant",
]

# --- Platforms per device type ----------------------------------------------
# Motion/door-style sensors and the alarm panel also get a hidden "config"
# switch used to simulate a trip/breach, since those domains have no HA
# service of their own to flip them with.
PLATFORMS_BY_TYPE = {
    DEVICE_TYPE_SWITCH: ["switch"],
    DEVICE_TYPE_LIGHT: ["light"],
    DEVICE_TYPE_FAN: ["fan"],
    DEVICE_TYPE_COVER: ["cover"],
    DEVICE_TYPE_LOCK: ["lock"],
    DEVICE_TYPE_BINARY_SENSOR: ["binary_sensor", "switch"],
    DEVICE_TYPE_SENSOR: ["sensor", "number"],
    DEVICE_TYPE_CLIMATE: ["climate", "number"],
    DEVICE_TYPE_VACUUM: ["vacuum", "sensor", "number"],
    DEVICE_TYPE_LAWN_MOWER: ["lawn_mower", "sensor", "number"],
    DEVICE_TYPE_WATER_HEATER: ["water_heater", "number"],
    DEVICE_TYPE_HUMIDIFIER: ["humidifier", "number"],
    DEVICE_TYPE_MEDIA_PLAYER: ["media_player"],
    DEVICE_TYPE_ALARM: ["alarm_control_panel", "switch"],
    DEVICE_TYPE_SIREN: ["siren"],
    DEVICE_TYPE_VALVE: ["valve"],
    DEVICE_TYPE_BUTTON: ["event", "button"],
    DEVICE_TYPE_UPDATE: ["update", "button"],
    DEVICE_TYPE_WEATHER: ["weather", "select"],
    DEVICE_TYPE_CAMERA: ["camera"],
    DEVICE_TYPE_IMAGE: ["image", "button"],
    DEVICE_TYPE_DEVICE_TRACKER: ["device_tracker", "select", "button"],
    DEVICE_TYPE_AIR_QUALITY: ["air_quality", "number"],
    DEVICE_TYPE_TEXT: ["text"],
    DEVICE_TYPE_NUMBER: ["number"],
    DEVICE_TYPE_SELECT: ["select"],
    DEVICE_TYPE_DATE: ["date"],
    DEVICE_TYPE_TIME: ["time"],
    DEVICE_TYPE_DATETIME: ["datetime"],
}

# Extra platforms needed only for specific (device_type, show_as) pairs.
EXTRA_PLATFORMS_BY_SHOW_AS = {
    (DEVICE_TYPE_SWITCH, "outlet"): ["sensor"],
    (DEVICE_TYPE_SENSOR, "battery"): ["binary_sensor", "switch", "button"],
}


@dataclass(frozen=True)
class Component:
    """One entity's worth of config within a Device Emulator entry.

    A device (config entry) can hold several of these - that's how a
    composed device (e.g. Temperature + Humidity + Battery sensors on one
    "Temperature/Humidity" device) is built. `id` is a globally unique
    string generated when the component is added (see config_flow.py),
    used both as this entity's unique_id prefix and as the key sibling
    entities use to find each other in helpers.py - so two components of
    the same device_type never cross-wire.
    """

    entry: ConfigEntry
    id: str
    device_type: str
    show_as: str | None = None
    image_source: str | None = None
    options: str | None = None

    @property
    def label(self) -> str | None:
        """The "show as" label, e.g. "Temperature" or "Garage Door", if any."""
        return show_as_label(self.device_type, self.show_as)

    @property
    def option_list(self) -> list[str]:
        """The parsed, comma-separated option list for a standalone Select.

        Falls back to DEFAULT_SELECT_OPTIONS if nothing was configured (a
        component built before this field existed, or an empty entry) so
        there's always at least one selectable option.
        """
        raw = self.options or DEFAULT_SELECT_OPTIONS
        parsed = [option.strip() for option in raw.split(",") if option.strip()]
        return parsed or [DEFAULT_SELECT_OPTIONS]


def components_for(entry: ConfigEntry) -> list[Component]:
    """Return every component configured on this entry."""
    return [
        Component(
            entry=entry,
            id=c[CONF_COMPONENT_ID],
            device_type=c[CONF_DEVICE_TYPE],
            show_as=c.get(CONF_SHOW_AS),
            image_source=c.get(CONF_IMAGE_SOURCE),
            options=c.get(CONF_OPTIONS),
        )
        for c in entry.data.get(CONF_COMPONENTS, [])
    ]


class YamlSpecError(Exception):
    """Raised when a YAML device-import spec is invalid or malformed."""


def build_component_from_spec(spec: Any) -> dict[str, Any]:
    """Validate one YAML component mapping and turn it into a stored component dict.

    Mirrors exactly what the config-flow wizard's per-step choices produce
    (see _ComponentStepsMixin / _build_component in config_flow.py) so a
    YAML-imported component behaves identically to one built by hand -
    same required show_as/image_source rules, same options default.
    """
    if not isinstance(spec, dict):
        raise YamlSpecError(f"each component must be a mapping, got: {spec!r}")

    device_type = spec.get(CONF_DEVICE_TYPE)
    if device_type not in DEVICE_TYPE_LABELS:
        valid = ", ".join(sorted(DEVICE_TYPE_LABELS))
        raise YamlSpecError(
            f"unknown device_type {device_type!r} - must be one of: {valid}"
        )

    component: dict[str, Any] = {
        CONF_COMPONENT_ID: uuid.uuid4().hex[:12],
        CONF_DEVICE_TYPE: device_type,
    }

    if device_type in SHOW_AS_OPTIONS:
        options = SHOW_AS_OPTIONS[device_type]
        valid_values = [opt["value"] for opt in options]
        show_as = spec.get(CONF_SHOW_AS, valid_values[0])
        if show_as not in valid_values:
            raise YamlSpecError(
                f"{device_type}: show_as {show_as!r} must be one of: "
                + ", ".join(valid_values)
            )
        component[CONF_SHOW_AS] = show_as

    if device_type in IMAGE_SOURCE_TYPES:
        image_source = spec.get(CONF_IMAGE_SOURCE)
        if not image_source:
            raise YamlSpecError(f"{device_type}: image_source is required")
        component[CONF_IMAGE_SOURCE] = image_source

    if device_type in OPTIONS_ENTRY_TYPES:
        component[CONF_OPTIONS] = spec.get(CONF_OPTIONS) or DEFAULT_SELECT_OPTIONS

    return component


def parse_components_yaml(raw: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse a pasted YAML block into (component dicts, optional device name).

    Expected shape::

        name: My Composed Device      # only used when creating a brand-new
        components:                   # device - ignored when importing onto
          - device_type: binary_sensor  # an existing one
            show_as: motion
          - device_type: sensor
            show_as: temperature

    Raises YamlSpecError with a human-readable reason on anything wrong -
    bad YAML syntax, the wrong top-level shape, an empty/missing
    components list, or any single component failing
    build_component_from_spec().
    """
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as err:
        raise YamlSpecError(f"invalid YAML: {err}") from err

    if not isinstance(data, dict):
        raise YamlSpecError("top-level YAML must be a mapping (name/components)")

    raw_components = data.get(CONF_COMPONENTS)
    if not isinstance(raw_components, list) or not raw_components:
        raise YamlSpecError("'components' must be a non-empty list")

    components = [build_component_from_spec(spec) for spec in raw_components]
    name = data.get("name")
    return components, (str(name).strip() if name else None)


def platforms_for_entry(entry: ConfigEntry) -> list[str]:
    """Return every platform every component of this entry needs."""
    platforms: list[str] = []
    for component in components_for(entry):
        for platform in PLATFORMS_BY_TYPE[component.device_type]:
            if platform not in platforms:
                platforms.append(platform)
        for extra in EXTRA_PLATFORMS_BY_SHOW_AS.get(
            (component.device_type, component.show_as), []
        ):
            if extra not in platforms:
                platforms.append(extra)
    if "select" not in platforms:
        # Every device gets one "Simulated status" select control, shared
        # by every component on it, even if none of them otherwise use
        # the select platform.
        platforms.append("select")
    return platforms


DEVICE_MODELS = {
    DEVICE_TYPE_SWITCH: "Switch Emulator",
    DEVICE_TYPE_LIGHT: "Light Emulator",
    DEVICE_TYPE_FAN: "Fan Emulator",
    DEVICE_TYPE_COVER: "Cover Emulator",
    DEVICE_TYPE_LOCK: "Lock Emulator",
    DEVICE_TYPE_BINARY_SENSOR: "Binary Sensor Emulator",
    DEVICE_TYPE_SENSOR: "Sensor Emulator",
    DEVICE_TYPE_CLIMATE: "Climate Emulator",
    DEVICE_TYPE_VACUUM: "Vacuum Emulator",
    DEVICE_TYPE_LAWN_MOWER: "Lawn Mower Emulator",
    DEVICE_TYPE_WATER_HEATER: "Water Heater Emulator",
    DEVICE_TYPE_HUMIDIFIER: "Humidifier Emulator",
    DEVICE_TYPE_MEDIA_PLAYER: "Media Player Emulator",
    DEVICE_TYPE_ALARM: "Alarm Control Panel Emulator",
    DEVICE_TYPE_SIREN: "Siren Emulator",
    DEVICE_TYPE_VALVE: "Valve Emulator",
    DEVICE_TYPE_BUTTON: "Button Emulator",
    DEVICE_TYPE_UPDATE: "Update Emulator",
    DEVICE_TYPE_WEATHER: "Weather Emulator",
    DEVICE_TYPE_CAMERA: "Camera Emulator",
    DEVICE_TYPE_IMAGE: "Image Emulator",
    DEVICE_TYPE_DEVICE_TRACKER: "Device Tracker Emulator",
    DEVICE_TYPE_AIR_QUALITY: "Air Quality Emulator",
    DEVICE_TYPE_TEXT: "Text Emulator",
    DEVICE_TYPE_NUMBER: "Number Emulator",
    DEVICE_TYPE_SELECT: "Select Emulator",
    DEVICE_TYPE_DATE: "Date Emulator",
    DEVICE_TYPE_TIME: "Time Emulator",
    DEVICE_TYPE_DATETIME: "Date & Time Emulator",
}

_SHOW_AS_LABEL_LOOKUPS = {
    DEVICE_TYPE_SWITCH: {v["value"]: v["label"] for v in SWITCH_SHOW_AS},
    DEVICE_TYPE_COVER: {v["value"]: v["label"] for v in COVER_SHOW_AS},
    DEVICE_TYPE_BINARY_SENSOR: {v["value"]: v["label"] for v in BINARY_SENSOR_SHOW_AS},
    DEVICE_TYPE_SENSOR: {v["value"]: v["label"] for v in SENSOR_SHOW_AS},
    DEVICE_TYPE_VALVE: {v["value"]: v["label"] for v in VALVE_SHOW_AS},
    DEVICE_TYPE_HUMIDIFIER: {v["value"]: v["label"] for v in HUMIDIFIER_SHOW_AS},
    DEVICE_TYPE_MEDIA_PLAYER: {v["value"]: v["label"] for v in MEDIA_PLAYER_SHOW_AS},
}


def show_as_label(device_type: str, show_as: str | None) -> str | None:
    """Return the human label for a (device_type, show_as) pair, if any."""
    if not show_as:
        return None
    return _SHOW_AS_LABEL_LOOKUPS.get(device_type, {}).get(show_as)


def device_model(device_type: str, show_as: str | None) -> str:
    """Return a friendly model name, taking the chosen "show as" into account."""
    label = show_as_label(device_type, show_as)
    if label:
        if device_type == DEVICE_TYPE_BINARY_SENSOR:
            return f"{label} Sensor Emulator"
        return f"{label} Emulator"
    return DEVICE_MODELS.get(device_type, "Device Emulator")


def suggested_name(device_type: str, show_as: str | None) -> str:
    """Return the default device name shown in the "Name" field.

    Mirrors device_model()'s wording so the suggested name and the
    device's model string always agree.
    """
    return device_model(device_type, show_as)


def device_info_for(entry: ConfigEntry) -> DeviceInfo:
    """Build the one shared DeviceInfo for every component on this entry.

    A config entry is one device, always - composing a device out of
    several entities (see Component above) means adding more components
    to the SAME entry, not creating new entries to attach elsewhere. The
    model shown is based on the first (primary) component; an Empty
    Device with no components yet is registered directly in __init__.py
    instead, since it has no entity to carry this.
    """
    components = entry.data.get(CONF_COMPONENTS, [])
    if components:
        primary = components[0]
        model = device_model(primary[CONF_DEVICE_TYPE], primary.get(CONF_SHOW_AS))
    else:
        model = "Empty Device"
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=model,
    )
