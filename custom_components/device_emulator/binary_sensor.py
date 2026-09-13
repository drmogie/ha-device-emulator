"""Fake binary_sensor platform (motion, door, smoke, and 15 other classes,
plus the battery-charging companion for a battery-shown Sensor component).

Mirrors the state of the paired "Simulate ___" switch (see switch.py) so
you have a normal, read-only binary_sensor to build cards and automations
against - exactly like a real sensor. "Momentary" classes (motion,
occupancy, presence, sound, vibration) auto-clear themselves after a bit,
like a real PIR or mic-based sensor would, and turn their own switch back
off to match. Everything else (door, smoke, moisture, ...) stays tripped
until you flip the switch back yourself, matching how those sensors
behave in real life.

Subscribes to the switch via the helper pub/sub in helpers.py, keyed by
each component's own id, instead of an entity-registry lookup - so the
link always forms regardless of setup order, and two of these on one
composed device never cross-wire.
"""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    BINARY_SENSOR_AUTO_CLEAR,
    BINARY_SENSOR_AUTO_CLEAR_SECONDS,
    Component,
    DEVICE_TYPE_BINARY_SENSOR,
    DEVICE_TYPE_SENSOR,
    components_for,
    device_info_for,
)
from .helpers import get_switch_entity, register_switch_listener
from .mixins import FakeEntityMixin

CLEAR_AFTER = timedelta(seconds=BINARY_SENSOR_AUTO_CLEAR_SECONDS)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake binary sensor for each matching component on this device."""
    entities = []
    for component in components_for(entry):
        if component.device_type == DEVICE_TYPE_BINARY_SENSOR:
            entities.append(FakeBinarySensor(component))
        elif component.device_type == DEVICE_TYPE_SENSOR and component.show_as == "battery":
            entities.append(FakeBatteryChargingSensor(component))
    async_add_entities(entities)


class FakeBinarySensor(FakeEntityMixin, BinarySensorEntity, RestoreEntity):
    """A simulated binary sensor of whatever device class was chosen."""

    _attr_has_entity_name = True

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        show_as = component.show_as or "motion"
        self._auto_clears = show_as in BINARY_SENSOR_AUTO_CLEAR

        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_binary_sensor"
        self._attr_device_class = BinarySensorDeviceClass(show_as)
        self._attr_device_info = device_info_for(component.entry)
        self._attr_is_on = False
        self._clear_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == "on"

        self.async_on_remove(
            register_switch_listener(
                self.hass, self._component.id, self._handle_switch_change
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._clear_timer:
            self._clear_timer()

    @callback
    def _handle_switch_change(self, is_on: bool) -> None:
        self._attr_is_on = is_on
        self.async_write_ha_state()

        if self._clear_timer:
            self._clear_timer()
            self._clear_timer = None

        if self._auto_clears and is_on:
            self._clear_timer = async_track_time_interval(
                self.hass, self._auto_clear, CLEAR_AFTER
            )

    @callback
    def _auto_clear(self, now) -> None:
        self._clear_timer = None
        switch_entity = get_switch_entity(self.hass, self._component.id)
        if switch_entity is not None:
            self.hass.async_create_task(switch_entity.async_turn_off())


class FakeBatteryChargingSensor(FakeEntityMixin, BinarySensorEntity, RestoreEntity):
    """Mirrors the hidden "Charging" switch for a battery-shown Sensor component.

    Real battery-powered devices commonly pair a battery % sensor with a
    battery_charging binary_sensor exactly like this.
    """

    _attr_has_entity_name = True
    _attr_name = "Charging"
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_unique_id = f"{component.id}_battery_charging"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == "on"

        self.async_on_remove(
            register_switch_listener(
                self.hass, self._component.id, self._handle_switch_change
            )
        )

    @callback
    def _handle_switch_change(self, is_on: bool) -> None:
        self._attr_is_on = is_on
        self.async_write_ha_state()
