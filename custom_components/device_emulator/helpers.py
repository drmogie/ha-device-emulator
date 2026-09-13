"""Shared helpers for linking sibling entities within a config entry.

Some device types are really two entities that need to agree with each
other - a plug's switch and its power sensor, or a motion/door sensor and
its hidden "simulate" switch. Looking a sibling up through the entity
registry at `async_added_to_hass` time is racy: platforms for the same
config entry are set up concurrently, so there's no guarantee the switch
has registered itself yet when the sensor goes looking for it - and if it
hasn't, the link never forms and toggling the switch silently does
nothing.

Instead, the switch entity registers itself directly in hass.data, and
publishes its state to a listener list whenever it changes. Sensors
subscribe to that list. Whoever sets up first, the link always forms:
if the switch is already there, a new subscriber is called immediately
with its current state; if not, it just waits in the listener list until
the switch shows up and publishes.
"""
from __future__ import annotations

from typing import Callable

from homeassistant.core import HomeAssistant

from .const import DOMAIN


def _entry_data(hass: HomeAssistant, entry_id: str) -> dict:
    return hass.data.setdefault(DOMAIN, {}).setdefault(entry_id, {})


STATE_OVERRIDE_NORMAL = "Normal"
STATE_OVERRIDE_UNAVAILABLE = "Unavailable"
STATE_OVERRIDE_UNKNOWN = "Unknown"
STATE_OVERRIDE_OPTIONS = [STATE_OVERRIDE_NORMAL, STATE_OVERRIDE_UNAVAILABLE, STATE_OVERRIDE_UNKNOWN]


def get_state_override(hass: HomeAssistant, entry_id: str) -> str:
    """Return the current forced-state option for this device."""
    return _entry_data(hass, entry_id).get("state_override", STATE_OVERRIDE_NORMAL)


def register_status_entity(hass: HomeAssistant, entry_id: str, entity) -> None:
    """Track an entity so it can be force-refreshed instantly.

    FakeEntityMixin's `available`/`state` overrides are pull-based - they
    check the live override on every read, so they're always correct
    eventually (e.g. after a restart or the next poll). Registering here
    just makes the change happen the instant the select is changed,
    instead of waiting for that next poll cycle.
    """
    _entry_data(hass, entry_id).setdefault("status_entities", []).append(entity)


def set_state_override(hass: HomeAssistant, entry_id: str, option: str) -> None:
    """Set the forced-state option for this device.

    Every FakeEntityMixin-based entity on this config entry checks this
    on every state write. Refreshing each registered entity here makes
    that take effect immediately rather than at the next poll.
    """
    _entry_data(hass, entry_id)["state_override"] = option
    for entity in list(_entry_data(hass, entry_id).get("status_entities", [])):
        entity.async_write_ha_state()


def get_weather_override(hass: HomeAssistant, component_id: str) -> str | None:
    """Return the forced condition for this weather component, or None for auto.

    The "Weather condition" select is the sole source of truth for this -
    it owns the value and is the one that restores it across restarts.
    The weather entity itself just reads this live on every state/
    forecast computation instead of keeping its own separately-restored
    copy of the same thing. Two independent copies of one value, each
    restored by a different entity with no guaranteed setup order, is
    exactly how the override used to get lost or go stale; reading one
    shared value removes that failure mode entirely.
    """
    return _entry_data(hass, component_id).get("weather_override")


def set_weather_override(hass: HomeAssistant, component_id: str, condition: str | None) -> None:
    """Set (None for auto) the forced condition for this weather component.

    Refreshes the weather entity immediately if it's already set up - the
    same immediate-refresh reason set_state_override refreshes
    status_entities - otherwise the change wouldn't be visible until the
    entity's next 15-minute tick.
    """
    _entry_data(hass, component_id)["weather_override"] = condition
    weather_entity = _entry_data(hass, component_id).get("weather_entity")
    if weather_entity is not None:
        weather_entity.async_write_ha_state()


def set_entity(hass: HomeAssistant, entry_id: str, key: str, entity) -> None:
    """Register any entity under an arbitrary key for this config entry.

    General-purpose version of set_switch_entity, for sibling entities
    that need to reach each other directly - e.g. a battery sensor
    reading its vacuum, or a button bumping its update entity's version.
    """
    _entry_data(hass, entry_id)[key] = entity


def get_entity(hass: HomeAssistant, entry_id: str, key: str):
    """Return the entity registered under `key` for this config entry, if any."""
    return _entry_data(hass, entry_id).get(key)


def set_switch_entity(hass: HomeAssistant, entry_id: str, entity) -> None:
    """Register the switch entity for this config entry."""
    _entry_data(hass, entry_id)["switch_entity"] = entity


def get_switch_entity(hass: HomeAssistant, entry_id: str):
    """Return the switch entity for this config entry, if it's set up."""
    return _entry_data(hass, entry_id).get("switch_entity")


def publish_switch_state(hass: HomeAssistant, entry_id: str, is_on: bool) -> None:
    """Notify every subscriber that the switch's state changed."""
    for listener in list(_entry_data(hass, entry_id).get("switch_listeners", [])):
        listener(is_on)


def step_toward(current: float, target: float, step: float) -> float:
    """Move `current` toward `target` by at most `step`, without overshooting.

    Shared by anything that animates a 0-100 position over time - covers
    and valves - so opening/closing takes realistic time instead of
    jumping straight to the requested position.
    """
    if current < target:
        return min(current + step, target)
    if current > target:
        return max(current - step, target)
    return current


def register_switch_listener(
    hass: HomeAssistant, entry_id: str, listener: Callable[[bool], None]
) -> Callable[[], None]:
    """Subscribe to the switch's state, regardless of setup order.

    If the switch has already registered itself, the listener is called
    immediately with its current state. Returns an unsubscribe function.
    """
    entry_data = _entry_data(hass, entry_id)
    listeners = entry_data.setdefault("switch_listeners", [])
    listeners.append(listener)

    switch_entity = entry_data.get("switch_entity")
    if switch_entity is not None:
        listener(switch_entity.is_on)

    def _unsubscribe() -> None:
        if listener in listeners:
            listeners.remove(listener)

    return _unsubscribe
