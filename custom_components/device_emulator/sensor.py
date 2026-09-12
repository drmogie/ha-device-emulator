"""Emulated sensor platform.

Since a virtual sensor has no real hardware feeding it, its value is set on
demand via the `device_emulator.set_sensor_value` service (Developer Tools >
Actions), which is handy for testing automations that react to sensor state.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_VALUE,
    CONF_DEVICE_CLASS,
    CONF_DEVICE_TYPE,
    CONF_INITIAL_VALUE,
    CONF_UNIT_OF_MEASUREMENT,
    DEVICE_TYPE_SENSOR,
    DOMAIN,
    MANUFACTURER,
    SERVICE_SET_SENSOR_VALUE,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the emulated sensor from a config entry."""
    if entry.data.get(CONF_DEVICE_TYPE) != DEVICE_TYPE_SENSOR:
        return

    async_add_entities([EmulatedSensor(entry)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_SENSOR_VALUE,
        {vol.Required(ATTR_VALUE): str},
        "async_set_value",
    )


class EmulatedSensor(SensorEntity):
    """A fake sensor with a manually-set value."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sensor"
        self._attr_name = None

        device_class = entry.data.get(CONF_DEVICE_CLASS)
        if device_class:
            self._attr_device_class = device_class

        unit = entry.data.get(CONF_UNIT_OF_MEASUREMENT)
        if unit:
            self._attr_native_unit_of_measurement = unit

        self._attr_native_value = self._coerce(
            entry.data.get(CONF_INITIAL_VALUE, "0")
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data["name"],
            manufacturer=MANUFACTURER,
            model="Virtual Sensor",
        )

    @staticmethod
    def _coerce(value: str):
        try:
            return float(value)
        except (TypeError, ValueError):
            return value

    async def async_set_value(self, value: str) -> None:
        """Handle the set_sensor_value service call."""
        self._attr_native_value = self._coerce(value)
        self.async_write_ha_state()
