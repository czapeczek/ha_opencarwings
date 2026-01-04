from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .api import OpenCarWingsAPI, AuthenticationError, DEFAULT_API_BASE

# Scan interval choices in minutes
SCAN_INTERVAL_OPTIONS = [1, 5, 10, 15, 30, 60, 180, 360, 720, 1440]
DEFAULT_SCAN_INTERVAL_MIN = 15

# Default API base URL
DEFAULT_API_BASE_URL = DEFAULT_API_BASE


class OpenCARWINGSConfigFlow(config_entries.ConfigFlow, domain="ha_opencarwings"):
    """Config flow for OpenCARWINGS."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where user provides credentials."""
        errors = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            api_base = user_input.get("api_base_url", DEFAULT_API_BASE_URL)

            client = OpenCarWingsAPI(getattr(self, "hass", None), base_url=api_base)
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
                        # persist initial scan interval choice
                        "scan_interval": user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL_MIN),
                        "api_base_url": api_base,
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required("scan_interval", default=DEFAULT_SCAN_INTERVAL_MIN): vol.In(SCAN_INTERVAL_OPTIONS),
                vol.Required("api_base_url", default=DEFAULT_API_BASE_URL): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_scan = self.config_entry.options.get("scan_interval", self.config_entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL_MIN))
        current_api = self.config_entry.options.get("api_base_url", self.config_entry.data.get("api_base_url", DEFAULT_API_BASE_URL))
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("scan_interval", default=current_scan): vol.In(SCAN_INTERVAL_OPTIONS),
                vol.Required("api_base_url", default=current_api): str,
            }),
        )


async def async_get_options_flow(config_entry):
    return OptionsFlowHandler(config_entry)
