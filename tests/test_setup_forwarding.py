import importlib

import pytest

from tests.fakes import FakeConfigEntries, make_hass

module = importlib.import_module("custom_components.ha_opencarwings")


@pytest.mark.asyncio
async def test_forward_entry_setups_and_unload(monkeypatch):
    monkeypatch.setattr("custom_components.ha_opencarwings.api.get_client", lambda *a: object())

    config_entries = FakeConfigEntries()
    hass = make_hass(config_entries=config_entries)
    entry = type("E", (), {"entry_id": "e1", "data": {"api_token": "t"}, "title": "t"})()

    assert await module.async_setup_entry(hass, entry) is True
    assert config_entries.forwarded[1] == module.PLATFORMS

    assert await module.async_unload_entry(hass, entry) is True
    assert config_entries.unloaded[1] == module.PLATFORMS
    assert "e1" not in hass.data["ha_opencarwings"]
