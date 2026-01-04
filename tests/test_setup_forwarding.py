import pytest
import asyncio

import importlib
module = importlib.import_module("custom_components.ha_opencarwings")


@pytest.mark.asyncio
async def test_forward_entry_setups_and_unload(monkeypatch):
    calls = {}

    async def async_forward_entry_setups(self, entry, platforms):
        calls['forward'] = (entry, platforms)

    async def async_unload_platforms(self, entry, platforms):
        calls['unload'] = (entry, platforms)
        return True

    # hass stub with config_entries having the methods
    config_entries = type("C", (), {
        "async_forward_entry_setups": async_forward_entry_setups,
        "async_unload_platforms": async_unload_platforms,
        "async_start_reauth": lambda x: None,
    })()

    hass = type("H", (), {"data": {}, "config_entries": config_entries})()

    entry = type("E", (), {"entry_id": "e1", "data": {"access_token": "a", "refresh_token": "r"}, "title": "t"})()

    # Monkeypatch the OpenCarWingsAPI to avoid real calls
    class MockClient:
        def __init__(self, hass):
            pass

        async def async_request(self, method, path, **kwargs):
            class R: status = 200
            async def json():
                return []
            R.json = json
            return R

        def set_tokens(self, access, refresh):
            pass

    monkeypatch.setattr(module, "OpenCarWingsAPI", MockClient)

    ok = await module.async_setup_entry(hass, entry)
    assert ok is True
    assert 'forward' in calls
    assert calls['forward'][1] == module.PLATFORMS

    # Now unload
    res = await module.async_unload_entry(hass, entry)
    assert res is True
    assert 'unload' in calls
    assert calls['unload'][1] == module.PLATFORMS
