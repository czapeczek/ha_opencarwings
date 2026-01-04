from __future__ import annotations

import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OpenCarWingsAPI, AuthenticationError

DOMAIN = "ha_opencarwings"
PLATFORMS = ["sensor", "switch", "device_tracker"]

# default: 15 minutes
DEFAULT_SCAN_INTERVAL_MIN = 15

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the OpenCARWINGS integration from a config entry with a DataUpdateCoordinator."""
    hass.data.setdefault(DOMAIN, {})

    # Respect configured API base URL (options override initial data)
    base_url = entry.options.get("api_base_url", entry.data.get("api_base_url"))
    client = OpenCarWingsAPI(hass, base_url=base_url) if base_url else OpenCarWingsAPI(hass)
    client.set_tokens(entry.data.get("access_token"), entry.data.get("refresh_token"))

    # Store client in hass.data under the entry id
    hass.data[DOMAIN][entry.entry_id] = {"client": client}

    async def _async_update_data():
        """Fetch data from API."""
        try:
            cars = await client.async_get_cars()
            return cars
        except AuthenticationError:
            # Let Home Assistant handle reauth via existing logic
            raise
        except Exception as err:  # pragma: no cover - network or unexpected
            raise UpdateFailed(err)

    # Determine scan interval from options (or fallback to default)
    scan_min = entry.options.get("scan_interval", entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL_MIN))

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_method=_async_update_data,
        update_interval=timedelta(minutes=scan_min),
    )

    # store coordinator
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    # Do initial refresh to populate data
    try:
        await coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN][entry.entry_id]["cars"] = coordinator.data or []
    except AuthenticationError:
        _LOGGER.warning("Tokens invalid or expired; requesting reauthentication")
        hass.config_entries.async_start_reauth(entry.entry_id)
        return False
    except Exception:
        _LOGGER.exception("Error while initializing OpenCARWINGS coordinator during setup")
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