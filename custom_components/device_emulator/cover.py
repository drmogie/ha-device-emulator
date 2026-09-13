"""Fake cover platform - one entity per Cover component.

Movement is animated: position moves toward its target over time instead
of jumping instantly, at a speed that depends on the chosen cover type
(a garage door takes ~14s to fully travel, a blind ~4s). Types that
don't report a percentage in real life (garage, gate, interior door)
still animate open/closed over that same travel time, they just don't
expose a "set to 43%" control. Blinds and shutters also get tilt.
"""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import COVER_PROFILES, Component, DEVICE_TYPE_COVER, components_for, device_info_for
from .helpers import step_toward
from .mixins import FakeEntityMixin

TICK = timedelta(seconds=0.5)
TICKS_PER_SECOND = 1 / TICK.total_seconds()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake cover for each Cover component on this device."""
    async_add_entities(
        FakeCover(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_COVER
    )


class FakeCover(FakeEntityMixin, CoverEntity, RestoreEntity):
    """A simulated cover with realistic travel time."""

    _attr_has_entity_name = True

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        show_as = component.show_as or "blind"
        profile = COVER_PROFILES.get(show_as, {"position": True, "tilt": False, "seconds": 6})

        self._supports_position = profile["position"]
        self._supports_tilt = profile["tilt"]
        self._step_per_tick = 100 / (profile["seconds"] * TICKS_PER_SECOND)

        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_cover"
        self._attr_device_class = CoverDeviceClass(show_as)
        self._attr_device_info = device_info_for(component.entry)

        features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        if self._supports_position:
            features |= CoverEntityFeature.SET_POSITION
        if self._supports_tilt:
            features |= (
                CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.SET_TILT_POSITION
            )
        self._attr_supported_features = features

        self._position = 100.0
        self._target_position = 100.0
        self._tilt = 100.0
        self._target_tilt = 100.0
        self._remove_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            attrs = last_state.attributes
            if (pos := attrs.get("current_position")) is not None:
                self._position = float(pos)
                self._target_position = self._position
            if (tilt := attrs.get("current_tilt_position")) is not None:
                self._tilt = float(tilt)
                self._target_tilt = self._tilt

        self._remove_timer = async_track_time_interval(self.hass, self._tick, TICK)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_timer:
            self._remove_timer()

    @property
    def current_cover_position(self) -> int | None:
        return round(self._position) if self._supports_position else None

    @property
    def current_cover_tilt_position(self) -> int | None:
        return round(self._tilt) if self._supports_tilt else None

    @property
    def is_closed(self) -> bool:
        return self._position <= 0

    @property
    def is_opening(self) -> bool:
        return self._target_position > self._position

    @property
    def is_closing(self) -> bool:
        return self._target_position < self._position

    @callback
    def _tick(self, now) -> None:
        changed = False
        if self._position != self._target_position:
            self._position = step_toward(self._position, self._target_position, self._step_per_tick)
            changed = True
        if self._tilt != self._target_tilt:
            self._tilt = step_toward(self._tilt, self._target_tilt, self._step_per_tick)
            changed = True
        if changed:
            self.async_write_ha_state()

    async def async_open_cover(self, **kwargs) -> None:
        self._target_position = 100.0

    async def async_close_cover(self, **kwargs) -> None:
        self._target_position = 0.0

    async def async_stop_cover(self, **kwargs) -> None:
        self._target_position = self._position

    async def async_set_cover_position(self, **kwargs) -> None:
        self._target_position = float(kwargs["position"])

    async def async_open_cover_tilt(self, **kwargs) -> None:
        self._target_tilt = 100.0

    async def async_close_cover_tilt(self, **kwargs) -> None:
        self._target_tilt = 0.0

    async def async_set_cover_tilt_position(self, **kwargs) -> None:
        self._target_tilt = float(kwargs["tilt_position"])
