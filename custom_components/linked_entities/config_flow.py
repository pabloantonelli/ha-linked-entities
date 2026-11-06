"""Config and options flow for Linked Entities."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DEBOUNCE_MS,
    CONF_EVENT_TYPES,
    CONF_MEMBERS,
    CONF_PRIMARY,
    CONF_TRIGGERS,
    DEFAULT_DEBOUNCE_MS,
    DOMAIN,
    STATEFUL_DOMAINS,
    TRIGGER_DOMAINS,
)

NO_PRIMARY = "none"


def _entities_schema(defaults: dict[str, Any]) -> dict:
    return {
        vol.Required(
            CONF_MEMBERS, default=defaults.get(CONF_MEMBERS, [])
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=STATEFUL_DOMAINS, multiple=True)
        ),
        vol.Optional(
            CONF_TRIGGERS, default=defaults.get(CONF_TRIGGERS, [])
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=TRIGGER_DOMAINS, multiple=True)
        ),
    }


def _settings_schema(members: list[str], defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_PRIMARY, default=defaults.get(CONF_PRIMARY) or NO_PRIMARY
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[NO_PRIMARY, *members],
                    translation_key=CONF_PRIMARY,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_DEBOUNCE_MS,
                default=defaults.get(CONF_DEBOUNCE_MS, DEFAULT_DEBOUNCE_MS),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=5000,
                    step=50,
                    unit_of_measurement="ms",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_EVENT_TYPES, default=defaults.get(CONF_EVENT_TYPES, [])
            ): selector.TextSelector(selector.TextSelectorConfig(multiple=True)),
        }
    )


def _validate_entities(
    flow_entries: list[ConfigEntry],
    user_input: dict[str, Any],
    exclude_entry_id: str | None = None,
) -> dict[str, str]:
    """Return form errors for the selected entities."""
    errors: dict[str, str] = {}
    members: list[str] = user_input.get(CONF_MEMBERS, [])
    triggers: list[str] = user_input.get(CONF_TRIGGERS, [])
    if not members:
        errors[CONF_MEMBERS] = "no_members"
    elif len(members) + len(triggers) < 2:
        errors["base"] = "too_few"
    if errors:
        return errors

    selected = set(members) | set(triggers)
    for entry in flow_entries:
        if entry.entry_id == exclude_entry_id:
            continue
        used = set(entry.options.get(CONF_MEMBERS, [])) | set(
            entry.options.get(CONF_TRIGGERS, [])
        )
        if selected & used:
            errors["base"] = "already_linked"
            break
    return errors


def _clean_settings(user_input: dict[str, Any]) -> dict[str, Any]:
    primary = user_input.get(CONF_PRIMARY)
    return {
        CONF_PRIMARY: None if primary in (None, NO_PRIMARY) else primary,
        CONF_DEBOUNCE_MS: int(user_input.get(CONF_DEBOUNCE_MS, DEFAULT_DEBOUNCE_MS)),
        CONF_EVENT_TYPES: [
            t.strip() for t in user_input.get(CONF_EVENT_TYPES, []) if t.strip()
        ],
    }


class LinkedEntitiesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create a link between entities."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: name and entities."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_entities(self._async_current_entries(), user_input)
            if not errors:
                self._data = user_input
                return await self.async_step_settings()

        defaults = user_input or {}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default=defaults.get(CONF_NAME, "")
                ): selector.TextSelector(),
                **_entities_schema(defaults),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: primary entity, debounce and event filters."""
        members: list[str] = self._data[CONF_MEMBERS]
        if user_input is not None:
            options = {
                CONF_MEMBERS: members,
                CONF_TRIGGERS: self._data.get(CONF_TRIGGERS, []),
                **_clean_settings(user_input),
            }
            return self.async_create_entry(
                title=self._data[CONF_NAME], data={}, options=options
            )

        default_primary = members[0] if len(members) == 1 else NO_PRIMARY
        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(members, {CONF_PRIMARY: default_primary}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return LinkedEntitiesOptionsFlow()


class LinkedEntitiesOptionsFlow(OptionsFlow):
    """Edit an existing link."""

    def __init__(self) -> None:
        """Initialise the options flow."""
        self._data: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: entities."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_entities(
                self.hass.config_entries.async_entries(DOMAIN),
                user_input,
                exclude_entry_id=self.config_entry.entry_id,
            )
            if not errors:
                self._data = user_input
                return await self.async_step_settings()

        defaults = user_input or dict(self.config_entry.options)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(_entities_schema(defaults)),
            errors=errors,
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: primary entity, debounce and event filters."""
        members: list[str] = self._data[CONF_MEMBERS]
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_MEMBERS: members,
                    CONF_TRIGGERS: self._data.get(CONF_TRIGGERS, []),
                    **_clean_settings(user_input),
                }
            )

        defaults = dict(self.config_entry.options)
        if defaults.get(CONF_PRIMARY) not in members:
            defaults[CONF_PRIMARY] = NO_PRIMARY
        return self.async_show_form(
            step_id="settings", data_schema=_settings_schema(members, defaults)
        )
