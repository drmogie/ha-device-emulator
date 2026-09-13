"""Fake fan platform - percentage-only, no separate on/off toggle.

There's deliberately no turn_on/turn_off feature flag pairing beyond
what percentage implies - "off" is simply 0%, and turn_on/turn_off just
move the percentage, so there's no separate state to desync from the
slider. Also has oscillation, direction, and sleep/eco/turbo presets.
"""
from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_FAN, components_for, device_info_for
from .mixins import FakeEntityMixin

PRESET_MODES = ["sleep", "eco", "turbo"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake fan for each Fan component on this device."""
    async_add_entities(
        FakeFan(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_FAN
    )


class FakeFan(FakeEntityMixin, FanEntity, RestoreEntity):
    """A simulated variable-speed fan controlled only by percentage."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.OSCILLATE
        | FanEntityFeature.DIRECTION
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = 4
    _attr_preset_modes = PRESET_MODES

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_fan"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_percentage = 50
        self._attr_oscillating = False
        self._attr_current_direction = "forward"
        self._attr_preset_mode = None
        self._last_percentage = 50

    @property
    def is_on(self) -> bool:
        """Fan is on whenever its speed is above 0%."""
        return self._attr_percentage > 0

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            attrs = last_state.attributes
            self._attr_percentage = attrs.get("percentage", self._attr_percentage)
            self._attr_oscillating = attrs.get("oscillating", self._attr_oscillating)
            self._attr_current_direction = attrs.get(
                "direction", self._attr_current_direction
            )
            self._attr_preset_mode = attrs.get("preset_mode", self._attr_preset_mode)
            if self._attr_percentage:
                self._last_percentage = self._attr_percentage

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs
    ) -> None:
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
            return
        target = percentage if percentage is not None else (self._last_percentage or 100)
        await self.async_set_percentage(target)

    async def async_turn_off(self, **kwargs) -> None:
        if self._attr_percentage:
            self._last_percentage = self._attr_percentage
        self._attr_percentage = 0
        self._attr_preset_mode = None
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage > 0:
            self._last_percentage = percentage
        self._attr_percentage = percentage
        self._attr_preset_mode = None
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        self._attr_preset_mode = preset_mode
        if self._attr_percentage == 0:
            self._attr_percentage = self._last_percentage or 100
        self.async_write_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        self._attr_oscillating = oscillating
        self.async_write_ha_state()

    async def async_set_direction(self, direction: str) -> None:
        self._attr_current_direction = direction
        self.async_write_ha_state()
