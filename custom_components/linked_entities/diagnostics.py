"""Diagnostics for Linked Entities."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import LinkedEntitiesConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: LinkedEntitiesConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a link."""
    return {"title": entry.title, "options": dict(entry.options), "group": entry.runtime_data.as_dict()}
