from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .api import OpenCarWingsAPI, AuthenticationError


class OpenCARWINGSConfigFlow(config_entries.ConfigFlow, domain="ha_opencarwings"):
    """Config flow for OpenCARWINGS."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where user provides credentials."""
        errors = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            client = OpenCarWingsAPI(getattr(self, "hass", None))
            try:
                tokens = await client.async_obtain_token(username, password)
            except AuthenticationError:
                errors["base"] = "auth"
            except Exception:  # pragma: no cover - fallback
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=username,
                    data={
                        "username": username,
                        "access_token": tokens.get("access"),
                        "refresh_token": tokens.get("refresh"),
                    },
                )

        data_schema = vol.Schema(
            {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
