"""Linked Entities: keep switches, lights and buttons mirroring each other."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import LinkedEntitiesConfigEntry, LinkGroup

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: LinkedEntitiesConfigEntry) -> bool:
    """Set up a link from a config entry."""
    group = LinkGroup(hass, entry)
    entry.runtime_data = group
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Start after the entities exist so the restored "sync enabled" state applies.
    group.async_start()
    entry.async_on_unload(group.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LinkedEntitiesConfigEntry) -> bool:
    """Unload a link."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: LinkedEntitiesConfigEntry
) -> None:
    """Reload the link when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
