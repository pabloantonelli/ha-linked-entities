"""Diagnostic sensor for Linked Entities."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LinkedEntitiesConfigEntry
from .entity import LinkedEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LinkedEntitiesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the diagnostic sensor."""
    async_add_entities([LastSourceSensor(entry)])


class LastSourceSensor(LinkedEntity, SensorEntity):
    """Which entity caused the last propagated change."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "last_source"

    def __init__(self, entry: LinkedEntitiesConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(entry, "last_source")

    @property
    def native_value(self) -> str | None:
        """Return the last source entity id."""
        return self.group.last_source
