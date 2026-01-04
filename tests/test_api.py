import pytest

import asyncio

from custom_components.ha_opencarwings import api


class MockResponse:
    def __init__(self, status=200, json_data=None, text_data=""):
        self.status = status
        self._json = json_data or {}
        self._text = text_data

    async def json(self):
        return self._json

    async def text(self):
        return self._text


class MockSession:
    def __init__(self):
        self.requests = []
        self.posts = []
        self._request_calls = 0

    async def post(self, url, json=None, **kwargs):
        if self.posts:
            return self.posts.pop(0)
        return MockResponse(404, {}, "not mocked")

    async def request(self, method, url, headers=None, **kwargs):
        # return the next queued request response if present
        if self.requests:
            return self.requests.pop(0)
        return MockResponse(200, {"ok": True})


@pytest.mark.asyncio
async def test_obtain_token_success(monkeypatch):
    mock_session = MockSession()
    mock_session.posts.append(MockResponse(201, {"access": "a1", "refresh": "r1"}))

    monkeypatch.setattr(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        lambda hass: mock_session,
    )

    client = api.OpenCarWingsAPI(hass=None)
    data = await client.async_obtain_token("user", "pass")

    assert client._access == "a1"
    assert client._refresh == "r1"
    assert data["access"] == "a1"


@pytest.mark.asyncio
async def test_obtain_token_failure(monkeypatch):
    mock_session = MockSession()
    mock_session.posts.append(MockResponse(401, {}, "bad creds"))

    monkeypatch.setattr(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        lambda hass: mock_session,
    )

    client = api.OpenCarWingsAPI(hass=None)
    with pytest.raises(api.AuthenticationError):
        await client.async_obtain_token("user", "wrong")


@pytest.mark.asyncio
async def test_refresh_success(monkeypatch):
    mock_session = MockSession()
    mock_session.posts.append(MockResponse(200, {"access": "a2"}))

    monkeypatch.setattr(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        lambda hass: mock_session,
    )

    client = api.OpenCarWingsAPI(hass=None)
    client._refresh = "r1"
    access = await client.async_refresh_token()

    assert access == "a2"
    assert client._access == "a2"


@pytest.mark.asyncio
async def test_request_retries_on_401_and_refresh(monkeypatch):
    mock_session = MockSession()
    # initial request -> 401
    mock_session.requests.append(MockResponse(401, {}, "unauth"))
    # after refresh, successful request -> 200
    mock_session.requests.append(MockResponse(200, {"ok": True}))
    # refresh post returns new access
    mock_session.posts.append(MockResponse(200, {"access": "a3"}))

    monkeypatch.setattr(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        lambda hass: mock_session,
    )

    client = api.OpenCarWingsAPI(hass=None)
    client._access = "old"
    client._refresh = "r1"

    resp = await client.async_request("GET", "/api/car/")
    assert resp.status == 200


@pytest.mark.asyncio
async def test_request_network_error(monkeypatch):
    class BadSession(MockSession):
        async def request(self, method, url, headers=None, **kwargs):
            raise Exception("network")

    mock_session = BadSession()

    monkeypatch.setattr(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        lambda hass: mock_session,
    )

    client = api.OpenCarWingsAPI(hass=None)
    with pytest.raises(api.RequestError):
        await client.async_request("GET", "/api/car/")
