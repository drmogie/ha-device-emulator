"""Fake humidifier / dehumidifier platform - one entity per component."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.humidifier import (
    MODE_AWAY,
    MODE_BOOST,
    MODE_ECO,
    MODE_NORMAL,
    MODE_SLEEP,
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_HUMIDIFIER, components_for, device_info_for
from .helpers import set_entity, step_toward
from .mixins import FakeEntityMixin

TICK = timedelta(seconds=30)
DRIFT_PER_TICK = 1.0
MODES = [MODE_NORMAL, MODE_AWAY, MODE_ECO, MODE_BOOST, MODE_SLEEP]

# Ambient baseline the humidity drifts toward while the device is off -
# a humidifier fights a naturally dry room, a dehumidifier fights a
# naturally humid one.
AMBIENT = {
    HumidifierDeviceClass.HUMIDIFIER: 35,
    HumidifierDeviceClass.DEHUMIDIFIER: 60,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake humidifier for each Humidifier component."""
    async_add_entities(
        FakeHumidifier(c)
        for c in components_for(entry)
        if c.device_type == DEVICE_TYPE_HUMIDIFIER
    )


class FakeHumidifier(FakeEntityMixin, HumidifierEntity, RestoreEntity):
    """A simulated humidifier or dehumidifier."""

    _attr_has_entity_name = True
    _attr_supported_features = HumidifierEntityFeature.MODES
    _attr_available_modes = MODES
    _attr_min_humidity = 30
    _attr_max_humidity = 80

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_device_class = (
            HumidifierDeviceClass.DEHUMIDIFIER
            if component.show_as == "dehumidifier"
            else HumidifierDeviceClass.HUMIDIFIER
        )
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_humidifier"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_is_on = False
        self._attr_mode = MODE_NORMAL
        self._attr_target_humidity = 45
        self._attr_current_humidity = 40
        self._remove_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        set_entity(self.hass, self._component.id, "humidifier_entity", self)

        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == "on"
            attrs = last_state.attributes
            self._attr_mode = attrs.get("mode", self._attr_mode)
            self._attr_target_humidity = attrs.get(
                "humidity", self._attr_target_humidity
            )
            self._attr_current_humidity = attrs.get(
                "current_humidity", self._attr_current_humidity
            )

        self._remove_timer = async_track_time_interval(self.hass, self._tick, TICK)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_timer:
            self._remove_timer()

    @callback
    def _tick(self, now) -> None:
        target = (
            self._attr_target_humidity
            if self._attr_is_on
            else AMBIENT[self._attr_device_class]
        )
        self._attr_current_humidity = round(
            step_toward(self._attr_current_humidity, target, DRIFT_PER_TICK)
        )
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_set_humidity(self, humidity: int) -> None:
        self._attr_target_humidity = humidity
        self.async_write_ha_state()

    async def async_set_mode(self, mode: str) -> None:
        self._attr_mode = mode
        self.async_write_ha_state()

    def set_current_humidity(self, value: float) -> None:
        """Called by the hidden 'Current humidity' number (see number.py)."""
        self._attr_current_humidity = value
        self.async_write_ha_state()
