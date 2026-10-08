"""Config flow: My Effe account (e-mail + password), verified by logging in."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import EffeAuthError, EffeClient, EffeError
from .const import DOMAIN

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL)),
        vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
    }
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR})


class EffeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def _async_validate(self, email: str, password: str) -> str | None:
        """Log in and list devices; return an error key or None."""
        client = EffeClient(async_get_clientsession(self.hass), email, password)
        try:
            await client.async_login()
            devices = await client.async_get_devices()
        except EffeAuthError:
            return "invalid_auth"
        except EffeError:
            return "cannot_connect"
        return None if devices else "no_devices"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()
            if error := await self._async_validate(email, user_input[CONF_PASSWORD]):
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=email,
                    data={CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            error = await self._async_validate(entry.data[CONF_EMAIL], user_input[CONF_PASSWORD])
            if error in (None, "no_devices"):
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"email": entry.data[CONF_EMAIL]},
        )
