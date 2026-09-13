"""Fake valve platform - one entity per Valve component, animated travel time."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_VALVE, components_for, device_info_for
from .helpers import step_toward
from .mixins import FakeEntityMixin

TICK = timedelta(seconds=0.5)
TRAVEL_SECONDS = 5
STEP_PER_TICK = 100 / (TRAVEL_SECONDS / TICK.total_seconds())


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake valve for each Valve component on this device."""
    async_add_entities(
        FakeValve(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_VALVE
    )


class FakeValve(FakeEntityMixin, ValveEntity, RestoreEntity):
    """A simulated water or gas valve with animated travel time."""

    _attr_has_entity_name = True
    _attr_reports_position = True
    _attr_supported_features = (
        ValveEntityFeature.OPEN
        | ValveEntityFeature.CLOSE
        | ValveEntityFeature.SET_POSITION
        | ValveEntityFeature.STOP
    )

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_device_class = (
            ValveDeviceClass.GAS if component.show_as == "gas" else ValveDeviceClass.WATER
        )
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_valve"
        self._attr_device_info = device_info_for(component.entry)
        self._position = 100.0
        self._target_position = 100.0
        self._remove_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            if (pos := last_state.attributes.get("current_position")) is not None:
                self._position = float(pos)
                self._target_position = self._position

        self._remove_timer = async_track_time_interval(self.hass, self._tick, TICK)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_timer:
            self._remove_timer()

    @property
    def current_valve_position(self) -> int:
        return round(self._position)

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
        if self._position == self._target_position:
            return
        self._position = step_toward(self._position, self._target_position, STEP_PER_TICK)
        self.async_write_ha_state()

    async def async_open_valve(self, **kwargs) -> None:
        self._target_position = 100.0

    async def async_close_valve(self, **kwargs) -> None:
        self._target_position = 0.0

    async def async_set_valve_position(self, position: int, **kwargs) -> None:
        self._target_position = float(position)

    async def async_stop_valve(self, **kwargs) -> None:
        self._target_position = self._position
