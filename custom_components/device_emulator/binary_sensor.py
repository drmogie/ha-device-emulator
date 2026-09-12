"""Emulated binary_sensor platform.

The state is toggled on demand via the
`device_emulator.set_binary_sensor_state` service, useful for testing
automations that react to things like simulated motion or door contact.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_STATE,
    CONF_DEVICE_CLASS,
    CONF_DEVICE_TYPE,
    CONF_INITIAL_STATE,
    DEVICE_TYPE_BINARY_SENSOR,
    DOMAIN,
    MANUFACTURER,
    SERVICE_SET_BINARY_SENSOR_STATE,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the emulated binary_sensor from a config entry."""
    if entry.data.get(CONF_DEVICE_TYPE) != DEVICE_TYPE_BINARY_SENSOR:
        return

    async_add_entities([EmulatedBinarySensor(entry)])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_BINARY_SENSOR_STATE,
        {vol.Required(ATTR_STATE): bool},
        "async_set_state",
    )


class EmulatedBinarySensor(BinarySensorEntity):
    """A fake binary sensor with a manually-set state."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_binary_sensor"
        self._attr_name = None

        device_class = entry.data.get(CONF_DEVICE_CLASS)
        if device_class:
            self._attr_device_class = device_class

        self._attr_is_on = bool(entry.data.get(CONF_INITIAL_STATE, False))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data["name"],
            manufacturer=MANUFACTURER,
            model="Virtual Binary Sensor",
        )

    async def async_set_state(self, state: bool) -> None:
        """Handle the set_binary_sensor_state service call."""
        self._attr_is_on = state
        self.async_write_ha_state()
