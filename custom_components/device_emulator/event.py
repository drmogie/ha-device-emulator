"""Fake event platform - one entity per Button component.

One event entity reports single/double/long press events, triggered by
three companion buttons (see button.py). A real momentary button press
has no way to distinguish click patterns on its own - you need three
separate actions to simulate them, so pressing each one calls trigger()
with the matching event type.
"""
from __future__ import annotations

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import Component, DEVICE_TYPE_BUTTON, components_for, device_info_for
from .helpers import set_entity
from .mixins import FakeEntityMixin

EVENT_TYPES = ["single_press", "double_press", "long_press"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake button-press event entity for each Button component."""
    async_add_entities(
        FakeButtonEvent(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_BUTTON
    )


class FakeButtonEvent(FakeEntityMixin, EventEntity):
    """Reports single/double/long press events, triggered by companion buttons.

    EventEntity already extends RestoreEntity internally, so the last
    press type and timestamp survive a restart with no extra code here.
    """

    _attr_has_entity_name = True
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = EVENT_TYPES

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_event"
        self._attr_device_info = device_info_for(component.entry)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        set_entity(self.hass, self._component.id, "event_entity", self)

    @callback
    def trigger(self, event_type: str) -> None:
        """Called by the matching companion button (see button.py)."""
        self._trigger_event(event_type)
        self.async_write_ha_state()
