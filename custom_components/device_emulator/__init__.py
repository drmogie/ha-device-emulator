"""The Device Emulator integration.

Creates virtual/fake devices (light, switch, sensor, binary_sensor) with no
real hardware behind them, for testing dashboards and automations. Each
config entry represents one emulated device.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_TYPE, DOMAIN, PLATFORMS_BY_TYPE


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Device Emulator from a config entry."""
    device_type = entry.data.get(CONF_DEVICE_TYPE)
    platforms = PLATFORMS_BY_TYPE.get(device_type, [])
    if not platforms:
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"device_type": device_type}

    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    device_type = entry.data.get(CONF_DEVICE_TYPE)
    platforms = PLATFORMS_BY_TYPE.get(device_type, [])

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    return unload_ok
