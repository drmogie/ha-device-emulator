"""Fake date platform - a standalone, settable date value."""
from __future__ import annotations

from datetime import date

from homeassistant.components.date import DateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import Component, DEVICE_TYPE_DATE, components_for, device_info_for
from .mixins import FakeEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake date entity for each Date component on this device."""
    async_add_entities(
        FakeDate(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_DATE
    )


class FakeDate(FakeEntityMixin, DateEntity, RestoreEntity):
    """A simulated settable date - holds whatever date you last set it to."""

    _attr_has_entity_name = True

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_date"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_value = dt_util.now().date()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._attr_native_value = date.fromisoformat(last_state.state)
            except (TypeError, ValueError):
                pass

    async def async_set_value(self, value: date) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
