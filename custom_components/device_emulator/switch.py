"""Fake switch platform.

Covers four roles that all boil down to "a thing that's on or off," one
switch per matching component on this device:
  - Switch component: the primary switch entity (shown as a plain switch
    or an outlet - an outlet also gets a paired power sensor, see
    sensor.py).
  - Binary Sensor component: a hidden "simulate" trigger switch.
  - Alarm Control Panel component: a hidden "simulate breach" switch.
  - Sensor component shown as Battery: a hidden "Charging" switch.

This is also the entity that publishes its state for sibling entities to
react to - see helpers.py. Each switch is keyed by its own component's
id, so two of the same kind on one composed device never cross-wire.
"""
from __future__ import annotations

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    BINARY_SENSOR_TRIGGER_LABELS,
    Component,
    DEVICE_TYPE_ALARM,
    DEVICE_TYPE_BINARY_SENSOR,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_SWITCH,
    components_for,
    device_info_for,
)
from .helpers import publish_switch_state, set_switch_entity
from .mixins import FakeEntityMixin

TRIGGER_TYPES = (DEVICE_TYPE_BINARY_SENSOR, DEVICE_TYPE_ALARM, DEVICE_TYPE_SENSOR)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake switch for each component on this device that needs one."""
    entities = []
    for component in components_for(entry):
        if component.device_type == DEVICE_TYPE_SWITCH:
            entities.append(FakeSwitch(component))
        elif component.device_type == DEVICE_TYPE_BINARY_SENSOR:
            entities.append(FakeSwitch(component))
        elif component.device_type == DEVICE_TYPE_ALARM:
            entities.append(FakeSwitch(component))
        elif component.device_type == DEVICE_TYPE_SENSOR and component.show_as == "battery":
            entities.append(FakeSwitch(component))
    async_add_entities(entities)


class FakeSwitch(FakeEntityMixin, SwitchEntity, RestoreEntity):
    """A simulated switch/outlet, or a hidden trigger control."""

    _attr_has_entity_name = True

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        device_type = component.device_type
        is_outlet = component.show_as == "outlet"
        is_trigger = device_type in TRIGGER_TYPES

        self._attr_unique_id = f"{component.id}_switch"
        self._attr_is_on = False

        if is_trigger:
            # This is a helper control, not the "real" reported entity -
            # keep it out of the way in the Config section of the device.
            self._attr_entity_category = EntityCategory.CONFIG
            if device_type == DEVICE_TYPE_BINARY_SENSOR:
                self._attr_name = BINARY_SENSOR_TRIGGER_LABELS.get(
                    component.show_as, "Simulate trip"
                )
                self._attr_icon = "mdi:radar"
            elif device_type == DEVICE_TYPE_SENSOR:
                self._attr_name = "Charging"
                self._attr_icon = "mdi:battery-charging"
            else:
                self._attr_name = "Simulate breach"
                self._attr_icon = "mdi:shield-alert"
        else:
            self._attr_name = component.label  # None unless there's more than one
            self._attr_device_class = (
                SwitchDeviceClass.OUTLET if is_outlet else SwitchDeviceClass.SWITCH
            )

        self._attr_device_info = device_info_for(component.entry)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == "on"

        # Make ourselves discoverable to sibling entities of THIS
        # component specifically (power sensor, binary_sensor, alarm
        # panel, battery sensor) and announce our restored state.
        set_switch_entity(self.hass, self._component.id, self)
        publish_switch_state(self.hass, self._component.id, self._attr_is_on)

    async def async_turn_on(self, **kwargs) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()
        publish_switch_state(self.hass, self._component.id, True)

    async def async_turn_off(self, **kwargs) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
        publish_switch_state(self.hass, self._component.id, False)
