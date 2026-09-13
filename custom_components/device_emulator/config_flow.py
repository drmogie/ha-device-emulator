"""Config flow for the Device Emulator integration.

Two flows share the "pick a domain, then show-as, then image source"
steps (via _ComponentStepsMixin):

  - The main "Add integration" flow (DeviceEmulatorConfigFlow) either
    creates a new device with this as its first component, or - if you
    pick an existing device in its "target" step - adds this as a new
    component onto that device instead, aborting without creating a
    duplicate entry.
  - Each device's "Configure" option (DeviceEmulatorOptionsFlow) lets you
    add another component onto that device (the same thing as the
    "target" step above, just reached directly from a device you're
    already looking at), or remove one you added before - removing a
    component also removes every entity tied to it (a battery sensor's
    hidden Charging switch, Charging binary_sensor, and Replace battery
    button all disappear along with it), since they're only ever created
    alongside that same component in the first place.

Either way, building a composed device (e.g. a Temperature sensor, a
Humidity sensor, and a Battery sensor all on one "Temperature/Humidity"
device) never creates more than one config entry - it's the same entry
gaining (or losing) components, not new entries attached to each other.
"""
from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    ADDABLE_DEVICE_TYPE_LABELS,
    CONF_COMPONENT_ID,
    CONF_COMPONENTS,
    CONF_DEVICE_TYPE,
    CONF_IMAGE_SOURCE,
    CONF_SHOW_AS,
    DEVICE_TYPE_LABELS,
    DOMAIN,
    IMAGE_SOURCE_TYPES,
    SHOW_AS_OPTIONS,
    components_for,
    suggested_name,
)

NEW_DEVICE_OPTION = "Create a new device"
_TARGET_ENTRY_ID = "target_entry_id"  # transient flow key, never stored on the entry

ACTION_ADD = "add"
ACTION_REMOVE = "remove"


