import pytest

import custom_components.ha_opencarwings as init_mod
from tests.fakes import FakeConfigEntries, make_hass


class ServicesStub:
    def __init__(self):
        self._handlers = {}

    def async_register(self, domain, service, handler):
        self._handlers[(domain, service)] = handler

    async def async_call(self, domain, service, data=None):
        handler = self._handlers.get((domain, service))
        if handler:
            class Call:
                def __init__(self, data):
                    self.data = data

            await handler(Call(data or {}))


class FakeCoordinatorClass:
    """Replaces DataUpdateCoordinator so refresh requests can be observed."""

    def __init__(self, hass, logger, name, update_method, update_interval=None):
        self.called = False
        self.data = []
        self.update_method = update_method

    async def async_config_entry_first_refresh(self):
        self.data = []

    async def async_request_refresh(self):
        self.called = True


def _hass():
    hass = make_hass(config_entries=FakeConfigEntries())
    hass.services = ServicesStub()
    return hass


def _entry(entry_id):
    return type("E", (), {"entry_id": entry_id, "title": entry_id, "data": {}})()


@pytest.mark.asyncio
async def test_refresh_service_for_entry(monkeypatch):
    monkeypatch.setattr("custom_components.ha_opencarwings.api.get_client", lambda *a: object())
    monkeypatch.setattr(init_mod, "DataUpdateCoordinator", FakeCoordinatorClass)

    hass = _hass()
    await init_mod.async_setup_entry(hass, _entry("e1"))
    await init_mod.async_setup_entry(hass, _entry("e2"))

    await hass.services.async_call("ha_opencarwings", "refresh", {"entry_id": "e1"})

    assert hass.data["ha_opencarwings"]["e1"]["coordinator"].called is True
    assert hass.data["ha_opencarwings"]["e2"]["coordinator"].called is False


@pytest.mark.asyncio
async def test_refresh_service_refreshes_all(monkeypatch):
    monkeypatch.setattr("custom_components.ha_opencarwings.api.get_client", lambda *a: object())
    monkeypatch.setattr(init_mod, "DataUpdateCoordinator", FakeCoordinatorClass)

    hass = _hass()
    await init_mod.async_setup_entry(hass, _entry("e1"))
    await init_mod.async_setup_entry(hass, _entry("e2"))

    await hass.services.async_call("ha_opencarwings", "refresh", {})

    assert hass.data["ha_opencarwings"]["e1"]["coordinator"].called is True
    assert hass.data["ha_opencarwings"]["e2"]["coordinator"].called is True


@pytest.mark.asyncio
async def test_refresh_service_ignores_unknown_entry(monkeypatch):
    monkeypatch.setattr("custom_components.ha_opencarwings.api.get_client", lambda *a: object())
    monkeypatch.setattr(init_mod, "DataUpdateCoordinator", FakeCoordinatorClass)

    hass = _hass()
    await init_mod.async_setup_entry(hass, _entry("e1"))

    await hass.services.async_call("ha_opencarwings", "refresh", {"entry_id": "nope"})

    assert hass.data["ha_opencarwings"]["e1"]["coordinator"].called is False
