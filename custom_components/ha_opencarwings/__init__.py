from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

DOMAIN = "ha_opencarwings"
PLATFORMS = ["sensor", "switch", "device_tracker", "button"]

# default: 15 minutes
DEFAULT_SCAN_INTERVAL_MIN = 15

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .api import get_client
    from .util import CarData
    import opencarwings_client
    from opencarwings_client import CarSerializerList, ApiException, Car
    from typing import List
    import asyncio
    from datetime import timedelta

    """Set up the OpenCARWINGS integration from a config entry with a DataUpdateCoordinator."""
    hass.data.setdefault(DOMAIN, {})

    # Respect configured API base URL (options override initial data)
    opts = getattr(entry, "options", {}) or {}
    base_url = opts.get("api_base_url", entry.data.get("api_base_url"))
    api_token = opts.get("api_token", entry.data.get("api_token"))
    client = await hass.async_add_executor_job(get_client, hass, base_url, api_token)

    # Ensure base_url is accessible on the client instance (helps tests and some clients)
    if base_url:
        # set both common attribute names
        try:
            setattr(client, "base_url", base_url)
            setattr(client, "_base", base_url)
        except Exception:
            pass

    # Store client in hass.data under the entry id
    hass.data[DOMAIN][entry.entry_id] = {"client": client}

    async def _enrich_cars_with_details(cars: List[CarData]) -> List[CarData]:
        """Enrich lite car objects (from /api/car/) with detail fetched by VIN."""
        if not isinstance(cars, list) or not cars:
            return cars

        cars_api = opencarwings_client.CarsApi(client)
        tasks = []
        by_vin: dict[str, CarData] = {}
        for c in cars:
            by_vin[str(c.vin)] = c
            tasks.append(cars_api.api_car_read(str(c.vin)))

        if not tasks:
            return cars

        details = await asyncio.gather(*tasks, return_exceptions=True)

        for d in details:
            if isinstance(d, Exception) or not isinstance(d, Car):
                continue
            vin = d.vin
            if not vin:
                continue
            vin = str(vin)
            by_vin[vin].car_detail = d

        # Preserve list order
        out: List[CarData] = []
        for c in cars:
            if c.vin:
                out.append(by_vin.get(str(c.vin), c))
            else:
                out.append(c)

        return out

    async def _async_update_data() -> List[CarData]:
        """Fetch data from API."""
        from datetime import datetime, timezone

        try:
            cars_api = opencarwings_client.CarsApi(client)
            # Prefer dedicated helper if available
            cars_list: List[CarSerializerList] = await cars_api.api_car_list()

            cars = [CarData(vin=x.vin, list_car=x) for x in cars_list]

            # Try to enrich with detail endpoint (to get odometer, versions, etc.)
            try:
                cars = await _enrich_cars_with_details(cars)
            except Exception as err:
                _LOGGER.exception(err)
                _LOGGER.error("Could not enrich car list with details: %s", err)

            # Track the last successful update time for CarLastRequestedSensor
            coordinator.last_update_time = datetime.now(timezone.utc)
            return cars
        except ApiException as err:
            raise UpdateFailed(err)
        except Exception as err:  # pragma: no cover - network or unexpected
            raise UpdateFailed(err)

    # Determine scan interval from options (or fallback to default)
    scan_min = opts.get("scan_interval", entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL_MIN))

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
    except ApiException as err:
        _LOGGER.error(err)
        hass.config_entries.async_start_reauth(entry.entry_id)
        return False
    except Exception:
        # Log the error but continue setup so platforms can use cached data if available
        _LOGGER.exception("Error while initializing OpenCARWINGS coordinator during setup")
        hass.data[DOMAIN][entry.entry_id]["cars"] = hass.data[DOMAIN][entry.entry_id].get("cars", [])
        # Don't abort setup; proceed to forward platforms so entity platforms can be set up
        pass

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register integration service to allow manual refresh via service call
    # Register only once per hass instance
    if not hass.data[DOMAIN].get("_service_refresh_registered"):
        async def _handle_refresh(call):
            """Handle service call to refresh OpenCARWINGS data."""
            entry_id = (call.data or {}).get("entry_id") if call else None
            if entry_id:
                data = hass.data.get(DOMAIN, {}).get(entry_id)
                if not data:
                    _LOGGER.warning("Refresh requested for unknown entry %s", entry_id)
                    return
                coord = data.get("coordinator")
                if coord:
                    await coord.async_request_refresh()
            else:
                # refresh all coordinators
                for d in hass.data.get(DOMAIN, {}).values():
                    # skip non-dict sentinel values stored in hass.data (like flags)
                    if not isinstance(d, dict):
                        continue
                    coord = d.get("coordinator")
                    if coord:
                        await coord.async_request_refresh()

        try:
            hass.services.async_register(DOMAIN, "refresh", _handle_refresh)
            hass.data[DOMAIN]["_service_refresh_registered"] = True
        except Exception:
            # If hass.services isn't available in tests/stubs, ignore
            _LOGGER.debug("Could not register refresh service (services not available in hass stub)")

    _LOGGER.info("OpenCARWINGS setup complete for %s", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove stored data
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
