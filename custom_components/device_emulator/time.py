"""Fake time platform - a standalone, settable time-of-day value."""
from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import Component, DEVICE_TYPE_TIME, components_for, device_info_for
from .mixins import FakeEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake time entity for each Time component on this device."""
    async_add_entities(
        FakeTime(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_TIME
    )


class FakeTime(FakeEntityMixin, TimeEntity, RestoreEntity):
    """A simulated settable time - holds whatever time you last set it to."""

    _attr_has_entity_name = True

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_time"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_value = (
            time.fromisoformat(component.initial)
            if component.initial is not None
            else dt_util.now().time().replace(microsecond=0)
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._attr_native_value = time.fromisoformat(last_state.state)
            except (TypeError, ValueError):
                pass

    async def async_set_value(self, value: time) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
