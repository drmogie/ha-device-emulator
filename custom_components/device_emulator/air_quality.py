"""Fake air_quality platform - one entity per Air Quality component.

This domain is legacy in Home Assistant - most modern integrations
report air quality as regular sensor entities with an air-quality
device_class instead - but it's still fully functional, so it's
included as its own device type. Its value is set directly by the
paired hidden "PM2.5" number control (see number.py), the same
"set it and it holds" pattern as the standalone Sensor device type.
"""
from __future__ import annotations

from homeassistant.components.air_quality import AirQualityEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_AIR_QUALITY, components_for, device_info_for
from .helpers import set_entity
from .mixins import FakeEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake air quality station for each Air Quality component."""
    async_add_entities(
        FakeAirQuality(c)
        for c in components_for(entry)
        if c.device_type == DEVICE_TYPE_AIR_QUALITY
    )


class FakeAirQuality(FakeEntityMixin, AirQualityEntity, RestoreEntity):
    """A simulated air quality station reporting PM2.5."""

    _attr_has_entity_name = True

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_air_quality"
        self._attr_device_info = device_info_for(component.entry)
        self._pm25 = 12.0

    @property
    def particulate_matter_2_5(self):
        return self._pm25

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        set_entity(self.hass, self._component.id, "air_quality_entity", self)
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._pm25 = float(last_state.state)
            except (TypeError, ValueError):
                pass

    @callback
    def set_pm25(self, value: float) -> None:
        """Called by the hidden 'PM2.5' number control."""
        self._pm25 = value
        self.async_write_ha_state()
