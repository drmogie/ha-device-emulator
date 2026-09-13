"""Shared mixin: lets the hidden "Simulated status" select force any fake
entity into Unavailable or Unknown, for testing how dashboards and
automations handle those states.

This works the same way for every domain because it hooks the two
properties Home Assistant's core Entity class always checks before
writing a state, rather than each domain's own state-determining
attribute (is_on, native_value, activity, hvac_mode, ...):

- If `available` is False, HA always writes "unavailable" - full stop,
  regardless of what the domain-specific state would otherwise be.
- If `available` is True but `state` returns None, HA writes "unknown".

So a single mixin overriding just these two properties, deferring to the
real entity via `super()` otherwise, covers every platform in this
integration without needing per-domain special-casing.

IMPORTANT: FakeEntityMixin must be the FIRST base class on every entity
that uses it (e.g. `class FakeSwitch(FakeEntityMixin, SwitchEntity,
RestoreEntity)`), so its `available`/`state` take priority in the MRO
while `super()` still correctly reaches the real domain implementation.

Call `self._register_for_status_updates()` once in `async_added_to_hass`
so a status change takes effect the instant it's made, rather than
waiting for this entity's next poll cycle.
"""
from __future__ import annotations

from .helpers import (
    STATE_OVERRIDE_UNAVAILABLE,
    STATE_OVERRIDE_UNKNOWN,
    get_state_override,
    register_status_entity,
)


class FakeEntityMixin:
    """Mix in first to let a fake entity be forced into a test state."""

    def _register_for_status_updates(self) -> None:
        """Call from async_added_to_hass for instant status-change refresh."""
        register_status_entity(self.hass, self._entry.entry_id, self)

    @property
    def available(self) -> bool:  # type: ignore[override]
        if get_state_override(self.hass, self._entry.entry_id) == STATE_OVERRIDE_UNAVAILABLE:
            return False
        return super().available

    @property
    def state(self):  # type: ignore[override]
        if get_state_override(self.hass, self._entry.entry_id) == STATE_OVERRIDE_UNKNOWN:
            return None
        return super().state
