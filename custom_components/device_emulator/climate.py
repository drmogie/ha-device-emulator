"""Fake thermostat platform - one climate entity per Climate component.

Heat, cool, heat/cool (range), and fan-only modes; fan speed; presets.
current_temperature drifts toward whatever the active mode calls for, or
can be set directly via the paired hidden number (see number.py).
"""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_NONE,
    PRESET_SLEEP,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_CLIMATE, components_for, device_info_for
from .helpers import set_entity
from .mixins import FakeEntityMixin

UPDATE_INTERVAL = timedelta(seconds=30)
AMBIENT_TEMP = 65.0
DRIFT_PER_TICK = 0.15
TOLERANCE = 0.3

FAN_MODES = ["auto", "low", "medium", "high"]

# A preset relaxes how hard the system tries to hit its target, by
# widening the gap it will tolerate before calling for heat/cool.
PRESET_OFFSETS = {
    PRESET_AWAY: 8.0,
    PRESET_ECO: 3.0,
    PRESET_SLEEP: 2.0,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake thermostat for each Climate component on this device."""
    async_add_entities(
        FakeThermostat(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_CLIMATE
    )


class FakeThermostat(FakeEntityMixin, ClimateEntity, RestoreEntity):
    """A simulated heat/cool thermostat."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.HEAT_COOL,
        HVACMode.FAN_ONLY,
    ]
    _attr_preset_modes = [
        PRESET_NONE,
        PRESET_HOME,
        PRESET_AWAY,
        PRESET_ECO,
        PRESET_SLEEP,
    ]
    _attr_fan_modes = FAN_MODES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_min_temp = 60
    _attr_max_temp = 90
    _attr_target_temperature_step = 0.5

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_climate"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_hvac_mode = HVACMode.HEAT
        self._attr_preset_mode = PRESET_NONE
        self._attr_fan_mode = "auto"
        self._attr_target_temperature = 70.0
        self._attr_target_temperature_high = 76.0
        self._attr_target_temperature_low = 68.0
        self._attr_current_temperature = 68.0
        self._remove_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        set_entity(self.hass, self._component.id, "climate_entity", self)

        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in [mode.value for mode in self._attr_hvac_modes]:
                self._attr_hvac_mode = HVACMode(last_state.state)
            attrs = last_state.attributes
            self._attr_target_temperature = attrs.get(
                ATTR_TEMPERATURE, self._attr_target_temperature
            )
            self._attr_target_temperature_high = attrs.get(
                "target_temp_high", self._attr_target_temperature_high
            )
            self._attr_target_temperature_low = attrs.get(
                "target_temp_low", self._attr_target_temperature_low
            )
            self._attr_current_temperature = attrs.get(
                "current_temperature", self._attr_current_temperature
            )
            self._attr_preset_mode = attrs.get("preset_mode", self._attr_preset_mode)
            self._attr_fan_mode = attrs.get("fan_mode", self._attr_fan_mode)

        self._remove_timer = async_track_time_interval(
            self.hass, self._simulate_temperature, UPDATE_INTERVAL
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_timer:
            self._remove_timer()

    def _offset(self) -> float:
        return PRESET_OFFSETS.get(self._attr_preset_mode, 0.0)

    def _effective_single_target(self) -> float:
        offset = self._offset()
        if self._attr_hvac_mode == HVACMode.COOL:
            return self._attr_target_temperature + offset
        return self._attr_target_temperature - offset

    def _effective_low(self) -> float:
        return self._attr_target_temperature_low - self._offset()

    def _effective_high(self) -> float:
        return self._attr_target_temperature_high + self._offset()

    @property
    def hvac_action(self) -> HVACAction:
        """Report heating/cooling/idle/fan/off based on mode and target."""
        mode = self._attr_hvac_mode
        if mode == HVACMode.OFF:
            return HVACAction.OFF
        if mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN

        current = self._attr_current_temperature

        if mode == HVACMode.HEAT:
            target = self._effective_single_target()
            return HVACAction.HEATING if current < target - TOLERANCE else HVACAction.IDLE

        if mode == HVACMode.COOL:
            target = self._effective_single_target()
            return HVACAction.COOLING if current > target + TOLERANCE else HVACAction.IDLE

        if mode == HVACMode.HEAT_COOL:
            low = self._effective_low()
            high = self._effective_high()
            if current < low - TOLERANCE:
                return HVACAction.HEATING
            if current > high + TOLERANCE:
                return HVACAction.COOLING
            return HVACAction.IDLE

        return HVACAction.IDLE

    @callback
    def _simulate_temperature(self, now) -> None:
        current = self._attr_current_temperature
        action = self.hvac_action

        if action == HVACAction.HEATING:
            current = min(current + DRIFT_PER_TICK, self._attr_max_temp)
        elif action == HVACAction.COOLING:
            current = max(current - DRIFT_PER_TICK, self._attr_min_temp)
        elif current > AMBIENT_TEMP:
            current = max(current - (DRIFT_PER_TICK / 2), AMBIENT_TEMP)
        elif current < AMBIENT_TEMP:
            current = min(current + (DRIFT_PER_TICK / 2), AMBIENT_TEMP)

        self._attr_current_temperature = round(current, 1)
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        changed = False
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._attr_target_temperature = temperature
            changed = True
        if (high := kwargs.get(ATTR_TARGET_TEMP_HIGH)) is not None:
            self._attr_target_temperature_high = high
            changed = True
        if (low := kwargs.get(ATTR_TARGET_TEMP_LOW)) is not None:
            self._attr_target_temperature_low = low
            changed = True
        if changed:
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        self._attr_preset_mode = preset_mode
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        self._attr_fan_mode = fan_mode
        self.async_write_ha_state()

    def set_current_temperature(self, value: float) -> None:
        """Called by the hidden 'Current temperature' number (see number.py)."""
        self._attr_current_temperature = value
        self.async_write_ha_state()
