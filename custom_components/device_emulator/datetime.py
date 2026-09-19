"""Fake date/time platform - a standalone, settable date+time value.

Named datetime.py to match its domain, like every other platform file in
this integration - this does NOT shadow the stdlib datetime module for
anything outside this file: Python resolves plain `import datetime`
elsewhere via sys.path (the real stdlib module), and this file is only
ever reachable as the qualified `custom_components.device_emulator.
datetime` submodule. HA core itself ships integrations with their own
datetime.py platform file the same way.
"""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import Component, DEVICE_TYPE_DATETIME, components_for, device_info_for
from .mixins import FakeEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake date/time entity for each Date & Time component."""
    async_add_entities(
        FakeDateTime(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_DATETIME
    )


class FakeDateTime(FakeEntityMixin, DateTimeEntity, RestoreEntity):
    """A simulated settable date+time - holds whatever you last set it to."""

    _attr_has_entity_name = True

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_datetime"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_value = (
            dt_util.parse_datetime(component.initial)
            if component.initial is not None
            else dt_util.now().replace(microsecond=0)
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            parsed = dt_util.parse_datetime(last_state.state)
            if parsed is not None:
                self._attr_native_value = parsed

    async def async_set_value(self, value: datetime) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
