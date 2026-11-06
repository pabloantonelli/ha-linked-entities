"""Tests for the config and options flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.linked_entities.const import DOMAIN


async def test_create_link(hass: HomeAssistant, booleans) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Luces quincho",
            "members": ["input_boolean.a", "input_boolean.b"],
            "triggers": [],
        },
    )
    assert result["step_id"] == "settings"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"primary": "input_boolean.a", "debounce_ms": 300, "event_types": []},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Luces quincho"
    assert result["options"]["primary"] == "input_boolean.a"
    await hass.async_block_till_done()
    assert hass.states.get("switch.luces_quincho") is not None


async def test_too_few(hass: HomeAssistant, booleans) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "x", "members": ["input_boolean.a"], "triggers": []}
    )
    assert result["errors"] == {"base": "too_few"}


async def test_already_linked(hass: HomeAssistant, booleans, make_entry) -> None:
    await make_entry()
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "x", "members": ["input_boolean.b", "input_boolean.c"], "triggers": []},
    )
    assert result["errors"] == {"base": "already_linked"}


async def test_options_flow(hass: HomeAssistant, booleans, make_entry) -> None:
    entry = await make_entry()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"members": ["input_boolean.a", "input_boolean.b", "input_boolean.c"], "triggers": []},
    )
    assert result["step_id"] == "settings"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"primary": "none", "debounce_ms": 0, "event_types": []}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["primary"] is None
    assert "input_boolean.c" in entry.runtime_data.members
