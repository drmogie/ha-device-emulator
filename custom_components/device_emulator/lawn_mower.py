"""Fake lawn mower platform - one entity per Lawn Mower component.

Same shape as the vacuum: battery drains while mowing, automatically
heads home when it gets low, and recharges while docked, all on a
simple periodic tick. Battery is reported through a separate sensor
entity (see sensor.py), matching how neither StateVacuumEntity nor
LawnMowerEntity report battery directly anymore.
"""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_LAWN_MOWER, components_for, device_info_for
from .helpers import set_entity
from .mixins import FakeEntityMixin

TICK = timedelta(seconds=10)
LOW_BATTERY = 15
RETURN_TICKS = 2  # ~20s simulated travel time back to the dock


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake lawn mower for each Lawn Mower component."""
    async_add_entities(
        FakeLawnMower(c)
        for c in components_for(entry)
        if c.device_type == DEVICE_TYPE_LAWN_MOWER
    )


class FakeLawnMower(FakeEntityMixin, LawnMowerEntity, RestoreEntity):
    """A simulated robotic lawn mower."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        LawnMowerEntityFeature.START_MOWING
        | LawnMowerEntityFeature.PAUSE
        | LawnMowerEntityFeature.DOCK
    )

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_lawn_mower"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_activity = LawnMowerActivity.DOCKED
        self.battery_level = 100  # read by the sibling battery sensor
        self._return_countdown = 0
        self._remove_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in [activity.value for activity in LawnMowerActivity]:
                self._attr_activity = LawnMowerActivity(last_state.state)

        set_entity(self.hass, self._component.id, "mower_entity", self)
        self._remove_timer = async_track_time_interval(self.hass, self._tick, TICK)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_timer:
            self._remove_timer()

    @callback
    def _tick(self, now) -> None:
        if self._attr_activity == LawnMowerActivity.MOWING:
            self.battery_level = max(0, self.battery_level - 2)
            if self.battery_level <= LOW_BATTERY:
                self._attr_activity = LawnMowerActivity.RETURNING
                self._return_countdown = RETURN_TICKS
        elif self._attr_activity == LawnMowerActivity.RETURNING:
            self._return_countdown -= 1
            if self._return_countdown <= 0:
                self._attr_activity = LawnMowerActivity.DOCKED
        elif self._attr_activity == LawnMowerActivity.DOCKED:
            self.battery_level = min(100, self.battery_level + 5)
        self.async_write_ha_state()

    async def async_start_mowing(self) -> None:
        if self.battery_level < 10:
            return  # too low to start, like a real mower
        self._attr_activity = LawnMowerActivity.MOWING
        self.async_write_ha_state()

    async def async_pause(self) -> None:
        self._attr_activity = LawnMowerActivity.PAUSED
        self.async_write_ha_state()

    async def async_dock(self) -> None:
        self._attr_activity = LawnMowerActivity.RETURNING
        self._return_countdown = RETURN_TICKS
        self.async_write_ha_state()
