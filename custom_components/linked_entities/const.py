"""Constants for the Linked Entities integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "linked_entities"

CONF_MEMBERS: Final = "members"
CONF_TRIGGERS: Final = "triggers"
CONF_PRIMARY: Final = "primary"
CONF_DEBOUNCE_MS: Final = "debounce_ms"
CONF_EVENT_TYPES: Final = "event_types"

DEFAULT_DEBOUNCE_MS: Final = 300

# Entities with an on/off state that are kept in sync bidirectionally.
STATEFUL_DOMAINS: Final = ["switch", "light", "fan", "input_boolean"]
# Stateless entities (push buttons) whose activation toggles the whole link.
TRIGGER_DOMAINS: Final = ["event", "button", "input_button"]

# Seconds a context created by this integration is remembered, to recognise
# the state changes our own service calls cause and avoid feedback loops.
OWN_CONTEXT_TTL: Final = 10.0
# Seconds after commanding a member during which a contradicting report from
# that member is treated as a transitional echo (slow / bouncy devices).
ECHO_WINDOW: Final = 2.0
