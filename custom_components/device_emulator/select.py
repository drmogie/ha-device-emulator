"""Fake select platform.

Three things live here:
  - "Simulated status" - one per DEVICE (entry-scoped, not per
    component), lets you force it to Unavailable or Unknown (Home
    Assistant's real special states) to see how your dashboards and
    automations handle it, or back to Normal. Every component on this
    device shares the same one - the actual override logic lives in
    mixins.py / helpers.py, keyed by entry id; this entity is just the
    dashboard control for it.
  - "Weather condition" - one per Weather component, overrides the
    simulated condition (see weather.py).
  - "Zone" - one per Device Tracker component, picks which zone that
    tracked device is in (see device_tracker.py).

All three are hidden config controls and are never themselves affected
by the status they control - otherwise you could set a device to
Unavailable and have no way to click it back to Normal.
"""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    Component,
    DEVICE_TRACKER_NOT_HOME_OPTION,
    DEVICE_TYPE_DEVICE_TRACKER,
    DEVICE_TYPE_WEATHER,
    WEATHER_AUTO_OPTION,
    WEATHER_CONDITION_OPTIONS,
    components_for,
    device_info_for,
)
from .helpers import STATE_OVERRIDE_OPTIONS, get_entity, set_entity, set_state_override


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the fake select entities for this device."""
    entities: list[SelectEntity] = [FakeStatusSelect(entry)]
    for component in components_for(entry):
        if component.device_type == DEVICE_TYPE_WEATHER:
            entities.append(FakeWeatherConditionSelect(component))
        elif component.device_type == DEVICE_TYPE_DEVICE_TRACKER:
            entities.append(FakeZoneSelect(component))
    async_add_entities(entities)


class FakeStatusSelect(SelectEntity, RestoreEntity):
    """Forces every entity on this device to Unavailable, Unknown, or Normal."""

    _attr_has_entity_name = True
    _attr_name = "Simulated status"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:progress-question"
    _attr_options = STATE_OVERRIDE_OPTIONS

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_simulated_status"
        self._attr_device_info = device_info_for(entry)
        self._attr_current_option = STATE_OVERRIDE_OPTIONS[0]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in self._attr_options:
                self._attr_current_option = last_state.state
                self._apply()

    def _apply(self) -> None:
        set_state_override(self.hass, self._entry.entry_id, self._attr_current_option)

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
        self._apply()


class FakeWeatherConditionSelect(SelectEntity, RestoreEntity):
    """Lets you force the weather condition, or hand it back to auto-cycling."""

    _attr_has_entity_name = True
    _attr_name = "Weather condition"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:weather-partly-cloudy"
    _attr_options = WEATHER_CONDITION_OPTIONS

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_unique_id = f"{component.id}_condition_override"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_current_option = WEATHER_AUTO_OPTION

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in self._attr_options:
                self._attr_current_option = last_state.state
                self._apply()

    def _apply(self) -> None:
        weather_entity = get_entity(self.hass, self._component.id, "weather_entity")
        if weather_entity is not None:
            weather_entity.set_condition_override(self._attr_current_option)

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
        self._apply()


class FakeZoneSelect(SelectEntity, RestoreEntity):
    """Lets you pick which zone this tracked device is currently in.

    Options are gathered from the zones actually defined in this Home
    Assistant instance - refreshed here on creation/restart, and on
    demand via the hidden "Refresh zones" button (see button.py) -
    plus "Not Home".
    """

    _attr_has_entity_name = True
    _attr_name = "Zone"
    _attr_icon = "mdi:map-marker-radius"

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_unique_id = f"{component.id}_zone_select"
        self._attr_device_info = device_info_for(component.entry)
        self._zone_map: dict[str, str] = {}  # option label -> zone entity_id
        self._attr_options = [DEVICE_TRACKER_NOT_HOME_OPTION]
        self._attr_current_option = DEVICE_TRACKER_NOT_HOME_OPTION

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        set_entity(self.hass, self._component.id, "zone_select_entity", self)
        self.refresh_zones()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in self._attr_options:
                self._attr_current_option = last_state.state
                self._apply()

    @callback
    def refresh_zones(self) -> None:
        """Re-scan zone.* entities currently defined in Home Assistant."""
        self._zone_map = {
            state.name: state.entity_id for state in self.hass.states.async_all("zone")
        }
        self._attr_options = [DEVICE_TRACKER_NOT_HOME_OPTION] + sorted(self._zone_map)
        if self._attr_current_option not in self._attr_options:
            self._attr_current_option = DEVICE_TRACKER_NOT_HOME_OPTION
        self.async_write_ha_state()

    def _apply(self) -> None:
        tracker = get_entity(self.hass, self._component.id, "tracker_entity")
        if tracker is not None:
            tracker.set_zone(self._zone_map.get(self._attr_current_option))

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
        self._apply()
