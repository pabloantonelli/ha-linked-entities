"""Tests for the synchronisation engine."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from pytest_homeassistant_custom_component.common import async_fire_time_changed


async def _call(hass: HomeAssistant, domain: str, service: str, entity_id: str) -> None:
    await hass.services.async_call(domain, service, {"entity_id": entity_id}, blocking=True)
    await hass.async_block_till_done()


def _state(hass: HomeAssistant, entity_id: str) -> str:
    return hass.states.get(entity_id).state


async def test_a_turns_b(hass: HomeAssistant, booleans, make_entry) -> None:
    await make_entry()
    await _call(hass, "input_boolean", "turn_on", "input_boolean.a")
    assert _state(hass, "input_boolean.b") == STATE_ON
    await _call(hass, "input_boolean", "turn_off", "input_boolean.a")
    assert _state(hass, "input_boolean.b") == STATE_OFF


async def test_b_turns_a(hass: HomeAssistant, booleans, make_entry) -> None:
    await make_entry()
    await _call(hass, "input_boolean", "turn_on", "input_boolean.b")
    assert _state(hass, "input_boolean.a") == STATE_ON
    assert hass.states.get("sensor.test_link_last_source").state == "input_boolean.b"


async def test_no_loop(hass: HomeAssistant, booleans, make_entry) -> None:
    """One external change produces exactly one command per other member."""
    await make_entry(members=("input_boolean.a", "input_boolean.b", "input_boolean.c"))
    calls: list[str] = []

    def _record(event):
        if event.data["domain"] == "input_boolean":
            calls.append(event.data["service_data"]["entity_id"])

    hass.bus.async_listen("call_service", _record)
    await _call(hass, "input_boolean", "turn_on", "input_boolean.a")
    # one call by the test + one per other member, no ping-pong
    assert sorted(calls) == ["input_boolean.a", "input_boolean.b", "input_boolean.c"]
    assert all(_state(hass, f"input_boolean.{x}") == STATE_ON for x in "abc")


async def test_unavailable_not_propagated_and_resync(
    hass: HomeAssistant, booleans, make_entry
) -> None:
    await make_entry()
    await _call(hass, "input_boolean", "turn_on", "input_boolean.a")
    assert _state(hass, "input_boolean.b") == STATE_ON

    hass.states.async_set("input_boolean.b", STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert _state(hass, "input_boolean.a") == STATE_ON

    # B comes back "off" (e.g. device rebooted): the link pushes it back on.
    hass.states.async_set("input_boolean.b", STATE_OFF)
    await hass.async_block_till_done()
    assert _state(hass, "input_boolean.a") == STATE_ON
    # state was faked with async_set, so re-read what the service set
    assert _state(hass, "input_boolean.b") == STATE_ON


async def test_primary_wins_on_return(hass: HomeAssistant, booleans, make_entry) -> None:
    await make_entry(primary="input_boolean.a")
    await _call(hass, "input_boolean", "turn_on", "input_boolean.a")
    hass.states.async_set("input_boolean.a", STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    hass.states.async_set("input_boolean.a", STATE_OFF)
    await hass.async_block_till_done()
    assert _state(hass, "input_boolean.b") == STATE_OFF


async def test_startup_aligns_to_primary(hass: HomeAssistant, booleans, make_entry) -> None:
    await _call(hass, "input_boolean", "turn_on", "input_boolean.b")
    await make_entry(primary="input_boolean.a")
    assert _state(hass, "input_boolean.b") == STATE_OFF
    assert hass.states.get("switch.test_link").state == STATE_OFF


async def test_button_toggles(hass: HomeAssistant, booleans, make_entry) -> None:
    await make_entry(triggers=("input_button.btn",))
    await _call(hass, "input_button", "press", "input_button.btn")
    assert _state(hass, "input_boolean.a") == STATE_ON
    assert _state(hass, "input_boolean.b") == STATE_ON
    await _call(hass, "input_button", "press", "input_button.btn")
    assert _state(hass, "input_boolean.a") == STATE_OFF
    assert _state(hass, "input_boolean.b") == STATE_OFF


async def test_event_type_filter(hass: HomeAssistant, booleans, make_entry) -> None:
    hass.states.async_set("event.remote", "2026-01-01T00:00:00+00:00", {"event_type": "press"})
    await make_entry(
        members=("input_boolean.a",), triggers=("event.remote",), event_types=("press",)
    )
    hass.states.async_set("event.remote", "2026-01-01T00:00:01+00:00", {"event_type": "release"})
    await hass.async_block_till_done()
    assert _state(hass, "input_boolean.a") == STATE_OFF
    hass.states.async_set("event.remote", "2026-01-01T00:00:02+00:00", {"event_type": "press"})
    await hass.async_block_till_done()
    assert _state(hass, "input_boolean.a") == STATE_ON


async def test_sync_disabled(hass: HomeAssistant, booleans, make_entry) -> None:
    await make_entry()
    await _call(hass, "switch", "turn_off", "switch.test_link_sync_enabled")
    await _call(hass, "input_boolean", "turn_on", "input_boolean.a")
    assert _state(hass, "input_boolean.b") == STATE_OFF
    # resuming re-aligns (no primary → on if any is on)
    await _call(hass, "switch", "turn_on", "switch.test_link_sync_enabled")
    assert _state(hass, "input_boolean.b") == STATE_ON


async def test_group_switch_controls_all(hass: HomeAssistant, booleans, make_entry) -> None:
    await make_entry()
    await _call(hass, "switch", "turn_on", "switch.test_link")
    assert _state(hass, "input_boolean.a") == STATE_ON
    assert _state(hass, "input_boolean.b") == STATE_ON
    assert hass.states.get("switch.test_link").state == STATE_ON
    # A user change right after a sync is deferred past the echo window,
    # then propagated (not lost).
    await _call(hass, "input_boolean", "turn_off", "input_boolean.b")
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done()
    assert _state(hass, "input_boolean.a") == STATE_OFF
    assert hass.states.get("switch.test_link").state == STATE_OFF


async def test_bounce_after_command_is_absorbed(
    hass: HomeAssistant, booleans, make_entry
) -> None:
    """B reports off then on right after being commanded: A must stay on."""
    await make_entry()
    await _call(hass, "input_boolean", "turn_on", "input_boolean.a")
    hass.states.async_set("input_boolean.b", STATE_OFF)
    hass.states.async_set("input_boolean.b", STATE_ON)
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done()
    assert _state(hass, "input_boolean.a") == STATE_ON


async def test_debounce_absorbs_bounce(hass: HomeAssistant, booleans, make_entry) -> None:
    await make_entry(debounce_ms=500)
    hass.states.async_set("input_boolean.a", STATE_ON)
    hass.states.async_set("input_boolean.a", STATE_OFF)
    hass.states.async_set("input_boolean.a", STATE_ON)
    await hass.async_block_till_done()
    assert _state(hass, "input_boolean.b") == STATE_OFF  # not yet
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()
    assert _state(hass, "input_boolean.b") == STATE_ON


async def test_unload(hass: HomeAssistant, booleans, make_entry) -> None:
    entry = await make_entry()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    await _call(hass, "input_boolean", "turn_on", "input_boolean.a")
    assert _state(hass, "input_boolean.b") == STATE_OFF
