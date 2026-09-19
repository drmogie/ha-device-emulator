"""Fake text platform - a standalone, settable free-text value."""
from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_TEXT, components_for, device_info_for
from .mixins import FakeEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake text entity for each Text component on this device."""
    async_add_entities(
        FakeText(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_TEXT
    )


class FakeText(FakeEntityMixin, TextEntity, RestoreEntity):
    """A simulated free-text value - holds whatever you last set it to."""

    _attr_has_entity_name = True
    _attr_native_max = 255

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_text"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_value = "Hello"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in (None, "unknown", "unavailable"):
                self._attr_native_value = last_state.state

    async def async_set_value(self, value: str) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
