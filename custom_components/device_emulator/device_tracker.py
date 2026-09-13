"""Fake device_tracker platform - one entity per Device Tracker component.

Uses `_attr_in_zones` rather than fake GPS coordinates - it's the
modern, direct way to say "this device is in this zone" without doing
distance math against latitude/longitude (and `_attr_location_name` is
deprecated). The zone itself is picked from a companion select entity
(see select.py's FakeZoneSelect) populated by scanning the zones
actually defined in this Home Assistant instance.
"""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_DEVICE_TRACKER, components_for, device_info_for
from .helpers import set_entity
from .mixins import FakeEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake device tracker for each Device Tracker component."""
    async_add_entities(
        FakeDeviceTracker(c)
        for c in components_for(entry)
        if c.device_type == DEVICE_TYPE_DEVICE_TRACKER
    )


class FakeDeviceTracker(FakeEntityMixin, TrackerEntity, RestoreEntity):
    """A simulated tracked device, placed in a zone via a select control."""

    _attr_has_entity_name = True
    _attr_source_type = SourceType.GPS

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_tracker"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_in_zones: list[str] = []

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            zones = last_state.attributes.get("in_zones")
            if zones:
                self._attr_in_zones = list(zones)

        set_entity(self.hass, self._component.id, "tracker_entity", self)

    @callback
    def set_zone(self, zone_entity_id: str | None) -> None:
        """Called by the companion zone select (see select.py)."""
        self._attr_in_zones = [zone_entity_id] if zone_entity_id else []
        self.async_write_ha_state()
