from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import OpenCarWingsAPI, AuthenticationError

DOMAIN = "ha_opencarwings"
PLATFORMS = ["sensor", "switch", "device_tracker"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the OpenCARWINGS integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    client = OpenCarWingsAPI(hass)
    client.set_tokens(entry.data.get("access_token"), entry.data.get("refresh_token"))

    # Store client in hass.data under the entry id
    hass.data[DOMAIN][entry.entry_id] = {"client": client}

    # Quick validation - try to call an endpoint to ensure the tokens work and fetch cars
    try:
        resp = await client.async_request("GET", "/api/car/")
        if resp.status == 401:
            _LOGGER.warning("Tokens invalid or expired; attempting refresh")
            try:
                await client.async_refresh_token()
            except AuthenticationError:
                _LOGGER.warning("Refresh failed; requesting reauthentication")
                hass.config_entries.async_start_reauth(entry.entry_id)
                return False

        if resp.status == 200:
            cars = await resp.json()
            hass.data[DOMAIN][entry.entry_id]["cars"] = cars
        else:
            hass.data[DOMAIN][entry.entry_id]["cars"] = []

    except Exception:  # pragma: no cover - network or unexpected
        _LOGGER.exception("Error while validating OpenCARWINGS tokens during setup")
        return False

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("OpenCARWINGS setup complete for %s", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove stored data
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok