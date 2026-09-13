"""The Device Emulator integration.

Each config entry is one simulated device, made up of one or more
"components" (see const.py's Component) - the entity type(s) chosen when
the device was created, plus anything added afterward through the
device's "Configure" option. platforms_for_entry() works out which
entity platforms the whole set of components needs.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_COMPONENTS, DOMAIN, MANUFACTURER, platforms_for_entry


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Device Emulator config entry (i.e. one simulated device)."""
    platforms = platforms_for_entry(entry)

    hass.data.setdefault(DOMAIN, {})
    # Remember exactly which platforms we forwarded, so async_unload_entry
    # can unload precisely those - NOT a freshly recomputed list, since by
    # the time a reload actually tears down this setup (e.g. after
    # "Configure" adds a component), entry.data already reflects the NEW
    # component set, which would include platforms that were never
    # actually forwarded for the setup being torn down.
    hass.data[DOMAIN][entry.entry_id] = {"platforms": platforms}

    if not entry.data.get(CONF_COMPONENTS):
        # A container with no components yet has no entity to carry a
        # DeviceInfo, so register its device directly - otherwise nothing
        # would ever give it its chosen name, and entities added to it
        # later via "Configure" would have nothing to attach to.
        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model="Empty Device",
        )

    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Device Emulator config entry."""
    platforms = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("platforms")
    if platforms is None:
        # Fallback for entries whose setup didn't run in this process
        # (shouldn't normally happen - setup always runs before unload).
        platforms = platforms_for_entry(entry)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
