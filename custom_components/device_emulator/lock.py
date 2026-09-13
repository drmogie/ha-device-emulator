"""Fake lock platform."""
from __future__ import annotations

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_LOCK, components_for, device_info_for
from .mixins import FakeEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake lock for each Lock component on this device."""
    async_add_entities(
        FakeLock(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_LOCK
    )


class FakeLock(FakeEntityMixin, LockEntity, RestoreEntity):
    """A simulated lock."""

    _attr_has_entity_name = True

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_lock"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_is_locked = True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_locked = last_state.state == "locked"

    async def async_lock(self, **kwargs) -> None:
        self._attr_is_locked = True
        self.async_write_ha_state()

    async def async_unlock(self, **kwargs) -> None:
        self._attr_is_locked = False
        self.async_write_ha_state()
