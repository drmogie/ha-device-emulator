"""Fake sensor platform.

Three roles share this file, one entity per matching component:
  - Outlet power monitoring (Switch component shown as an outlet)
  - Vacuum / lawn mower battery (modern StateVacuumEntity/LawnMowerEntity
    no longer report battery themselves - it's a dedicated sensor now)
  - The standalone Sensor component itself - a generic settable numeric
    sensor for whichever device_class was picked (temperature, humidity,
    power, ...), controlled by a paired hidden number entity (see
    number.py). When shown as Battery, it also drains/charges on its
    own, driven by the hidden "Charging" switch (see switch.py).

Both the sensor and its number get the show-as label in their name (e.g.
"Temperature" / "Temperature Value") so a composed device with several
sensors doesn't end up with identical-looking entities.
"""
from __future__ import annotations

import random
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    Component,
    DEVICE_TYPE_LAWN_MOWER,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_SWITCH,
    DEVICE_TYPE_VACUUM,
    SENSOR_SHOW_AS_SPECS,
    components_for,
    device_info_for,
)
from .helpers import get_entity, get_switch_entity, register_switch_listener, set_entity
from .mixins import FakeEntityMixin

PLUG_UPDATE_INTERVAL = timedelta(seconds=30)
MIN_WATTS = 38
MAX_WATTS = 65

BATTERY_POLL_INTERVAL = timedelta(seconds=10)
BATTERY_TICK_INTERVAL = timedelta(seconds=5)
BATTERY_CHARGE_STEP = 3
BATTERY_DRAIN_STEP = 1

# device_class -> HA SensorDeviceClass, for the standalone generic sensor.
DEVICE_CLASS_MAP = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "humidity": SensorDeviceClass.HUMIDITY,
    "illuminance": SensorDeviceClass.ILLUMINANCE,
    "pressure": SensorDeviceClass.PRESSURE,
    "carbon_dioxide": SensorDeviceClass.CO2,
    "pm25": SensorDeviceClass.PM25,
    "voltage": SensorDeviceClass.VOLTAGE,
    "current": SensorDeviceClass.CURRENT,
    "power": SensorDeviceClass.POWER,
    "energy": SensorDeviceClass.ENERGY,
    "battery": SensorDeviceClass.BATTERY,
    "signal_strength": SensorDeviceClass.SIGNAL_STRENGTH,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake sensor for each matching component on this device."""
    entities = []
    for component in components_for(entry):
        if component.device_type == DEVICE_TYPE_SWITCH and component.show_as == "outlet":
            entities.append(FakePlugPower(component))
        elif component.device_type == DEVICE_TYPE_VACUUM:
            entities.append(FakeBatterySensor(component, "vacuum_entity"))
        elif component.device_type == DEVICE_TYPE_LAWN_MOWER:
            entities.append(FakeBatterySensor(component, "mower_entity"))
        elif component.device_type == DEVICE_TYPE_SENSOR:
            entities.append(FakeGenericSensor(component))
    async_add_entities(entities)


class FakePlugPower(FakeEntityMixin, SensorEntity):
    """Simulated power draw for a switch shown as an outlet."""

    _attr_has_entity_name = True
    _attr_name = "Power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_unique_id = f"{component.id}_power"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_value = 0
        self._is_on = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        self.async_on_remove(
            register_switch_listener(
                self.hass, self._component.id, self._handle_switch_change
            )
        )
        self.async_on_remove(
            async_track_time_interval(self.hass, self._tick, PLUG_UPDATE_INTERVAL)
        )

    @callback
    def _handle_switch_change(self, is_on: bool) -> None:
        self._is_on = is_on
        self._update_power()
        self.async_write_ha_state()

    @callback
    def _tick(self, now) -> None:
        self._update_power()
        self.async_write_ha_state()

    def _update_power(self) -> None:
        if self._is_on:
            self._attr_native_value = round(random.uniform(MIN_WATTS, MAX_WATTS), 1)
        else:
            self._attr_native_value = 0


class FakeBatterySensor(FakeEntityMixin, SensorEntity):
    """Battery level read from a sibling vacuum or lawn mower entity.

    Modern StateVacuumEntity/LawnMowerEntity no longer report battery
    themselves, so this mirrors it as a proper dedicated battery sensor,
    the way real integrations do it today.
    """

    _attr_has_entity_name = True
    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, component: Component, sibling_key: str) -> None:
        self._component = component
        self._entry = component.entry
        self._sibling_key = sibling_key
        self._attr_unique_id = f"{component.id}_battery"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_value = 100

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        set_entity(self.hass, self._component.id, "battery_sensor_entity", self)
        self.async_on_remove(
            async_track_time_interval(self.hass, self._tick, BATTERY_POLL_INTERVAL)
        )
        self.refresh()

    @callback
    def _tick(self, now) -> None:
        self.refresh()

    @callback
    def refresh(self) -> None:
        """Pull the latest value from the sibling entity and write it."""
        sibling = get_entity(self.hass, self._component.id, self._sibling_key)
        if sibling is not None:
            self._attr_native_value = sibling.battery_level
            self.async_write_ha_state()


class FakeGenericSensor(FakeEntityMixin, SensorEntity, RestoreEntity):
    """A generic settable sensor for the standalone Sensor component.

    Its value is driven by the paired hidden number control (see
    number.py) - a raw sensor's whole purpose in this integration is to
    hold whatever value you set it to. The one exception is when shown
    as Battery: it also drains and charges on its own, driven by the
    hidden "Charging" switch (see switch.py), the same way a real
    battery-powered device's reported level moves on its own.
    """

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        show_as = component.show_as or "temperature"
        self._is_battery = show_as == "battery"
        label, unit, default, _min, _max, _step = SENSOR_SHOW_AS_SPECS[show_as]

        self._attr_name = label
        self._attr_unique_id = f"{component.id}_sensor"
        self._attr_device_class = DEVICE_CLASS_MAP.get(show_as)
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = default
        self._attr_device_info = device_info_for(component.entry)
        self._charging = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        set_entity(self.hass, self._component.id, "value_entity", self)
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._attr_native_value = float(last_state.state)
            except (TypeError, ValueError):
                pass

        if self._is_battery:
            self.async_on_remove(
                register_switch_listener(
                    self.hass, self._component.id, self._handle_charging_change
                )
            )
            self.async_on_remove(
                async_track_time_interval(self.hass, self._battery_tick, BATTERY_TICK_INTERVAL)
            )

    @callback
    def _handle_charging_change(self, is_on: bool) -> None:
        self._charging = is_on

    @callback
    def _battery_tick(self, now) -> None:
        value = self._attr_native_value or 0
        if self._charging:
            value = min(100, value + BATTERY_CHARGE_STEP)
            if value >= 100:
                switch_entity = get_switch_entity(self.hass, self._component.id)
                if switch_entity is not None:
                    self.hass.async_create_task(switch_entity.async_turn_off())
        else:
            value = max(0, value - BATTERY_DRAIN_STEP)

        if value != self._attr_native_value:
            self._attr_native_value = value
            self.async_write_ha_state()

    @callback
    def set_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()

    @callback
    def replace_battery(self) -> None:
        """Called by the hidden 'Replace battery' button (see button.py)."""
        self._attr_native_value = 100
        self.async_write_ha_state()
        switch_entity = get_switch_entity(self.hass, self._component.id)
        if switch_entity is not None:
            self.hass.async_create_task(switch_entity.async_turn_off())
