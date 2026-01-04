"""Async client for OpenCARWINGS API (JWT auth).

Provides methods to obtain and refresh JWT tokens and make authenticated requests.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiohttp import ClientResponse
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
        self._session = async_get_clientsession(hass)
        self._base = base_url.rstrip("/")
        self._access: Optional[str] = None
        self._refresh: Optional[str] = None
        self._lock = asyncio.Lock()

    def set_tokens(self, access: str | None, refresh: str | None) -> None:
        self._access = access
        self._refresh = refresh

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

    async def async_request(self, method: str, path: str, **kwargs) -> ClientResponse:
        url = f"{self._base}{path if path.startswith('/') else '/' + path}"
        headers = kwargs.pop("headers", {}) or {}

        if self._access:
            headers["Authorization"] = f"Bearer {self._access}"

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
