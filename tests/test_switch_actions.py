import pytest


@pytest.mark.asyncio
async def test_ac_switch_calls_api(monkeypatch):
    # Create hass with data and a client stub
    calls = []

    class MockClient:
        def __init__(self, hass):
            self.hass = hass

        async def async_request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            class R: pass
            return R()

    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"client": MockClient(None), "cars": [{"vin": "VIN1", "model_name": "M1"}]}}}})()

    from custom_components.ha_opencarwings import switch as switch_mod
    entry = type("E", (), {"entry_id": "e1"})()

    added = []
    def add(entities):
        added.extend(entities)

    await switch_mod.async_setup_entry(hass, entry, add)
    sw = added[0]

    # turn on
    await sw.async_turn_on()
    assert calls[0][0] == "POST"
    assert "/api/command/VIN1/" in calls[0][1]

    # turn off
    await sw.async_turn_off()
    assert calls[1][0] == "POST"
    assert "/api/command/VIN1/" in calls[1][1]
