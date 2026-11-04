"""Async client for OpenCARWINGS API (JWT auth).

Provides methods to obtain and refresh JWT tokens and make authenticated requests.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

try:
    from aiohttp import ClientResponse, ClientTimeout
except Exception:  # pragma: no cover - aiohttp not available in tests
    ClientResponse = object
    ClientTimeout = None

from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

DEFAULT_API_BASE = "https://opencarwings.viaaq.eu"


class AuthenticationError(Exception):
    pass


class RequestError(Exception):
    pass


class OpenCarWingsAPI:
    def __init__(self, hass, base_url: str = DEFAULT_API_BASE) -> None:
        self.hass = hass
        # Import the helper dynamically so tests that monkeypatch
        # `homeassistant.helpers.aiohttp_client.async_get_clientsession`
        # will be respected.
        try:
            import importlib

            aiohttp_mod = importlib.import_module(
                "homeassistant.helpers.aiohttp_client"
            )
            self._session = aiohttp_mod.async_get_clientsession(hass)
        except Exception:  # pragma: no cover - fallback for tests
            self._session = None

        self._base = base_url.rstrip("/")
        self._access: Optional[str] = None
        self._refresh: Optional[str] = None
        self._lock = asyncio.Lock()

    def set_tokens(self, access: str | None, refresh: str | None) -> None:
        self._access = access
        self._refresh = refresh

    def set_api_key(self, api_key: str) -> None:
        """Set API key for authentication (Personal API Key method)."""
        if not api_key or not api_key.strip():
            raise AuthenticationError("API key cannot be empty")
        self._access = api_key.strip()
        self._refresh = None

    async def async_obtain_token(self, username: str, password: str) -> dict:
        url = f"{self._base}/api/token/obtain/"
        payload = {"username": username, "password": password}

        _LOGGER.debug("Requesting JWT token for user %s", username)
        resp = await self._session.post(url, json=payload)
        if resp.status not in (200, 201):
            text = await resp.text()
            _LOGGER.debug("Token obtain failed: %s %s", resp.status, text)
            raise AuthenticationError("Invalid credentials or server error")

        data = await resp.json()
        self._access = data.get("access")
        self._refresh = data.get("refresh")
        if not self._access:
            raise AuthenticationError("No access token received")
        return data

    async def async_refresh_token(self) -> str:
        if not self._refresh:
            raise AuthenticationError("No refresh token available")
        url = f"{self._base}/api/token/refresh/"
        payload = {"refresh": self._refresh}

        _LOGGER.debug("Refreshing JWT token")
        resp = await self._session.post(url, json=payload)
        if resp.status not in (200, 201):
            text = await resp.text()
            _LOGGER.debug("Token refresh failed: %s %s", resp.status, text)
            raise AuthenticationError("Refresh failed")

        data = await resp.json()
        access = data.get("access")
        if not access:
            raise AuthenticationError("No access token received on refresh")
        self._access = access
        return access

    async def async_validate_api_key(self, api_key: str) -> bool:
        """Validate API key by making a simple request.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if API key is valid
            
        Raises:
            AuthenticationError if API key is invalid
        """
        self.set_api_key(api_key)
        try:
            resp = await self.async_request("GET", "/api/car/")
            if resp.status == 401:
                raise AuthenticationError("Invalid API key")
            if resp.status != 200:
                text = await resp.text()
                _LOGGER.debug("API key validation failed: %s %s", resp.status, text)
                raise RequestError(f"API key validation failed: {resp.status}")
            return True
        except AuthenticationError:
            raise
        except Exception as err:
            raise RequestError(f"Failed to validate API key: {err}")

    async def async_get_cars(self) -> list:
        """Retrieve a list of cars for the authenticated account.

        Returns a list of car objects (as dictionaries) on success.
        Raises RequestError or AuthenticationError on failures.
        """
        resp = await self.async_request("GET", "/api/car/")
        if resp.status == 401:
            raise AuthenticationError("Not authorized to fetch cars")
        if resp.status != 200:
            text = await resp.text()
            _LOGGER.debug("Failed to fetch cars: %s %s", resp.status, text)
            raise RequestError(f"Failed fetching cars: {resp.status}")

        data = await resp.json()
        # Expecting an array of car objects
        return data

    async def async_request(self, method: str, path: str, **kwargs) -> ClientResponse:
        url = f"{self._base}{path if path.startswith('/') else '/' + path}"
        headers = kwargs.pop("headers", {}) or {}

        if self._access:
                # If it looks like an API Key (long hex), use Token format; else Bearer (JWT)
                if len(self._access) > 100 or not self._access.startswith("eyJ"):
                    headers["Authorization"] = f"Token {self._access}"
                else:
                    headers["Authorization"] = f"Bearer {self._access}"

        if ClientTimeout is not None and "timeout" not in kwargs:
            kwargs["timeout"] = ClientTimeout(total=20)

        try:
            resp = await self._session.request(method, url, headers=headers, **kwargs)
        except Exception as err:  # pragma: no cover - network error
            _LOGGER.exception("Request to OpenCARWINGS failed")
            raise RequestError(err)

        # If unauthorized, try to refresh once and retry
        if resp.status == 401 and self._refresh:
            _LOGGER.debug("Received 401, attempting token refresh")
            async with self._lock:
                try:
                    await self.async_refresh_token()
                except AuthenticationError:
                    _LOGGER.debug("Refresh failed during retry")
                    raise
                headers["Authorization"] = f"Bearer {self._access}"
                resp = await self._session.request(method, url, headers=headers, **kwargs)

        return resp

    async def async_get_car_by_vin(self, vin: str) -> dict:
        """Retrieve full car detail by VIN."""
        vin = (vin or "").strip()
        if not vin:
            raise RequestError("VIN missing")

        # TODO: if your spec says a different path, change ONLY this line:
        path = f"/api/car/{vin}/"

        resp = await self.async_request("GET", path)
        if resp.status == 401:
            raise AuthenticationError("Not authorized to fetch car detail")
        if resp.status != 200:
            text = await resp.text()
            _LOGGER.debug("Failed to fetch car detail by VIN %s: %s %s", vin, resp.status, text)
            raise RequestError(f"Failed fetching car detail by VIN: {resp.status}")

        return await resp.json()

    async def async_get_latest_trip(self, vin: str) -> dict | None:
        """Retrieve the latest probe trip record for extra temperature telemetry."""
        vin = (vin or "").strip()
        if not vin:
            return None
        try:
            resp = await self.async_request("GET", f"/api/car/{vin}/probe/trips", params={"page_size": 1})
            if resp.status != 200:
                return None
            data = await resp.json()
            results = data.get("results") if isinstance(data, dict) else None
            if results and isinstance(results, list) and len(results) > 0:
                return results[0]
        except Exception as err:
            _LOGGER.debug("Could not fetch probe/trips for %s: %s", vin, err)
        return None

    async def async_list_timers(self, vin: str) -> list[dict]:
        resp = await self.async_request("GET", f"/api/car/{vin}/timers/")
        if resp.status != 200:
            raise RequestError(f"Failed fetching timers: {resp.status}")
        return await resp.json()

    async def async_create_timer(self, vin: str, timer: dict) -> dict:
        resp = await self.async_request("POST", f"/api/car/{vin}/timers/", json=timer)
        if resp.status not in (200, 201):
            raise RequestError(f"Failed creating timer: {resp.status}")
        return await resp.json()

    async def async_update_timer(self, vin: str, timer_id: int, timer: dict) -> dict:
        resp = await self.async_request("PATCH", f"/api/car/{vin}/timers/{timer_id}", json=timer)
        if resp.status != 200:
            raise RequestError(f"Failed updating timer: {resp.status}")
        return await resp.json()

    async def async_delete_timer(self, vin: str, timer_id: int) -> None:
        resp = await self.async_request("DELETE", f"/api/car/{vin}/timers/{timer_id}")
        if resp.status != 204:
            raise RequestError(f"Failed deleting timer: {resp.status}")

    async def async_send_command(
        self, vin: str, command_type: int, command_pin: str = None
    ) -> dict:
        """Send a command to a vehicle.
        
        Args:
            vin: Vehicle VIN
            command_type: Command type ID (1-16)
            command_pin: PIN code for commands that require it (7, 8, 9, 10, 11, 12, 13, 14, 16)
        
        Returns:
            Response dictionary from the API
        """
        vin = (vin or "").strip()
        if not vin:
            raise RequestError("VIN missing")

        path = f"/api/command/{vin}/"
        payload = {"vin": vin, "command_type": command_type}
        
        if command_pin:
            payload["command_pin"] = command_pin

        resp = await self.async_request("POST", path, json=payload)
        
        if resp.status == 401:
            raise AuthenticationError("Not authorized to send command")
        if resp.status == 403:
            raise RequestError("Command PIN not set up or invalid")
        if resp.status == 404:
            raise RequestError("Car not found")
        if resp.status != 200:
            text = await resp.text()
            _LOGGER.debug("Failed to send command to %s: %s %s", vin, resp.status, text)
            raise RequestError(f"Failed to send command: {resp.status}")

        return await resp.json()

    async def async_request_car_refresh(self, vin: str) -> dict:
        """Ask the vehicle to refresh its data on the OpenCARWINGS server."""
        return await self.async_send_command(vin, 1)
