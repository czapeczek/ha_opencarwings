import pytest
import importlib

from custom_components.ha_opencarwings import api
module_init = importlib.import_module("custom_components.ha_opencarwings")


class MockResponse:
    def __init__(self, status=200, json_data=None, text_data=""):
        self.status = status
        self._json = json_data or {}
        self._text = text_data

    async def json(self):
        return self._json

    async def text(self):
        return self._text


class MockClient:
    def __init__(self, hass=None):
        self._called = False

    async def async_request(self, method, path, **kwargs):
        return MockResponse(200, [{"vin": "VIN1", "model_name": "Model A"}, {"vin": "VIN2", "model_name": "Model B"}])

    def set_tokens(self, access, refresh):
        pass


@pytest.mark.asyncio
async def test_get_cars_api(monkeypatch):
    client = api.OpenCarWingsAPI(hass=None)

    # Monkeypatch the client's session to return the mocked response when called by async_get_cars
    async def _request(self, method, url, headers=None, **kwargs):
        return MockResponse(200, [{"vin": "VINX"}])

    client._session = type("S", (), {"request": _request})()

    cars = await client.async_get_cars()

    assert isinstance(cars, list)
    assert cars[0]["vin"] == "VINX"


@pytest.mark.asyncio
async def test_setup_stores_cars(monkeypatch):
    async def _forward(self, entry, platforms):
        return None

    async def _unload(self, entry, platforms):
        return True

    config_entries = type("C", (), {"async_start_reauth": lambda x: None, "async_forward_entry_setups": _forward, "async_unload_platforms": _unload})()
    hass = type("H", (), {"data": {}, "config_entries": config_entries})()

    # Monkeypatch OpenCarWingsAPI in the module to return our MockClient
    monkeypatch.setattr("custom_components.ha_opencarwings.OpenCarWingsAPI", lambda hass: MockClient(hass))

    entry = type("E", (), {"entry_id": "e1", "data": {"access_token": "a", "refresh_token": "r"}, "title": "t"})()

    ok = await module_init.async_setup_entry(hass, entry)

    assert ok
    assert hass.data["ha_opencarwings"]["e1"]["cars"][0]["vin"] == "VIN1"
