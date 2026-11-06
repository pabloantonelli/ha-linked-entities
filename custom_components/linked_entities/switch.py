"""Switch entities for Linked Entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import LinkedEntitiesConfigEntry
from .entity import LinkedEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LinkedEntitiesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the link switches."""
    async_add_entities([LinkGroupSwitch(entry), LinkSyncSwitch(entry)])


class LinkGroupSwitch(LinkedEntity, SwitchEntity):
    """One switch that represents (and controls) the whole link."""

    _attr_name = None  # use the device name, e.g. switch.luces_quincho
    _attr_translation_key = "group"

    def __init__(self, entry: LinkedEntitiesConfigEntry) -> None:
        """Initialise the switch."""
        super().__init__(entry, "group")

    @property
    def available(self) -> bool:
        """Available once at least one member reports on/off."""
        return self.group.is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return the group state."""
        return self.group.is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the linked entities."""
        return {
            "entity_id": self.group.members,
            "triggers": self.group.triggers,
            "primary": self.group.primary,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn every member on."""
        await self.group.async_turn(True, self.entity_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn every member off."""
        await self.group.async_turn(False, self.entity_id)


class LinkSyncSwitch(LinkedEntity, SwitchEntity, RestoreEntity):
    """Pause/resume synchronisation for the link."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "sync_enabled"

    def __init__(self, entry: LinkedEntitiesConfigEntry) -> None:
        """Initialise the switch."""
        super().__init__(entry, "sync_enabled")

    async def async_added_to_hass(self) -> None:
        """Restore the previous state."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self.group.sync_enabled = last.state != STATE_OFF

    @property
    def is_on(self) -> bool:
        """Return whether sync is enabled."""
        return self.group.sync_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Resume synchronisation."""
        self.group.async_set_sync_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Pause synchronisation."""
        self.group.async_set_sync_enabled(False)
