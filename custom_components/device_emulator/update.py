"""Fake update platform - one entity per Update component.

Firmware vs software is decided by whether this device has other
components alongside the update (added via "Configure", e.g. a Switch
with an Update component added to it represents that hardware's own
firmware) or is the update on its own (representing a standalone
software/app update) - which is why UpdateDeviceClass only has FIRMWARE;
the absence of a device_class is itself how HA represents software.

Versions use a YYYY.MM.DD.N format - a calendar date plus a plain
incrementing counter for that day, reset to 1 each new day - rather than
semantic versioning or a raw timestamp.

A hidden "Simulate new update" button (see button.py) lets you bump the
latest_version at will, so you can repeatedly test the "update available"
-> install -> "up to date" flow without restarting Home Assistant.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import Component, DEVICE_TYPE_UPDATE, components_for, device_info_for
from .helpers import set_entity
from .mixins import FakeEntityMixin

INSTALL_SECONDS = 5


def _format_version(day, counter: int) -> str:
    return f"{day.strftime('%Y.%m.%d')}.{counter}"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake update entity for each Update component on this device."""
    total_components = len(components_for(entry))
    async_add_entities(
        FakeUpdate(c, is_firmware=total_components > 1)
        for c in components_for(entry)
        if c.device_type == DEVICE_TYPE_UPDATE
    )


class FakeUpdate(FakeEntityMixin, UpdateEntity, RestoreEntity):
    """A simulated pending firmware or software update."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.PROGRESS
        | UpdateEntityFeature.RELEASE_NOTES
    )

    def __init__(self, component: Component, is_firmware: bool) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_device_class = UpdateDeviceClass.FIRMWARE if is_firmware else None
        self._attr_title = "Firmware" if is_firmware else "Software"
        self._attr_release_summary = (
            "Bug fixes and performance improvements."
            if is_firmware
            else "New features, bug fixes, and performance improvements."
        )
        self._attr_release_url = "https://example.com/release-notes"

        self._attr_unique_id = f"{component.id}_update"
        self._attr_device_info = device_info_for(component.entry)

        today = dt_util.utcnow().date()
        self._version_date = today
        self._version_counter = 1
        self._attr_installed_version = _format_version(today - timedelta(days=30), 1)
        self._attr_latest_version = _format_version(today, 1)
        self._attr_in_progress = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            attrs = last_state.attributes
            installed = attrs.get("installed_version")
            latest = attrs.get("latest_version")
            if installed:
                self._attr_installed_version = installed
            if latest:
                self._attr_latest_version = latest

        set_entity(self.hass, self._component.id, "update_entity", self)

    async def async_release_notes(self) -> str | None:
        return (
            "## What's new\n\n"
            "- Improved stability\n"
            "- Minor bug fixes\n"
            "- Performance improvements\n"
        )

    async def async_install(self, version: str | None, backup: bool, **kwargs) -> None:
        self._attr_in_progress = True
        steps = 10
        for step in range(1, steps + 1):
            self._attr_update_percentage = round(step / steps * 100)
            self.async_write_ha_state()
            await asyncio.sleep(INSTALL_SECONDS / steps)
        self._attr_installed_version = version or self._attr_latest_version
        self._attr_in_progress = False
        self._attr_update_percentage = None
        self.async_write_ha_state()

    @callback
    def simulate_new_version(self) -> None:
        """Bump latest_version, as if a new release just shipped."""
        today = dt_util.utcnow().date()
        if today == self._version_date:
            self._version_counter += 1
        else:
            self._version_date = today
            self._version_counter = 1
        self._attr_latest_version = _format_version(self._version_date, self._version_counter)
        self.async_write_ha_state()