class _ComponentStepsMixin:
    """Shared "show as" / "image source" steps for both flows below."""

    _data: dict[str, Any]

    async def async_step_show_as(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask which device_class / capability set to show this domain as."""
        options = SHOW_AS_OPTIONS[self._data[CONF_DEVICE_TYPE]]

        if user_input is not None:
            self._data[CONF_SHOW_AS] = user_input[CONF_SHOW_AS]
            return await self._next_step()

        schema = vol.Schema(
            {
                vol.Required(CONF_SHOW_AS, default=options[0]["value"]): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                )
            }
        )
        return self.async_show_form(step_id="show_as", data_schema=schema)

    async def async_step_image_source(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for the image URL or /local/ path to serve."""
        if user_input is not None:
            self._data[CONF_IMAGE_SOURCE] = user_input[CONF_IMAGE_SOURCE]
            return await self._next_step()

        schema = vol.Schema({vol.Required(CONF_IMAGE_SOURCE): str})
        return self.async_show_form(step_id="image_source", data_schema=schema)

    def _build_component(self) -> dict[str, Any]:
        """Turn self._data into a component dict with a fresh unique id."""
        component: dict[str, Any] = {
            CONF_COMPONENT_ID: uuid.uuid4().hex[:12],
            CONF_DEVICE_TYPE: self._data[CONF_DEVICE_TYPE],
        }
        if CONF_SHOW_AS in self._data:
            component[CONF_SHOW_AS] = self._data[CONF_SHOW_AS]
        if CONF_IMAGE_SOURCE in self._data:
            component[CONF_IMAGE_SOURCE] = self._data[CONF_IMAGE_SOURCE]
        return component


class DeviceEmulatorConfigFlow(
    config_entries.ConfigFlow, _ComponentStepsMixin, domain=DOMAIN
):
    """Create a new emulated device with its first component."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask which Home Assistant domain to emulate."""
        if user_input is not None:
            self._data = dict(user_input)
            return await self._next_step()

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_TYPE): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": key, "label": label}
                            for key, label in DEVICE_TYPE_LABELS.items()
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_target(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask whether to create a new device or add onto an existing one."""
        if user_input is not None:
            selected = user_input[_TARGET_ENTRY_ID]
            self._data[_TARGET_ENTRY_ID] = None if selected == NEW_DEVICE_OPTION else selected
            if self._data[_TARGET_ENTRY_ID] is not None:
                return await self._finish()  # going onto an existing device - no name needed
            return await self._next_step()

        existing = self.hass.config_entries.async_entries(DOMAIN)
        options = [{"value": NEW_DEVICE_OPTION, "label": NEW_DEVICE_OPTION}] + [
            {"value": e.entry_id, "label": e.title} for e in existing
        ]
        schema = vol.Schema(
            {
                vol.Required(_TARGET_ENTRY_ID, default=NEW_DEVICE_OPTION): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                )
            }
        )
        return self.async_show_form(step_id="target", data_schema=schema)

    async def async_step_name(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Name the device, defaulting to something based on what was picked."""
        if user_input is not None:
            self._data["name"] = user_input["name"]
            return await self._finish()

        default = suggested_name(
            self._data[CONF_DEVICE_TYPE], self._data.get(CONF_SHOW_AS)
        )
        schema = vol.Schema({vol.Required("name", default=default): str})
        return self.async_show_form(step_id="name", data_schema=schema)

    async def _next_step(self) -> FlowResult:
        """Advance to whichever step this device type still needs."""
        device_type = self._data[CONF_DEVICE_TYPE]

        if device_type in SHOW_AS_OPTIONS and CONF_SHOW_AS not in self._data:
            return await self.async_step_show_as()

        if device_type in IMAGE_SOURCE_TYPES and CONF_IMAGE_SOURCE not in self._data:
            return await self.async_step_image_source()

        if _TARGET_ENTRY_ID not in self._data:
            return await self.async_step_target()

        return await self.async_step_name()

    async def _finish(self) -> FlowResult:
        target_entry_id = self._data.get(_TARGET_ENTRY_ID)

        if target_entry_id:
            # Add this as a new component onto an existing device - the
            # same thing that device's own "Configure" option does, just
            # reachable from "Add integration" too. No new entry, no
            # entity-registry juggling - just one more item in the
            # target's own component list, exactly as if that device had
            # been updated with a new capability.
            target_entry = self.hass.config_entries.async_get_entry(target_entry_id)
            updated_components = [
                *target_entry.data.get(CONF_COMPONENTS, []),
                self._build_component(),
            ]
            return self.async_update_reload_and_abort(
                target_entry,
                data={**target_entry.data, CONF_COMPONENTS: updated_components},
                reason="added_to_device",
            )

        device_type = self._data[CONF_DEVICE_TYPE]
        show_as = self._data.get(CONF_SHOW_AS)
        slug = self._data["name"].strip().lower().replace(" ", "_")
        parts = [device_type, show_as or "", slug]
        await self.async_set_unique_id("_".join(part for part in parts if part))
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=self._data["name"], data={CONF_COMPONENTS: [self._build_component()]}
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return DeviceEmulatorOptionsFlow()


class DeviceEmulatorOptionsFlow(_ComponentStepsMixin, config_entries.OptionsFlow):
    """"Configure" flow: add a component onto this device, or remove one."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose to add a new entity, or remove one that's already here."""
        components = components_for(self.config_entry)
        if not components:
            return await self.async_step_add()  # nothing to remove yet

        if user_input is not None:
            if user_input["action"] == ACTION_REMOVE:
                return await self.async_step_remove()
            return await self.async_step_add()

        schema = vol.Schema(
            {
                vol.Required("action", default=ACTION_ADD): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": ACTION_ADD, "label": "Add an entity"},
                            {"value": ACTION_REMOVE, "label": "Remove an entity"},
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_add(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask which domain to add to this device."""
        if user_input is not None:
            self._data = dict(user_input)
            return await self._next_step()

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_TYPE): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": key, "label": label}
                            for key, label in ADDABLE_DEVICE_TYPE_LABELS.items()
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="add", data_schema=schema)

    async def async_step_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask which existing entity to remove."""
        components = components_for(self.config_entry)
        options = [
            {
                "value": component.id,
                "label": component.label or DEVICE_TYPE_LABELS[component.device_type],
            }
            for component in components
        ]

        if user_input is not None:
            return await self._remove(user_input["component_id"])

        schema = vol.Schema(
            {
                vol.Required("component_id"): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                )
            }
        )
        return self.async_show_form(step_id="remove", data_schema=schema)

    async def _next_step(self) -> FlowResult:
        device_type = self._data[CONF_DEVICE_TYPE]

        if device_type in SHOW_AS_OPTIONS and CONF_SHOW_AS not in self._data:
            return await self.async_step_show_as()

        if device_type in IMAGE_SOURCE_TYPES and CONF_IMAGE_SOURCE not in self._data:
            return await self.async_step_image_source()

        return await self._finish()

    async def _finish(self) -> FlowResult:
        entry = self.config_entry
        new_component = self._build_component()
        updated_components = [*entry.data.get(CONF_COMPONENTS, []), new_component]

        self.hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_COMPONENTS: updated_components}
        )
        await self.hass.config_entries.async_reload(entry.entry_id)
        return self.async_create_entry(title="", data={})

    async def _remove(self, component_id: str) -> FlowResult:
        """Remove a component and every entity tied to its id."""
        entry = self.config_entry

        entity_registry = er.async_get(self.hass)
        prefix = f"{component_id}_"
        for entity_entry in er.async_entries_for_config_entry(
            entity_registry, entry.entry_id
        ):
            # Every entity for a component - the primary one and any
            # companions (a battery's Charging switch/binary_sensor/
            # button, an outlet's power sensor, ...) - shares this same
            # id as its unique_id prefix, since they're only ever created
            # alongside that one component in each platform's
            # async_setup_entry. Removing by prefix removes all of them
            # together, with nothing left orphaned.
            if entity_entry.unique_id.startswith(prefix):
                entity_registry.async_remove(entity_entry.entity_id)

        remaining = [
            c
            for c in entry.data.get(CONF_COMPONENTS, [])
            if c[CONF_COMPONENT_ID] != component_id
        ]
        self.hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_COMPONENTS: remaining}
        )
        await self.hass.config_entries.async_reload(entry.entry_id)
        return self.async_create_entry(title="", data={})
