"""Fake siren platform - one entity per Siren component."""
from __future__ import annotations

from homeassistant.components.siren import (
    ATTR_DURATION,
    SirenEntity,
    SirenEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_SIREN, components_for, device_info_for
from .mixins import FakeEntityMixin


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake siren for each Siren component on this device."""
    async_add_entities(
        FakeSiren(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_SIREN
    )


class FakeSiren(FakeEntityMixin, SirenEntity, RestoreEntity):
    """A simulated siren/chime."""

    _attr_has_entity_name = True
    _attr_available_tones = ["chime", "alarm", "bell", "siren"]
    _attr_supported_features = (
        SirenEntityFeature.TURN_ON
        | SirenEntityFeature.TURN_OFF
        | SirenEntityFeature.TONES
        | SirenEntityFeature.VOLUME_SET
        | SirenEntityFeature.DURATION
    )

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_siren"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_is_on = False
        self._auto_off_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == "on"

    async def async_will_remove_from_hass(self) -> None:
        if self._auto_off_timer:
            self._auto_off_timer()

    async def async_turn_on(self, **kwargs) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()

        if self._auto_off_timer:
            self._auto_off_timer()
            self._auto_off_timer = None

        duration = kwargs.get(ATTR_DURATION)
        if duration:
            self._auto_off_timer = async_call_later(self.hass, duration, self._auto_off)

    async def async_turn_off(self, **kwargs) -> None:
        if self._auto_off_timer:
            self._auto_off_timer()
            self._auto_off_timer = None
        self._attr_is_on = False
        self.async_write_ha_state()

    @callback
    def _auto_off(self, now) -> None:
        self._auto_off_timer = None
        self._attr_is_on = False
        self.async_write_ha_state()
