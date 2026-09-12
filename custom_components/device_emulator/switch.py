"""Emulated switch platform."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEVICE_TYPE,
    CONF_INITIAL_STATE,
    DEVICE_TYPE_SWITCH,
    DOMAIN,
    MANUFACTURER,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the emulated switch from a config entry."""
    if entry.data.get(CONF_DEVICE_TYPE) != DEVICE_TYPE_SWITCH:
        return
    async_add_entities([EmulatedSwitch(entry)])


class EmulatedSwitch(SwitchEntity):
    """A fake switch with no real hardware behind it."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_switch"
        self._attr_name = None
        self._attr_is_on = bool(entry.data.get(CONF_INITIAL_STATE, False))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data["name"],
            manufacturer=MANUFACTURER,
            model="Virtual Switch",
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
