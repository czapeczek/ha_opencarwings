import pytest

import custom_components.ha_opencarwings as init_mod


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


@pytest.mark.asyncio
async def test_refresh_service_for_entry(monkeypatch):
    # Create a fake coordinator that records refresh calls
    class FakeCoordinator:
        def __init__(self):
            self.called = False

        async def async_request_refresh(self):
            self.called = True

    coord = FakeCoordinator()

    class C:
        async def async_forward_entry_setups(self, *args, **kwargs):
            return None

    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"coordinator": coord}}}, "services": ServicesStub(), "config_entries": C()})()

    # Monkeypatch API client to avoid real network calls during setup
    class FakeAPI:
        def __init__(self, hass, base_url=None):
            pass

        async def async_get_cars(self):
            return []

        def set_tokens(self, access, refresh):
            return

    class FakeCoordinatorClass:
        def __init__(self, hass, logger, name, update_method, update_interval=None):
            self.called = False
            self.update_method = update_method

        async def async_request_refresh(self):
            self.called = True

    monkeypatch.setattr(init_mod, "OpenCarWingsAPI", FakeAPI)
    monkeypatch.setattr(init_mod, "DataUpdateCoordinator", FakeCoordinatorClass)

    entry = type("E", (), {"entry_id": "e1", "title": "e1", "data": {}})()
    # call setup which should register service
    await init_mod.async_setup_entry(hass, entry)

    # find the coordinator instance installed by setup
    real_coord = hass.data["ha_opencarwings"]["e1"].get("coordinator")

    # call the service targeting entry e1
    await hass.services.async_call("ha_opencarwings", "refresh", {"entry_id": "e1"})

    assert getattr(real_coord, "called", False) is True
    # call the service targeting entry e1
    await hass.services.async_call("ha_opencarwings", "refresh", {"entry_id": "e1"})

    assert coord.called is True


@pytest.mark.asyncio
async def test_refresh_service_refreshes_all(monkeypatch):
    class FakeCoordinator:
        def __init__(self):
            self.called = False

        async def async_request_refresh(self):
            self.called = True

    c1 = FakeCoordinator()
    c2 = FakeCoordinator()

    class C:
        async def async_forward_entry_setups(self, *args, **kwargs):
            return None

    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"coordinator": c1}, "e2": {"coordinator": c2}}}, "services": ServicesStub(), "config_entries": C()})()

    # Monkeypatch API client to avoid real network calls during setup
    class FakeAPI:
        def __init__(self, hass, base_url=None):
            pass

        async def async_get_cars(self):
            return []

        def set_tokens(self, access, refresh):
            return

    monkeypatch.setattr(init_mod, "OpenCarWingsAPI", FakeAPI)

    entry = type("E", (), {"entry_id": "e1", "title": "e1", "data": {}})()
    await init_mod.async_setup_entry(hass, entry)

    await hass.services.async_call("ha_opencarwings", "refresh", {})

    assert c1.called is True
    assert c2.called is True