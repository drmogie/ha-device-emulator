"""Fake image platform - one entity per Image component.

Unlike camera, image entities are meant to be fetched once and stay
static until refreshed - so this reads the configured source (a URL or
a path under your www folder, served at /local/) once, and only
re-reads it when the hidden "Refresh image" button is pressed.

For URLs, ImageEntity's own `image_url` handles fetching and caching
automatically. For local paths, `image()` is overridden to read the
file directly - `image_url` stays UNDEFINED so the base class falls
through to calling it.
"""
from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import Component, DEVICE_TYPE_IMAGE, components_for, device_info_for
from .helpers import set_entity
from .mixins import FakeEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake image entity for each Image component on this device."""
    async_add_entities(
        FakeImage(hass, c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_IMAGE
    )


class FakeImage(FakeEntityMixin, ImageEntity):
    """A simulated static image, fetched once and refreshed on demand."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, component: Component) -> None:
        ImageEntity.__init__(self, hass)
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        source = component.image_source or ""
        self._local_path = None

        if source.startswith(("http://", "https://")):
            self._attr_image_url = source
        else:
            self._local_path = hass.config.path(
                "www", source.removeprefix("/local/").removeprefix("local/")
            )

        self._attr_unique_id = f"{component.id}_image"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_image_last_updated = dt_util.utcnow()

    def image(self) -> bytes | None:
        if self._local_path is None:
            return None
        try:
            with open(self._local_path, "rb") as file:
                return file.read()
        except OSError:
            return None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        set_entity(self.hass, self._component.id, "image_entity", self)

    def refresh_image(self) -> None:
        """Called by the hidden 'Refresh image' button (see button.py)."""
        self._cached_image = None
        self._attr_image_last_updated = dt_util.utcnow()
        self.async_write_ha_state()
