"""Fake number platform.

Every hidden "set this value directly" control lives here, one per
matching component:
  - Vacuum / lawn mower: battery level
  - Sensor: the value itself (this IS the whole point of that component) -
    named with its show-as label, e.g. "Temperature Value", so a composed
    device with several sensors doesn't end up with several identical
    "Value" controls
  - Climate: current temperature (independent of the target)
  - Water heater: current temperature
  - Humidifier: current humidity
  - Air quality: PM2.5 reading

Setting one pushes a value into the sibling entity and lets it continue
its normal simulation (drift, drain, etc.) from that point. Battery-style
values (vacuum/mower battery, and Sensor shown as Battery) also drain/
charge on their own, so these numbers poll their sibling periodically and
update the displayed slider to match - otherwise it would silently go
stale the moment the sibling's own simulation moved the value.
"""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    Component,
    DEVICE_TYPE_AIR_QUALITY,
    DEVICE_TYPE_CLIMATE,
    DEVICE_TYPE_HUMIDIFIER,
    DEVICE_TYPE_LAWN_MOWER,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_VACUUM,
    DEVICE_TYPE_WATER_HEATER,
    SENSOR_SHOW_AS_SPECS,
    components_for,
    device_info_for,
)
from .helpers import get_entity

POLL_INTERVAL = timedelta(seconds=5)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake number control for each matching component on this device."""
    entities = []
    for component in components_for(entry):
        if component.device_type in (DEVICE_TYPE_VACUUM, DEVICE_TYPE_LAWN_MOWER):
            entities.append(FakeBatteryLevelNumber(component))
        elif component.device_type == DEVICE_TYPE_SENSOR:
            entities.append(FakeSensorValueNumber(component))
        elif component.device_type == DEVICE_TYPE_CLIMATE:
            entities.append(FakeCurrentTemperatureNumber(component, "climate_entity"))
        elif component.device_type == DEVICE_TYPE_WATER_HEATER:
            entities.append(FakeCurrentTemperatureNumber(component, "water_heater_entity"))
        elif component.device_type == DEVICE_TYPE_HUMIDIFIER:
            entities.append(FakeCurrentHumidityNumber(component))
        elif component.device_type == DEVICE_TYPE_AIR_QUALITY:
            entities.append(FakePm25Number(component))
    async_add_entities(entities)


class FakeBatteryLevelNumber(NumberEntity):
    """Lets you set the vacuum's or lawn mower's battery level directly.

    Also polls that sibling every few seconds so the slider tracks the
    battery as it drains while running and recharges while docked,
    instead of only reflecting the last value you set it to.
    """

    _attr_has_entity_name = True
    _attr_name = "Battery level"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_icon = "mdi:battery-sync"

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._sibling_key = (
            "vacuum_entity" if component.device_type == DEVICE_TYPE_VACUUM else "mower_entity"
        )
        self._attr_unique_id = f"{component.id}_battery_level_control"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_value = 100

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_time_interval(self.hass, self._tick, POLL_INTERVAL)
        )
        self._sync()

    @callback
    def _tick(self, now) -> None:
        self._sync()

    def _sync(self) -> None:
        """Pull the sibling's live value in case its own simulation moved it."""
        sibling = get_entity(self.hass, self._component.id, self._sibling_key)
        if sibling is not None and sibling.battery_level != self._attr_native_value:
            self._attr_native_value = sibling.battery_level
            self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()

        sibling = get_entity(self.hass, self._component.id, self._sibling_key)
        if sibling is not None:
            sibling.battery_level = int(value)

        battery_sensor = get_entity(self.hass, self._component.id, "battery_sensor_entity")
        if battery_sensor is not None:
            battery_sensor.refresh()


class FakeSensorValueNumber(NumberEntity):
    """Lets you set a Sensor component's value directly.

    Named after the show-as label (e.g. "Temperature Value") so a
    composed device with several sensors gets distinguishable controls.
    When shown as Battery, this also polls the sibling sensor so the
    slider tracks the charge/drain simulation - see sensor.py.
    """

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:tune-variant"

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        show_as = component.show_as or "temperature"
        self._is_battery = show_as == "battery"
        label, unit, default, minimum, maximum, step = SENSOR_SHOW_AS_SPECS[show_as]

        self._attr_name = f"{label} Value"
        self._attr_unique_id = f"{component.id}_value_control"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_value = default

    async def async_added_to_hass(self) -> None:
        if self._is_battery:
            self.async_on_remove(
                async_track_time_interval(self.hass, self._tick, POLL_INTERVAL)
            )
        self._sync()

    @callback
    def _tick(self, now) -> None:
        self._sync()

    def _sync(self) -> None:
        sibling = get_entity(self.hass, self._component.id, "value_entity")
        if sibling is not None and sibling.native_value != self._attr_native_value:
            self._attr_native_value = sibling.native_value
            self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
        sibling = get_entity(self.hass, self._component.id, "value_entity")
        if sibling is not None:
            sibling.set_value(value)


class FakeCurrentTemperatureNumber(NumberEntity):
    """Lets you set a climate or water heater's current temperature directly."""

    _attr_has_entity_name = True
    _attr_name = "Current temperature"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_native_min_value = 0
    _attr_native_max_value = 150
    _attr_native_step = 0.5
    _attr_icon = "mdi:thermometer"

    def __init__(self, component: Component, sibling_key: str) -> None:
        self._component = component
        self._entry = component.entry
        self._sibling_key = sibling_key
        self._attr_unique_id = f"{component.id}_current_temperature_control"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_value = 70.0

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
        sibling = get_entity(self.hass, self._component.id, self._sibling_key)
        if sibling is not None:
            sibling.set_current_temperature(value)


class FakeCurrentHumidityNumber(NumberEntity):
    """Lets you set a humidifier's current humidity directly."""

    _attr_has_entity_name = True
    _attr_name = "Current humidity"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_icon = "mdi:water-percent"

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_unique_id = f"{component.id}_current_humidity_control"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_value = 40.0

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
        sibling = get_entity(self.hass, self._component.id, "humidifier_entity")
        if sibling is not None:
            sibling.set_current_humidity(value)


class FakePm25Number(NumberEntity):
    """Lets you set the air quality station's PM2.5 reading directly."""

    _attr_has_entity_name = True
    _attr_name = "PM2.5"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = "µg/m³"
    _attr_native_min_value = 0
    _attr_native_max_value = 500
    _attr_native_step = 1
    _attr_icon = "mdi:blur"

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_unique_id = f"{component.id}_pm25_control"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_native_value = 12.0

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
        sibling = get_entity(self.hass, self._component.id, "air_quality_entity")
        if sibling is not None:
            sibling.set_pm25(value)
