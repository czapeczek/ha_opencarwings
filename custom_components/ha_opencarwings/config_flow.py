from __future__ import annotations

import logging

import opencarwings_client
from opencarwings_client import AccountDetail
from opencarwings_client.rest import ApiException
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN

from .api import get_client, DEFAULT_API_BASE

# Scan interval choices in minutes with friendly labels
SCAN_INTERVAL_CHOICES = [
    (1, "1 minute"),
    (5, "5 minutes"),
    (10, "10 minutes"),
    (15, "15 minutes (default)"),
    (30, "30 minutes"),
    (60, "1 hour"),
    (180, "3 hours"),
    (360, "6 hours"),
    (720, "12 hours"),
    (1440, "1 day"),
]
# Values used when selector is not available (fallback)
SCAN_INTERVAL_OPTIONS = [c[0] for c in SCAN_INTERVAL_CHOICES]
DEFAULT_SCAN_INTERVAL_MIN = 15

# Default API base URL
_LOGGER = logging.getLogger(__name__)


class OpenCARWINGSConfigFlow(config_entries.ConfigFlow, domain="ha_opencarwings"):
    """Config flow for OpenCARWINGS."""

    VERSION = 2

    async def async_step_user(self, user_input=None):
        """Handle the initial step where user provides credentials."""
        errors = {}
        if user_input is not None:
            # each user has its own API token
            api_token = user_input[CONF_TOKEN]
            api_base = user_input.get("api_base_url", DEFAULT_API_BASE)
            hass = getattr(self, "hass", None)
            async with await hass.async_add_executor_job(get_client, hass, api_base, api_token) as client:
                api_instance = opencarwings_client.AccountApi(client)
                try:
                    account_info: AccountDetail = await api_instance.account_detail_list()
                    return self.async_create_entry(
                        title=account_info.username,
                        data={
                            "account_info": account_info.username,
                            "api_token": api_token,
                            # persist initial scan interval choice
                            "scan_interval": user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL_MIN),
                            "api_base_url": api_base,
                        },
                    )
                except ApiException as err:
                    _LOGGER.exception(err)
                    if err.status == 401:
                        errors["base"] = "auth"
                    else:
                        errors["base"] = err.body
                except Exception as err:
                    _LOGGER.exception(err)
                    errors["base"] = "unknown"

        # Prefer to show a pretty select when Home Assistant's selector helpers
        # are available; fall back to a numeric choice list otherwise.
        try:
            from homeassistant.helpers import selector

            scan_selector = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[{"value": v, "label": l} for v, l in SCAN_INTERVAL_CHOICES]
                )
            )
        except Exception:
            # selector not available in minimal test stubs — use numeric options
            scan_selector = vol.In(SCAN_INTERVAL_OPTIONS)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN): str,
                vol.Required("scan_interval", default=DEFAULT_SCAN_INTERVAL_MIN): scan_selector,
                vol.Required("api_base_url", default=DEFAULT_API_BASE): str,
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
        current_api = self.config_entry.options.get("api_base_url", self.config_entry.data.get("api_base_url", DEFAULT_API_BASE))
        current_api_token = self.config_entry.options.get(CONF_TOKEN, self.config_entry.data.get("api_token"))
        try:
            from homeassistant.helpers import selector

            scan_selector = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[{"value": v, "label": l} for v, l in SCAN_INTERVAL_CHOICES]
                )
            )
        except Exception:
            scan_selector = vol.In(SCAN_INTERVAL_OPTIONS)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_TOKEN, default=current_api_token): str,
                vol.Required("scan_interval", default=current_scan): scan_selector,
                vol.Required("api_base_url", default=current_api): str,
            }),
        )


async def async_get_options_flow(config_entry):
    return OptionsFlowHandler(config_entry)
