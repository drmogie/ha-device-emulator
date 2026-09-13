"""Fake robot vacuum platform - one entity per Vacuum component.

Uses the modern activity-based vacuum API (VacuumActivity). Battery
level is reported through a separate sensor entity (see sensor.py) since
current Home Assistant no longer supports battery reporting directly on
the vacuum entity itself - it drains while cleaning, automatically heads
home when it gets low, and recharges while docked, all on a simple
periodic tick.
"""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_VACUUM, components_for, device_info_for
from .helpers import set_entity
from .mixins import FakeEntityMixin

TICK = timedelta(seconds=10)
LOW_BATTERY = 15
RETURN_TICKS = 2  # ~20s simulated travel time back to the dock
FAN_SPEEDS = ["quiet", "standard", "turbo", "max"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake vacuum for each Vacuum component on this device."""
    async_add_entities(
        FakeVacuum(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_VACUUM
    )


class FakeVacuum(FakeEntityMixin, StateVacuumEntity, RestoreEntity):
    """A simulated robot vacuum."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        VacuumEntityFeature.STATE
        | VacuumEntityFeature.START
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.LOCATE
    )
    _attr_fan_speed_list = FAN_SPEEDS

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_vacuum"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_activity = VacuumActivity.DOCKED
        self._attr_fan_speed = "standard"
        self.battery_level = 100  # read by the sibling battery sensor
        self._return_countdown = 0
        self._remove_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in [activity.value for activity in VacuumActivity]:
                self._attr_activity = VacuumActivity(last_state.state)
            self._attr_fan_speed = last_state.attributes.get(
                "fan_speed", self._attr_fan_speed
            )

        set_entity(self.hass, self._component.id, "vacuum_entity", self)
        self._remove_timer = async_track_time_interval(self.hass, self._tick, TICK)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_timer:
            self._remove_timer()

    @callback
    def _tick(self, now) -> None:
        if self._attr_activity == VacuumActivity.CLEANING:
            self.battery_level = max(0, self.battery_level - 2)
            if self.battery_level <= LOW_BATTERY:
                self._attr_activity = VacuumActivity.RETURNING
                self._return_countdown = RETURN_TICKS
        elif self._attr_activity == VacuumActivity.RETURNING:
            self._return_countdown -= 1
            if self._return_countdown <= 0:
                self._attr_activity = VacuumActivity.DOCKED
        elif self._attr_activity == VacuumActivity.DOCKED:
            self.battery_level = min(100, self.battery_level + 5)
        self.async_write_ha_state()

    async def async_start(self) -> None:
        if self.battery_level < 10:
            return  # too low to start, like a real vacuum
        self._attr_activity = VacuumActivity.CLEANING
        self.async_write_ha_state()

    async def async_pause(self) -> None:
        self._attr_activity = VacuumActivity.PAUSED
        self.async_write_ha_state()

    async def async_stop(self, **kwargs) -> None:
        self._attr_activity = VacuumActivity.IDLE
        self.async_write_ha_state()

    async def async_return_to_base(self, **kwargs) -> None:
        self._attr_activity = VacuumActivity.RETURNING
        self._return_countdown = RETURN_TICKS
        self.async_write_ha_state()

    async def async_locate(self, **kwargs) -> None:
        return None

    async def async_set_fan_speed(self, fan_speed: str, **kwargs) -> None:
        self._attr_fan_speed = fan_speed
        self.async_write_ha_state()
