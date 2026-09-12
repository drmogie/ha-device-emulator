"""Constants for the Device Emulator integration."""

DOMAIN = "device_emulator"

CONF_DEVICE_TYPE = "device_type"
CONF_DEVICE_CLASS = "device_class"
CONF_UNIT_OF_MEASUREMENT = "unit_of_measurement"
CONF_INITIAL_STATE = "initial_state"
CONF_INITIAL_VALUE = "initial_value"

DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_SWITCH = "switch"
DEVICE_TYPE_SENSOR = "sensor"
DEVICE_TYPE_BINARY_SENSOR = "binary_sensor"

DEVICE_TYPES = [
    DEVICE_TYPE_LIGHT,
    DEVICE_TYPE_SWITCH,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_BINARY_SENSOR,
]

# Maps each supported device type to the HA platform(s) it forwards to.
# Adding a new domain later just means adding an entry here plus a
# <domain>.py platform file - the config flow and __init__ already loop
# over DEVICE_TYPES generically.
PLATFORMS_BY_TYPE = {
    DEVICE_TYPE_LIGHT: ["light"],
    DEVICE_TYPE_SWITCH: ["switch"],
    DEVICE_TYPE_SENSOR: ["sensor"],
    DEVICE_TYPE_BINARY_SENSOR: ["binary_sensor"],
}

MANUFACTURER = "Device Emulator"

SERVICE_SET_SENSOR_VALUE = "set_sensor_value"
SERVICE_SET_BINARY_SENSOR_STATE = "set_binary_sensor_state"

ATTR_VALUE = "value"
ATTR_STATE = "state"
