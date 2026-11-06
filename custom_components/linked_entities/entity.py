"""Base entity for Linked Entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .coordinator import LinkedEntitiesConfigEntry, LinkGroup


class LinkedEntity(Entity):
    """Entity attached to a link group's device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: LinkedEntitiesConfigEntry, key: str) -> None:
        """Initialise the entity."""
        self.group: LinkGroup = entry.runtime_data
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Linked Entities",
            model="Link group",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to group updates."""
        await super().async_added_to_hass()
        self.async_on_remove(self.group.async_add_listener(self.async_write_ha_state))
