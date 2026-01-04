from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OpenCarWingsAPI, AuthenticationError

DOMAIN = "ha_opencarwings"
PLATFORMS = ["sensor", "switch", "device_tracker", "button"]

# default: 15 minutes
DEFAULT_SCAN_INTERVAL_MIN = 15

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the OpenCARWINGS integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    # -------------------------
    # API client
    # -------------------------
    opts = entry.options or {}
    base_url = opts.get("api_base_url", entry.data.get("api_base_url"))

    client = OpenCarWingsAPI(hass, base_url=base_url) if base_url else OpenCarWingsAPI(hass)
    client.set_tokens(entry.data.get("access_token"), entry.data.get("refresh_token"))

    # keep base_url accessible (helps tests and some client code)
    if base_url:
        try:
            client.base_url = base_url
            client._base = base_url
        except Exception:
            pass

    # -------------------------
    # Coordinator update method
    # -------------------------
    async def _async_update_data() -> list[dict[str, Any]]:
        try:
            if hasattr(client, "async_get_cars"):
                return await client.async_get_cars()

            if hasattr(client, "async_request"):
                resp = await client.async_request("GET", "/api/car/")
                return await resp.json()

            raise RuntimeError("Client has no method to fetch cars")

        except AuthenticationError:
            # handled by HA reauth flow
            raise
        except Exception as err:
            raise UpdateFailed(err) from err

    scan_min = opts.get(
        "scan_interval",
        entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL_MIN),
    )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_method=_async_update_data,
        update_interval=timedelta(minutes=int(scan_min)),
    )

    # -------------------------
    # FIRST REFRESH (CRITICAL)
    # -------------------------
    try:
        await coordinator.async_config_entry_first_refresh()
        cars_cache = coordinator.data or []
    except AuthenticationError:
        _LOGGER.warning("OpenCARWINGS tokens invalid/expired – starting reauth")
        hass.config_entries.async_start_reauth(entry.entry_id)
        return False
    except Exception:
        _LOGGER.exception("Coordinator initial refresh failed; using cached data if available")
        cars_cache = []

    # -------------------------
    # Store integration state
    # -------------------------
    hass.data[DOMAIN][entry.entry_id].update(
        {
            "client": client,
            "coordinator": coordinator,
            # CRITICAL: cache VINs so entities never disappear
            "cars": cars_cache,
        }
    )

    # -------------------------
    # Forward platforms
    # -------------------------
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # -------------------------
    # Optional refresh service
    # -------------------------
    if not hass.data[DOMAIN].get("_service_refresh_registered"):

        async def _handle_refresh(call):
            entry_id = (call.data or {}).get("entry_id")
            if entry_id:
                data = hass.data.get(DOMAIN, {}).get(entry_id)
                if not data:
                    _LOGGER.warning("Refresh requested for unknown entry %s", entry_id)
                    return
                coord = data.get("coordinator")
                if coord:
                    await coord.async_request_refresh()
            else:
                for d in hass.data.get(DOMAIN, {}).values():
                    if isinstance(d, dict):
                        coord = d.get("coordinator")
                        if coord:
                            await coord.async_request_refresh()

        try:
            hass.services.async_register(DOMAIN, "refresh", _handle_refresh)
            hass.data[DOMAIN]["_service_refresh_registered"] = True
        except Exception:
            _LOGGER.debug("Refresh service not registered (services unavailable)")

    _LOGGER.info("OpenCARWINGS setup complete for %s", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
