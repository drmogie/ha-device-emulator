"""Fake alarm control panel platform - one entity per Alarm component.

Supports home/away/night/vacation/custom-bypass arming, each with a
simulated exit delay before it actually arms. A hidden "Simulate breach"
switch (see switch.py) lets you trip it for testing: tripping while
armed starts an entry delay countdown (state PENDING), then TRIGGERED if
not disarmed in time - and disarming silences it and resets the switch,
just like clearing a real panel.
"""
from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity

from .const import Component, DEVICE_TYPE_ALARM, components_for, device_info_for
from .helpers import get_switch_entity, register_switch_listener
from .mixins import FakeEntityMixin

EXIT_DELAY = 10
ENTRY_DELAY = 10

ARMED_STATES = {
    AlarmControlPanelState.ARMED_HOME,
    AlarmControlPanelState.ARMED_AWAY,
    AlarmControlPanelState.ARMED_NIGHT,
    AlarmControlPanelState.ARMED_VACATION,
    AlarmControlPanelState.ARMED_CUSTOM_BYPASS,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a fake alarm control panel for each Alarm component."""
    async_add_entities(
        FakeAlarmPanel(c) for c in components_for(entry) if c.device_type == DEVICE_TYPE_ALARM
    )


class FakeAlarmPanel(FakeEntityMixin, AlarmControlPanelEntity, RestoreEntity):
    """A simulated security panel with exit/entry delays."""

    _attr_has_entity_name = True
    _attr_code_arm_required = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
        | AlarmControlPanelEntityFeature.ARM_VACATION
        | AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS
    )

    def __init__(self, component: Component) -> None:
        self._component = component
        self._entry = component.entry
        self._attr_name = component.label
        self._attr_unique_id = f"{component.id}_alarm"
        self._attr_device_info = device_info_for(component.entry)
        self._attr_alarm_state = AlarmControlPanelState.DISARMED
        self._pending_target: AlarmControlPanelState | None = None
        self._pending_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._register_for_status_updates()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in [s.value for s in AlarmControlPanelState]:
                # Never restore into a mid-transition state.
                if last_state.state not in (
                    AlarmControlPanelState.ARMING,
                    AlarmControlPanelState.PENDING,
                    AlarmControlPanelState.DISARMING,
                ):
                    self._attr_alarm_state = AlarmControlPanelState(last_state.state)

        self.async_on_remove(
            register_switch_listener(
                self.hass, self._component.id, self._handle_breach
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_pending()

    def _cancel_pending(self) -> None:
        if self._pending_timer:
            self._pending_timer()
            self._pending_timer = None

    async def _start_arming(self, target: AlarmControlPanelState) -> None:
        self._cancel_pending()
        self._pending_target = target
        self._attr_alarm_state = AlarmControlPanelState.ARMING
        self.async_write_ha_state()
        self._pending_timer = async_call_later(self.hass, EXIT_DELAY, self._finish_arming)

    @callback
    def _finish_arming(self, now) -> None:
        self._pending_timer = None
        if self._pending_target is not None:
            self._attr_alarm_state = self._pending_target
            self.async_write_ha_state()

    @callback
    def _handle_breach(self, is_on: bool) -> None:
        if is_on:
            if self._attr_alarm_state in ARMED_STATES:
                self._pending_target = self._attr_alarm_state
                self._attr_alarm_state = AlarmControlPanelState.PENDING
                self.async_write_ha_state()
                self._pending_timer = async_call_later(
                    self.hass, ENTRY_DELAY, self._finish_triggering
                )
        else:
            if self._attr_alarm_state in (
                AlarmControlPanelState.PENDING,
                AlarmControlPanelState.TRIGGERED,
            ):
                self._cancel_pending()
                self._attr_alarm_state = self._pending_target or AlarmControlPanelState.DISARMED
                self.async_write_ha_state()

    @callback
    def _finish_triggering(self, now) -> None:
        self._pending_timer = None
        self._attr_alarm_state = AlarmControlPanelState.TRIGGERED
        self.async_write_ha_state()

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        self._cancel_pending()
        self._pending_target = None
        self._attr_alarm_state = AlarmControlPanelState.DISARMED
        self.async_write_ha_state()
        switch_entity = get_switch_entity(self.hass, self._component.id)
        if switch_entity is not None and switch_entity.is_on:
            await switch_entity.async_turn_off()

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self._start_arming(AlarmControlPanelState.ARMED_HOME)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self._start_arming(AlarmControlPanelState.ARMED_AWAY)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        await self._start_arming(AlarmControlPanelState.ARMED_NIGHT)

    async def async_alarm_arm_vacation(self, code: str | None = None) -> None:
        await self._start_arming(AlarmControlPanelState.ARMED_VACATION)

    async def async_alarm_arm_custom_bypass(self, code: str | None = None) -> None:
        await self._start_arming(AlarmControlPanelState.ARMED_CUSTOM_BYPASS)
