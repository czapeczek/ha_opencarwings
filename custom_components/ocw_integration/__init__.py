from __future__ import annotations

import logging
from datetime import timedelta
import asyncio
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .abrp import ABRPBridge
from .api import OpenCarWingsAPI, AuthenticationError, RequestError

DOMAIN = "ocw_integration"
PLATFORMS = ["sensor", "switch", "device_tracker", "button", "select", "binary_sensor"]

# default: 15 minutes
DEFAULT_SCAN_INTERVAL_MIN = 15

_LOGGER = logging.getLogger(__name__)


def _resolve_timer_target(hass: HomeAssistant, call) -> tuple[str, str]:
    """Resolve an entry and VIN from a selected device or explicit fields."""
    entry_id = call.data.get("entry_id")
    vin = call.data.get("vin")
    device_id = call.data.get("device_id")

    if device_id:
        registry = device_registry.async_get(hass)
        device = registry.async_get(device_id)
        if device is None:
            raise ServiceValidationError("The selected car device was not found")
        for domain, identifier in device.identifiers:
            if domain == DOMAIN:
                vin = vin or identifier
                break
        if not vin:
            raise ServiceValidationError("The selected device is not an OpenCarWings car")
        if not entry_id and device.config_entries:
            entry_id = next(iter(device.config_entries))
        if entry_id and device.config_entries and entry_id not in device.config_entries:
            raise ServiceValidationError("The selected car does not belong to the selected integration entry")

    if not entry_id:
        entries = [key for key, value in hass.data.get(DOMAIN, {}).items() if isinstance(value, dict)]
        if len(entries) == 1:
            entry_id = entries[0]
    if not entry_id:
        raise ServiceValidationError("Select an OpenCarWings integration entry")
    if not vin:
        raise ServiceValidationError("Select a car or provide a VIN")
    if entry_id not in hass.data.get(DOMAIN, {}):
        raise ServiceValidationError("The selected OpenCarWings integration entry is not loaded")
    return entry_id, vin


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the OpenCARWINGS integration from a config entry with a DataUpdateCoordinator."""
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    hass.data.setdefault(DOMAIN, {})

    # Respect configured API base URL (options override initial data)
    opts = getattr(entry, "options", {}) or {}
    base_url = opts.get("api_base_url", entry.data.get("api_base_url"))
    client = OpenCarWingsAPI(hass, base_url=base_url) if base_url else OpenCarWingsAPI(hass)
    
    # Set authentication method: API key or JWT tokens
    if entry.data.get("api_key"):
        client.set_api_key(entry.data.get("api_key"))
    else:
        # Fallback for old entries with JWT tokens
        client.set_tokens(entry.data.get("access_token"), entry.data.get("refresh_token"))

    # Ensure base_url is accessible on the client instance (helps tests and some clients)
    if base_url:
        # set both common attribute names
        try:
            setattr(client, "base_url", base_url)
            setattr(client, "_base", base_url)
        except Exception:
            pass

    # Optional ABRP telemetry bridge
    abrp_token = (opts.get("abrp_user_token", entry.data.get("abrp_user_token", "")) or "").strip()
    abrp_bridge = ABRPBridge(hass, client, abrp_token) if abrp_token else None
    if abrp_bridge:
        _LOGGER.info("ABRP telemetry bridge enabled for OpenCARWINGS (%s)", entry.title)

    # Store client and optional ABRP bridge in hass.data under the entry id
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "abrp_bridge": abrp_bridge,
    }

    async def _enrich_cars_with_details(cars: list) -> list:
        """Enrich lite car objects (from /api/car/) with detail fetched by VIN."""
        if not isinstance(cars, list) or not cars:
            return cars
        if not hasattr(client, "async_get_car_by_vin"):
            return cars

        vins: list[str] = []
        tasks = []
        for c in cars:
            if isinstance(c, dict) and c.get("vin"):
                vin = str(c["vin"])
                vins.append(vin)
                tasks.append(client.async_get_car_by_vin(vin))

        if not tasks:
            return cars

        details = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge by VIN: detail wins, list fills missing fields
        by_vin: dict[str, dict] = {}
        for c in cars:
            if isinstance(c, dict) and c.get("vin"):
                by_vin[str(c["vin"])] = c

        for d in details:
            if isinstance(d, Exception) or not isinstance(d, dict):
                continue
            vin = d.get("vin")
            if not vin:
                continue
            vin = str(vin)
            by_vin[vin] = {**by_vin.get(vin, {}), **d}

        # Preserve list order
        out: list[dict] = []
        for c in cars:
            if isinstance(c, dict) and c.get("vin"):
                out.append(by_vin.get(str(c["vin"]), c))
            elif isinstance(c, dict):
                out.append(c)

        return out

    async def _async_update_data():
        """Fetch data from API."""
        from datetime import datetime, timezone

        try:
            # Prefer dedicated helper if available
            if hasattr(client, "async_get_cars"):
                cars = await client.async_get_cars()

                # Try to enrich with detail endpoint (to get odometer, versions, etc.)
                try:
                    cars = await _enrich_cars_with_details(cars)
                except Exception as err:
                    _LOGGER.debug("Could not enrich car list with details: %s", err)

                # Track the last successful update time for CarLastRequestedSensor
                coordinator.last_update_time = datetime.now(timezone.utc)
                hass.data[DOMAIN][entry.entry_id]["cars"] = cars

                if abrp_bridge is not None:
                    try:
                        await abrp_bridge.async_process_cars(cars)
                    except Exception as err:
                        _LOGGER.debug("Could not forward telemetry to ABRP: %s", err)

                return cars

            # Fallback to raw request-based client (used in tests)
            if hasattr(client, "async_request"):
                resp = await client.async_request("GET", "/api/car/")
                result = await resp.json()

                try:
                    result = await _enrich_cars_with_details(result)
                except Exception as err:
                    _LOGGER.debug("Could not enrich car list with details: %s", err)

                coordinator.last_update_time = datetime.now(timezone.utc)
                hass.data[DOMAIN][entry.entry_id]["cars"] = result

                if abrp_bridge is not None:
                    try:
                        await abrp_bridge.async_process_cars(result)
                    except Exception as err:
                        _LOGGER.debug("Could not forward telemetry to ABRP: %s", err)

                return result

            raise RuntimeError("Client has no method to fetch cars")

        except AuthenticationError:
            # Let Home Assistant handle reauth via existing logic
            raise
        except RequestError as err:
            raise UpdateFailed(err)
        except Exception as err:  # pragma: no cover - network or unexpected
            raise UpdateFailed(err)

    # Determine scan interval from options (or fallback to default)
    scan_min = int(opts.get("scan_interval", entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL_MIN)))

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
        # Log the error but continue setup so platforms can use cached data if available
        _LOGGER.exception("Error while initializing OpenCARWINGS coordinator during setup")
        hass.data[DOMAIN][entry.entry_id]["cars"] = hass.data[DOMAIN][entry.entry_id].get("cars", [])
        # Don't abort setup; proceed to forward platforms so entity platforms can be set up
        pass

    # Schedule 30-second ABRP & active-polling timer ONLY when ABRP token is configured.
    # Without an ABRP token, updates follow the standard Scan Interval and OpenCARWINGS schedule.
    if abrp_bridge is not None:
        try:
            from homeassistant.helpers.event import async_track_time_interval

            async def _async_abrp_heartbeat(_now=None) -> None:
                await abrp_bridge.async_heartbeat(coordinator)

            unsub_abrp = async_track_time_interval(
                hass, _async_abrp_heartbeat, timedelta(seconds=30)
            )
            entry.async_on_unload(unsub_abrp)
        except Exception as err:
            _LOGGER.debug("Could not register ABRP heartbeat interval: %s", err)

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
            timer_fields = {
                vol.Required("entry_id"): str,
                vol.Required("vin"): str,
            }

            async def _handle_create_timer(call):
                entry_id, vin = _resolve_timer_target(hass, call)
                data = hass.data[DOMAIN][entry_id]
                timer = {key: value for key, value in call.data.items() if key not in {"entry_id", "vin", "device_id"}}
                await data["client"].async_create_timer(vin, timer)
                await data["coordinator"].async_request_refresh()

            async def _handle_update_timer(call):
                entry_id, vin = _resolve_timer_target(hass, call)
                data = hass.data[DOMAIN][entry_id]
                timer_id = call.data["timer_id"]
                timer = {key: value for key, value in call.data.items() if key not in {"entry_id", "vin", "device_id", "timer_id"}}
                await data["client"].async_update_timer(vin, timer_id, timer)
                await data["coordinator"].async_request_refresh()

            async def _handle_delete_timer(call):
                entry_id, vin = _resolve_timer_target(hass, call)
                data = hass.data[DOMAIN][entry_id]
                await data["client"].async_delete_timer(vin, call.data["timer_id"])
                await data["coordinator"].async_request_refresh()

            hass.services.async_register(DOMAIN, "create_timer", _handle_create_timer, vol.Schema({
                vol.Optional("entry_id"): str,
                vol.Optional("vin"): str,
                vol.Optional("device_id"): str,
                vol.Required("name"): str,
                vol.Required("time"): str,
                vol.Optional("timer_type", default=0): vol.Coerce(int),
                vol.Optional("command_type", default=3): vol.Coerce(int),
                vol.Optional("enabled", default=True): bool,
                vol.Optional("date"): str,
                vol.Optional("weekday_mon", default=False): bool,
                vol.Optional("weekday_tue", default=False): bool,
                vol.Optional("weekday_wed", default=False): bool,
                vol.Optional("weekday_thu", default=False): bool,
                vol.Optional("weekday_fri", default=False): bool,
                vol.Optional("weekday_sat", default=False): bool,
                vol.Optional("weekday_sun", default=False): bool,
            }))
            hass.services.async_register(DOMAIN, "update_timer", _handle_update_timer, vol.Schema({
                vol.Optional("entry_id"): str,
                vol.Optional("vin"): str,
                vol.Optional("device_id"): str,
                vol.Required("timer_id"): vol.Coerce(int),
                vol.Optional("enabled"): bool,
                vol.Optional("name"): str,
                vol.Optional("time"): str,
                vol.Optional("date"): str,
                vol.Optional("command_type"): vol.Coerce(int),
                vol.Optional("timer_type"): vol.Coerce(int),
                vol.Optional("weekday_mon"): bool,
                vol.Optional("weekday_tue"): bool,
                vol.Optional("weekday_wed"): bool,
                vol.Optional("weekday_thu"): bool,
                vol.Optional("weekday_fri"): bool,
                vol.Optional("weekday_sat"): bool,
                vol.Optional("weekday_sun"): bool,
            }))
            hass.services.async_register(DOMAIN, "delete_timer", _handle_delete_timer, vol.Schema({
                vol.Optional("entry_id"): str,
                vol.Optional("vin"): str,
                vol.Optional("device_id"): str,
                vol.Required("timer_id"): vol.Coerce(int),
            }))
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
