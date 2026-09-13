"""Fake button platform.

Five roles share this file, all pure "puppet" controls that set a
sibling entity's value or state - none of them are the actual reported
entity, so none respect the "Simulated status" override (that stays on
the primary entity in each case: event.py, update.py, device_tracker.py,
sensor.py):

  - Button component: three press-type triggers (single/double/long),
    each calling the sibling event entity's trigger() (see event.py)
    with the matching event type.
  - Update component: a hidden "Simulate new update" button that bumps
    the sibling update entity's latest_version, for re-testing the
    update flow without restarting Home Assistant.
  - Device Tracker component: a hidden "Refresh zones" button that
    re-scans the zones currently defined in this Home Assistant.
  - Image component: a hidden "Refresh image" button that forces a re-fetch.
  - Sensor component shown as Battery: a hidden "Replace battery" button
    that resets the sibling sensor to 100% and stops charging.
"""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    Component,
    DEVICE_TYPE_BUTTON,
    DEVICE_TYPE_DEVICE_TRACKER,
    DEVICE_TYPE_IMAGE,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_UPDATE,
    components_for,
    device_info_for,
)
from .helpers import get_entity

PRESS_TYPES = [
    ("single_press", "Trigger single press", "mdi:gesture-tap"),
    ("double_press", "Trigger double press", "mdi:gesture-double-tap"),
    ("long_press", "Trigger long press", "mdi:gesture-tap-hold"),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake button (or three) for each matching component."""
    entities = []
    for component in components_for(entry):
        if component.device_type == DEVICE_TYPE_BUTTON:
            entities.extend(
                FakePressButton(component, event_type, name, icon)
                for event_type, name, icon in PRESS_TYPES
            )
        elif component.device_type == DEVICE_TYPE_UPDATE:
            entities.append(FakeUpdateTriggerButton(component))
        elif component.device_type == DEVICE_TYPE_DEVICE_TRACKER:
            entities.append(FakeRefreshZonesButton(component))
        elif component.device_type == DEVICE_TYPE_IMAGE:
            entities.append(FakeRefreshImageButton(component))
        elif component.device_type == DEVICE_TYPE_SENSOR and component.show_as == "battery":
            entities.append(FakeReplaceBatteryButton(component))
    async_add_entities(entities)


class FakePressButton(ButtonEntity):
    """Triggers one specific press type on the sibling event entity."""

    _attr_has_entity_name = True

    def __init__(self, component: Component, event_type: str, name: str, icon: str) -> None:
        self._component = component
        self._entry = component.entry
        self._event_type = event_type
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{component.id}_press_{event_type}"
        self._attr_device_info = device_info_for(component.entry)

    async def async_press(self) -> None:
        event_entity = get_entity(self.hass, self._component.id, "event_entity")
        if event_entity is not None:
            event_entity.trigger(self._event_type)


class FakeUpdateTriggerButton(ButtonEntity):
    """Hidden button that bumps the sibling update entity's latest_version."""

    _attr_has_entity_name = True
    _attr_name = "Simulate new update"
    _attr_icon = "mdi:cloud-download-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_unique_id = f"{component.id}_simulate_update"
        self._attr_device_info = device_info_for(component.entry)

    async def async_press(self) -> None:
        update_entity = get_entity(self.hass, self._component.id, "update_entity")
        if update_entity is not None:
            update_entity.simulate_new_version()


class FakeRefreshZonesButton(ButtonEntity):
    """Hidden button that re-scans zones for the sibling zone select."""

    _attr_has_entity_name = True
    _attr_name = "Refresh zones"
    _attr_icon = "mdi:map-marker-radius"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_unique_id = f"{component.id}_refresh_zones"
        self._attr_device_info = device_info_for(component.entry)

    async def async_press(self) -> None:
        zone_select = get_entity(self.hass, self._component.id, "zone_select_entity")
        if zone_select is not None:
            zone_select.refresh_zones()


class FakeRefreshImageButton(ButtonEntity):
    """Hidden button that forces the sibling image entity to re-fetch."""

    _attr_has_entity_name = True
    _attr_name = "Refresh image"
    _attr_icon = "mdi:image-refresh-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_unique_id = f"{component.id}_refresh_image"
        self._attr_device_info = device_info_for(component.entry)

    async def async_press(self) -> None:
        image_entity = get_entity(self.hass, self._component.id, "image_entity")
        if image_entity is not None:
            image_entity.refresh_image()


class FakeReplaceBatteryButton(ButtonEntity):
    """Hidden button that resets the sibling battery sensor to 100%.

    Only created when a Sensor component is shown as Battery - simulates
    swapping in a fresh battery, and stops any charging in progress.
    """

    _attr_has_entity_name = True
    _attr_name = "Replace battery"
    _attr_icon = "mdi:battery-plus-variant"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_unique_id = f"{component.id}_replace_battery"
        self._attr_device_info = device_info_for(component.entry)

    async def async_press(self) -> None:
        value_entity = get_entity(self.hass, self._component.id, "value_entity")
        if value_entity is not None:
            value_entity.replace_battery()
