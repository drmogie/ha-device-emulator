"""Fake light platform - one light per Light component, every capability.

Brightness, color temperature, and full RGB color are all supported at
once, switching color_mode based on whichever command was last used -
like a real "White and Color Ambiance" bulb. No show-as picker; this is
the only light variant.
"""
from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_LIGHT, components_for, device_info_for
from .mixins import FakeEntityMixin

EFFECT_LIST = ["none", "colorloop", "random"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake light for each Light component on this device."""
    async_add_entities(
        FakeLight(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_LIGHT
    )


class FakeLight(FakeEntityMixin, LightEntity, RestoreEntity):
    """A simulated light with brightness, color temp, and RGB color."""

    _attr_has_entity_name = True
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP, ColorMode.HS}
    _attr_effect_list = EFFECT_LIST
    _attr_min_color_temp_kelvin = 2000
    _attr_max_color_temp_kelvin = 6500

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label  # None unless this device has more than one
        self._attr_unique_id = f"{component.id}_light"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_color_mode = ColorMode.COLOR_TEMP
        self._attr_is_on = False
        self._attr_brightness = 180
        self._attr_color_temp_kelvin = 3300
        self._attr_hs_color = (27.0, 85.0)  # warm amber default
        self._attr_effect = "none"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == "on"
            attrs = last_state.attributes
            self._attr_brightness = attrs.get(ATTR_BRIGHTNESS, self._attr_brightness)
            self._attr_color_temp_kelvin = attrs.get(
                ATTR_COLOR_TEMP_KELVIN, self._attr_color_temp_kelvin
            )
            hs_color = attrs.get(ATTR_HS_COLOR)
            if hs_color is not None:
                self._attr_hs_color = tuple(hs_color)
            self._attr_effect = attrs.get(ATTR_EFFECT, self._attr_effect)
            color_mode = attrs.get("color_mode")
            if color_mode in self._attr_supported_color_modes:
                self._attr_color_mode = color_mode

    async def async_turn_on(self, **kwargs) -> None:
        self._attr_is_on = True
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            self._attr_color_temp_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            self._attr_color_mode = ColorMode.COLOR_TEMP
        if ATTR_HS_COLOR in kwargs:
            self._attr_hs_color = kwargs[ATTR_HS_COLOR]
            self._attr_color_mode = ColorMode.HS
        if ATTR_EFFECT in kwargs:
            self._attr_effect = kwargs[ATTR_EFFECT]
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
