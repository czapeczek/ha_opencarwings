import pytest

from custom_components.ha_opencarwings import button as button_mod


@pytest.mark.asyncio
async def test_refresh_button_created_and_has_unique_id():
    coord = type("C", (), {"data": None})()
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"coordinator": coord}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await button_mod.async_setup_entry(hass, entry, add)

    assert len(added) == 1
    btn = added[0]
    assert btn.unique_id == "ha_opencarwings_refresh_e1"


@pytest.mark.asyncio
async def test_refresh_button_triggers_coordinator_refresh(monkeypatch):
    class FakeCoordinator:
        def __init__(self):
            self.called = False

        async def async_request_refresh(self):
            self.called = True

    coord = FakeCoordinator()
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"coordinator": coord}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await button_mod.async_setup_entry(hass, entry, add)

    btn = added[0]
    await btn.async_press()

    assert coord.called is True