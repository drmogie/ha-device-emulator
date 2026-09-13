"""Fake camera platform - one entity per Camera component.

Serves the configured image source (a URL or a path under your www
folder, served at /local/) for both the snapshot and the "live" view.
There's no real video stream here - since CameraEntityFeature.STREAM
isn't declared, Home Assistant's own camera component automatically
falls back to repeatedly polling async_camera_image() to fake an MJPEG
feed, so the same source serves both cases without extra code.
"""
from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

import aiohttp

from .const import Component, DEVICE_TYPE_CAMERA, components_for, device_info_for
from .mixins import FakeEntityMixin

FETCH_TIMEOUT = aiohttp.ClientTimeout(total=10)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake camera for each Camera component on this device."""
    async_add_entities(
        FakeCamera(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_CAMERA
    )


class FakeCamera(FakeEntityMixin, Camera):
    """A simulated camera serving a fixed image as both live and still."""

    _attr_has_entity_name = True

    def __init__(self, component: Component) -> None:
        Camera.__init__(self)
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._source: str = component.image_source or ""
        self._attr_unique_id = f"{component.id}_camera"
        self._attr_device_info = device_info_for(component.entry)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        if not self._source:
            return None

        if self._source.startswith(("http://", "https://")):
            session = async_get_clientsession(self.hass)
            try:
                async with session.get(self._source, timeout=FETCH_TIMEOUT) as response:
                    if response.status != 200:
                        return None
                    return await response.read()
            except Exception:  # noqa: BLE001 - any fetch failure just means no image
                return None

        path = self.hass.config.path(
            "www", self._source.removeprefix("/local/").removeprefix("local/")
        )
        try:
            return await self.hass.async_add_executor_job(_read_file, path)
        except OSError:
            return None


def _read_file(path: str) -> bytes:
    with open(path, "rb") as file:
        return file.read()
