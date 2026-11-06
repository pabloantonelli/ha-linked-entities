"""Synchronisation engine for a single link group."""

from __future__ import annotations

from collections.abc import Callable
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_STARTED,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Context,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .const import (
    CONF_DEBOUNCE_MS,
    CONF_EVENT_TYPES,
    CONF_MEMBERS,
    CONF_PRIMARY,
    CONF_TRIGGERS,
    DEFAULT_DEBOUNCE_MS,
    ECHO_WINDOW,
    OWN_CONTEXT_TTL,
)

_LOGGER = logging.getLogger(__name__)

_INVALID_STATES = (None, STATE_UNAVAILABLE, STATE_UNKNOWN)

type LinkedEntitiesConfigEntry = ConfigEntry[LinkGroup]


def _on_off(state: State | None) -> bool | None:
    """Return True/False for an on/off state, None when it is not usable."""
    if state is None or state.state not in (STATE_ON, STATE_OFF):
        return None
    return state.state == STATE_ON


class LinkGroup:
    """Keep a set of on/off entities mirroring each other."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the group from the config entry options."""
        self.hass = hass
        self.entry = entry
        options = entry.options
        self.members: list[str] = list(options.get(CONF_MEMBERS, []))
        self.triggers: list[str] = list(options.get(CONF_TRIGGERS, []))
        self.primary: str | None = options.get(CONF_PRIMARY) or None
        self.event_types: list[str] = [
            t.strip() for t in options.get(CONF_EVENT_TYPES, []) if t.strip()
        ]
        self.debounce: float = (
            options.get(CONF_DEBOUNCE_MS, DEFAULT_DEBOUNCE_MS) or 0
        ) / 1000

        self.sync_enabled = True
        self.is_on: bool | None = None
        self.last_source: str | None = None

        self._own_contexts: dict[str, float] = {}
        self._expected: dict[str, tuple[bool, float]] = {}
        self._pending_source: str | None = None
        self._cancel_debounce: CALLBACK_TYPE | None = None
        self._echo_rechecks: dict[str, CALLBACK_TYPE] = {}
        self._unsubs: list[CALLBACK_TYPE] = []
        self._listeners: list[Callable[[], None]] = []

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    @callback
    def async_start(self) -> None:
        """Start listening to members and perform the initial alignment."""
        self._unsubs.append(
            async_track_state_change_event(
                self.hass, self.members, self._handle_member_event
            )
        )
        if self.triggers:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, self.triggers, self._handle_trigger_event
                )
            )
        if self.hass.is_running:
            self._async_initial_sync()
        else:
            self._unsubs.append(
                self.hass.bus.async_listen_once(
                    EVENT_HOMEASSISTANT_STARTED,
                    lambda _event: self._async_initial_sync(),
                )
            )

    @callback
    def async_stop(self) -> None:
        """Stop all listeners and timers."""
        self._cancel_pending()
        for cancel in self._echo_rechecks.values():
            cancel()
        self._echo_rechecks.clear()
        while self._unsubs:
            unsub = self._unsubs.pop()
            try:
                unsub()
            except ValueError:
                # async_listen_once listener already fired and removed itself.
                pass

    @callback
    def async_add_listener(self, update_callback: Callable[[], None]) -> CALLBACK_TYPE:
        """Register an entity callback fired whenever the group changes."""
        self._listeners.append(update_callback)

        @callback
        def remove() -> None:
            self._listeners.remove(update_callback)

        return remove

    @callback
    def _notify(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()

    # ------------------------------------------------------------------ #
    # Public API used by entities
    # ------------------------------------------------------------------ #
    @callback
    def async_set_sync_enabled(self, enabled: bool) -> None:
        """Pause or resume synchronisation."""
        self.sync_enabled = enabled
        if enabled:
            # Re-align members that may have drifted while paused.
            self._async_initial_sync()
        else:
            self._cancel_pending()
        self._notify()

    async def async_turn(self, target: bool, source: str) -> None:
        """Turn the whole group on/off (from the aggregate switch)."""
        self._cancel_pending()
        await self._async_apply(target, source)

    # ------------------------------------------------------------------ #
    # State computation
    # ------------------------------------------------------------------ #
    def _computed_state(self) -> bool | None:
        """Derive the group state from the members' current states."""
        if self.primary and (
            value := _on_off(self.hass.states.get(self.primary))
        ) is not None:
            return value
        values = [
            v
            for eid in self.members
            if (v := _on_off(self.hass.states.get(eid))) is not None
        ]
        if not values:
            return None
        return any(values)

    def _is_own(self, context: Context) -> bool:
        now = time.monotonic()
        for ctx_id, expires in list(self._own_contexts.items()):
            if expires < now:
                del self._own_contexts[ctx_id]
        return (
            context.id in self._own_contexts
            or (context.parent_id is not None and context.parent_id in self._own_contexts)
        )

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #
    @callback
    def _async_initial_sync(self) -> None:
        """Align every member to the primary (or 'on if any is on')."""
        target = self._computed_state()
        if target is None:
            return
        if not self.sync_enabled:
            self.is_on = target
            self._notify()
            return
        self.hass.async_create_task(
            self._async_apply(target, self.primary or "startup"),
            eager_start=True,
        )

    @callback
    def _handle_member_event(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        new_value = _on_off(new_state)
        if new_state is None or new_value is None:
            # Member went unavailable/unknown: never propagate that.
            self._refresh()
            return

        old_raw = old_state.state if old_state is not None else None
        if old_raw == new_state.state:
            return  # attribute-only change

        if self._is_own(new_state.context):
            # A change we caused ourselves.
            self._refresh()
            return

        if not self.sync_enabled:
            self._refresh()
            return

        if old_raw in _INVALID_STATES:
            self._handle_member_returned(entity_id, new_value)
            return

        if (expected := self._expected.get(entity_id)) is not None:
            expected_value, expires = expected
            if time.monotonic() < expires:
                if expected_value == new_value:
                    del self._expected[entity_id]
                else:
                    # Probably a bounce right after we commanded it; re-check
                    # when the window closes and propagate if it stuck.
                    _LOGGER.debug(
                        "Deferring transitional state %s of %s",
                        new_state.state,
                        entity_id,
                    )
                    self._defer_recheck(entity_id, expires - time.monotonic())
                return
            del self._expected[entity_id]

        self._schedule(entity_id)

    @callback
    def _defer_recheck(self, entity_id: str, delay: float) -> None:
        if (cancel := self._echo_rechecks.pop(entity_id, None)) is not None:
            cancel()

        @callback
        def _recheck(_now: Any) -> None:
            self._echo_rechecks.pop(entity_id, None)
            self._expected.pop(entity_id, None)
            value = _on_off(self.hass.states.get(entity_id))
            if self.sync_enabled and value is not None and value != self.is_on:
                self._schedule(entity_id)

        self._echo_rechecks[entity_id] = async_call_later(
            self.hass, max(delay, 0), _recheck
        )

    @callback
    def _handle_member_returned(self, entity_id: str, value: bool) -> None:
        """A member came back from unavailable/unknown."""
        if entity_id == self.primary or self.is_on is None:
            # The primary owns the physical load: its state is the truth.
            self._schedule(entity_id)
            return
        if value != self.is_on:
            self.hass.async_create_task(
                self._async_apply(self.is_on, entity_id), eager_start=True
            )

    @callback
    def _handle_trigger_event(self, event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        if (
            new_state is None
            or new_state.state in _INVALID_STATES
            or old_state is None
            or old_state.state == STATE_UNAVAILABLE
            or old_state.state == new_state.state
        ):
            return
        if self.event_types and new_state.domain == "event":
            if new_state.attributes.get("event_type") not in self.event_types:
                return
        if not self.sync_enabled:
            return
        current = self.is_on if self.is_on is not None else self._computed_state()
        target = not bool(current)
        self._cancel_pending()
        self.hass.async_create_task(
            self._async_apply(target, event.data["entity_id"]), eager_start=True
        )

    # ------------------------------------------------------------------ #
    # Propagation
    # ------------------------------------------------------------------ #
    @callback
    def _schedule(self, source: str) -> None:
        """Propagate the state of `source`, coalescing quick bounces."""
        self._cancel_pending()
        self._pending_source = source
        if self.debounce <= 0:
            self._fire_pending()
            return
        self._cancel_debounce = async_call_later(
            self.hass, self.debounce, self._debounce_fired
        )

    @callback
    def _debounce_fired(self, _now: Any) -> None:
        self._fire_pending()

    @callback
    def _fire_pending(self) -> None:
        source = self._pending_source
        self._pending_source = None
        self._cancel_debounce = None
        if source is None:
            return
        value = _on_off(self.hass.states.get(source))
        if value is None:
            return
        self.hass.async_create_task(
            self._async_apply(value, source), eager_start=True
        )

    @callback
    def _cancel_pending(self) -> None:
        if self._cancel_debounce is not None:
            self._cancel_debounce()
            self._cancel_debounce = None
        self._pending_source = None

    @callback
    def _refresh(self) -> None:
        """Recompute the group state without commanding anything."""
        new = self._computed_state()
        if new is not None and new != self.is_on:
            self.is_on = new
        self._notify()

    async def _async_apply(self, target: bool, source: str) -> None:
        """Command every out-of-sync, available member to `target`."""
        self.is_on = target
        self.last_source = source
        self._notify()

        context = Context()
        self._own_contexts[context.id] = time.monotonic() + OWN_CONTEXT_TTL
        service = SERVICE_TURN_ON if target else SERVICE_TURN_OFF

        for entity_id in self.members:
            current = _on_off(self.hass.states.get(entity_id))
            if current is None or current == target:
                continue
            self._expected[entity_id] = (target, time.monotonic() + ECHO_WINDOW)
            domain = entity_id.split(".", 1)[0]
            try:
                await self.hass.services.async_call(
                    domain,
                    service,
                    {ATTR_ENTITY_ID: entity_id},
                    blocking=False,
                    context=context,
                )
            except Exception:  # noqa: BLE001 - one bad member must not stop the rest
                _LOGGER.exception(
                    "Linked Entities %s: failed to %s %s",
                    self.entry.title,
                    service,
                    entity_id,
                )

    def as_dict(self) -> dict[str, Any]:
        """Return a diagnostics snapshot."""
        return {
            "members": self.members,
            "triggers": self.triggers,
            "primary": self.primary,
            "event_types": self.event_types,
            "debounce_s": self.debounce,
            "sync_enabled": self.sync_enabled,
            "is_on": self.is_on,
            "last_source": self.last_source,
            "member_states": {
                eid: (s.state if (s := self.hass.states.get(eid)) else None)
                for eid in [*self.members, *self.triggers]
            },
        }
