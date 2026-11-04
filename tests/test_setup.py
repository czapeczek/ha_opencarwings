import importlib

import pytest

from custom_components.ha_opencarwings.util import CarData
from tests.fakes import FakeConfigEntries, make_hass

module_init = importlib.import_module("custom_components.ha_opencarwings")


class FakeClient:
    pass


@pytest.mark.asyncio
async def test_setup_stores_cars_and_client(monkeypatch):
    seen = {}

    def _get_client(hass, base_url, api_token):
        seen["args"] = (base_url, api_token)
        return FakeClient()

    monkeypatch.setattr("custom_components.ha_opencarwings.api.get_client", _get_client)

    hass = make_hass(config_entries=FakeConfigEntries())
    entry = type("E", (), {
        "entry_id": "e1",
        "data": {"api_token": "tok", "api_base_url": "https://custom.example"},
        "title": "t",
    })()

    assert await module_init.async_setup_entry(hass, entry) is True

    # token and base URL come from the config entry
    assert seen["args"] == ("https://custom.example", "tok")

    stored = hass.data["ha_opencarwings"]["e1"]
    cars = stored["cars"]
    assert [c.vin for c in cars] == ["VIN1", "VIN2"]
    assert all(isinstance(c, CarData) for c in cars)
    # list entries are enriched with the detail endpoint
    assert cars[0].car_detail is not None
    assert cars[0].get_latest_car().odometer == 1000
    assert stored["client"].base_url == "https://custom.example"
    assert stored["coordinator"].last_update_time is not None


@pytest.mark.asyncio
async def test_options_override_entry_data(monkeypatch):
    seen = {}

    def _get_client(hass, base_url, api_token):
        seen["args"] = (base_url, api_token)
        return FakeClient()

    monkeypatch.setattr("custom_components.ha_opencarwings.api.get_client", _get_client)

    hass = make_hass(config_entries=FakeConfigEntries())
    entry = type("E", (), {
        "entry_id": "e1",
        "data": {"api_token": "old", "api_base_url": "https://old.example"},
        "options": {"api_token": "new", "api_base_url": "https://new.example"},
        "title": "t",
    })()

    assert await module_init.async_setup_entry(hass, entry) is True
    assert seen["args"] == ("https://new.example", "new")


@pytest.mark.asyncio
async def test_setup_continues_when_detail_enrichment_fails(monkeypatch, fake_cars_api):
    async def _fail(self, vin):
        raise RuntimeError("detail endpoint down")

    monkeypatch.setattr(fake_cars_api, "api_car_read", _fail)
    monkeypatch.setattr("custom_components.ha_opencarwings.api.get_client", lambda *a: FakeClient())

    hass = make_hass(config_entries=FakeConfigEntries())
    entry = type("E", (), {"entry_id": "e1", "data": {"api_token": "t"}, "title": "t"})()

    assert await module_init.async_setup_entry(hass, entry) is True
    cars = hass.data["ha_opencarwings"]["e1"]["cars"]
    assert [c.vin for c in cars] == ["VIN1", "VIN2"]
    assert all(c.car_detail is None for c in cars)


@pytest.mark.asyncio
async def test_setup_raises_auth_failed_on_401(monkeypatch, fake_cars_api):
    from homeassistant.exceptions import ConfigEntryAuthFailed
    from opencarwings_client import ApiException

    async def _unauthorized(self):
        raise ApiException(status=401, reason="Unauthorized")

    monkeypatch.setattr(fake_cars_api, "api_car_list", _unauthorized)
    monkeypatch.setattr("custom_components.ha_opencarwings.api.get_client", lambda *a: FakeClient())

    config_entries = FakeConfigEntries()
    hass = make_hass(config_entries=config_entries)
    entry = type("E", (), {"entry_id": "e1", "data": {"api_token": "bad"}, "title": "t"})()

    # Home Assistant turns this into a reauth flow
    with pytest.raises(ConfigEntryAuthFailed):
        await module_init.async_setup_entry(hass, entry)
    assert config_entries.forwarded is None


@pytest.mark.asyncio
async def test_setup_continues_on_other_api_errors(monkeypatch, fake_cars_api):
    from opencarwings_client import ApiException

    async def _server_error(self):
        raise ApiException(status=500, reason="Server error")

    monkeypatch.setattr(fake_cars_api, "api_car_list", _server_error)
    monkeypatch.setattr("custom_components.ha_opencarwings.api.get_client", lambda *a: FakeClient())

    config_entries = FakeConfigEntries()
    hass = make_hass(config_entries=config_entries)
    entry = type("E", (), {"entry_id": "e1", "data": {"api_token": "t"}, "title": "t"})()

    # Non-auth failures keep the integration loaded with no data
    assert await module_init.async_setup_entry(hass, entry) is True
    assert hass.data["ha_opencarwings"]["e1"]["cars"] == []
