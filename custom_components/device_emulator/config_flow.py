"""Config flow for the Device Emulator integration.

Adding an emulated device is fully GUI-driven: Settings > Devices & Services
> Add Integration > Device Emulator. Step 1 picks a name and device type;
step 2 asks for the extra options relevant to that type.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DEVICE_CLASS,
    CONF_DEVICE_TYPE,
    CONF_INITIAL_STATE,
    CONF_INITIAL_VALUE,
    CONF_UNIT_OF_MEASUREMENT,
    DEVICE_TYPE_BINARY_SENSOR,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPES,
    DOMAIN,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_DEVICE_TYPE, default="light"): vol.In(DEVICE_TYPES),
    }
)


class DeviceEmulatorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Device Emulator."""

    VERSION = 1

    def __init__(self) -> None:
        self._name: str | None = None
        self._device_type: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """First step: name and device type."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._name = user_input[CONF_NAME]
            self._device_type = user_input[CONF_DEVICE_TYPE]
            return await self.async_step_configure()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_configure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Second step: options specific to the chosen device type."""
        if user_input is not None:
            data = {
                CONF_NAME: self._name,
                CONF_DEVICE_TYPE: self._device_type,
                **user_input,
            }
            return self.async_create_entry(title=self._name, data=data)

        schema = self._schema_for_device_type(self._device_type)
        return self.async_show_form(step_id="configure", data_schema=schema)

    @staticmethod
    def _schema_for_device_type(device_type: str | None) -> vol.Schema:
        if device_type == DEVICE_TYPE_SENSOR:
            return vol.Schema(
                {
                    vol.Optional(CONF_DEVICE_CLASS, default=""): str,
                    vol.Optional(CONF_UNIT_OF_MEASUREMENT, default=""): str,
                    vol.Optional(CONF_INITIAL_VALUE, default="0"): str,
                }
            )
        if device_type == DEVICE_TYPE_BINARY_SENSOR:
            return vol.Schema(
                {
                    vol.Optional(CONF_DEVICE_CLASS, default=""): str,
                    vol.Optional(CONF_INITIAL_STATE, default=False): bool,
                }
            )
        # light, switch
        return vol.Schema(
            {
                vol.Optional(CONF_INITIAL_STATE, default=False): bool,
            }
        )
