"""Fixtures for Linked Entities tests."""

from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.linked_entities.const import (
    CONF_DEBOUNCE_MS,
    CONF_EVENT_TYPES,
    CONF_MEMBERS,
    CONF_PRIMARY,
    CONF_TRIGGERS,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in every test."""
    return


@pytest.fixture
async def booleans(hass: HomeAssistant) -> None:
    """Create input_boolean.a/b/c and input_button.btn as fake devices."""
    assert await async_setup_component(
        hass,
        "input_boolean",
        {"input_boolean": {"a": {"name": "A"}, "b": {"name": "B"}, "c": {"name": "C"}}},
    )
    assert await async_setup_component(
        hass, "input_button", {"input_button": {"btn": {"name": "Btn"}}}
    )
    await hass.async_block_till_done()


@pytest.fixture
def make_entry(hass: HomeAssistant):
    """Return a factory that sets up a link entry."""

    async def _make(
        members=("input_boolean.a", "input_boolean.b"),
        triggers=(),
        primary=None,
        debounce_ms=0,
        event_types=(),
        title="Test link",
    ) -> MockConfigEntry:
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=title,
            data={},
            options={
                CONF_MEMBERS: list(members),
                CONF_TRIGGERS: list(triggers),
                CONF_PRIMARY: primary,
                CONF_DEBOUNCE_MS: debounce_ms,
                CONF_EVENT_TYPES: list(event_types),
            },
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _make
