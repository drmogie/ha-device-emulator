"""Fake water heater platform - one entity per Water Heater component."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_ELECTRIC,
    STATE_GAS,
    STATE_HEAT_PUMP,
    STATE_HIGH_DEMAND,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_WATER_HEATER, components_for, device_info_for
from .helpers import set_entity, step_toward
from .mixins import FakeEntityMixin

TICK = timedelta(seconds=60)
DRIFT_PER_TICK = 0.5
AWAY_OFFSET = 20.0

OPERATION_LIST = [STATE_OFF, STATE_ECO, STATE_ELECTRIC, STATE_GAS, STATE_HEAT_PUMP, STATE_HIGH_DEMAND]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake water heater for each Water Heater component."""
    async_add_entities(
        FakeWaterHeater(c)
        for c in components_for(entry)
        if c.device_type == DEVICE_TYPE_WATER_HEATER
    )


class FakeWaterHeater(FakeEntityMixin, WaterHeaterEntity, RestoreEntity):
    """A simulated tank water heater."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_operation_list = OPERATION_LIST
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
        | WaterHeaterEntityFeature.AWAY_MODE
    )
    _attr_min_temp = 90
    _attr_max_temp = 140
    _attr_target_temperature_step = 1

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_water_heater"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_current_operation = STATE_ECO
        self._attr_target_temperature = 120.0
        self._attr_current_temperature = 116.0
        self._attr_is_away_mode_on = False
        self._remove_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        set_entity(self.hass, self._component.id, "water_heater_entity", self)

        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in OPERATION_LIST:
                self._attr_current_operation = last_state.state
            attrs = last_state.attributes
            self._attr_target_temperature = attrs.get(
                ATTR_TEMPERATURE, self._attr_target_temperature
            )
            self._attr_current_temperature = attrs.get(
                "current_temperature", self._attr_current_temperature
            )
            self._attr_is_away_mode_on = attrs.get("away_mode", self._attr_is_away_mode_on) == "on"

        self._remove_timer = async_track_time_interval(self.hass, self._tick, TICK)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_timer:
            self._remove_timer()

    @callback
    def _tick(self, now) -> None:
        if self._attr_current_operation == STATE_OFF:
            return
        target = self._attr_target_temperature
        if self._attr_is_away_mode_on:
            target -= AWAY_OFFSET
        self._attr_current_temperature = round(
            step_toward(self._attr_current_temperature, target, DRIFT_PER_TICK), 1
        )
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._attr_target_temperature = temperature
            self.async_write_ha_state()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        self._attr_current_operation = operation_mode
        self.async_write_ha_state()

    async def async_turn_away_mode_on(self) -> None:
        self._attr_is_away_mode_on = True
        self.async_write_ha_state()

    async def async_turn_away_mode_off(self) -> None:
        self._attr_is_away_mode_on = False
        self.async_write_ha_state()

    def set_current_temperature(self, value: float) -> None:
        """Called by the hidden 'Current temperature' number (see number.py)."""
        self._attr_current_temperature = value
        self.async_write_ha_state()
