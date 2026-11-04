import pytest

from custom_components.ha_opencarwings import switch as switch_mod
from tests.helpers import make_car


@pytest.mark.asyncio
async def test_ac_switch_calls_api(fake_cars_api):
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"client": object(), "cars": [make_car("VIN1")]}}}})()
    entry = type("E", (), {"entry_id": "e1"})()

    added = []
    await switch_mod.async_setup_entry(hass, entry, added.extend)
    sw = added[0]
    assert sw.unique_id == "ha_opencarwings_ac_VIN1"

    await sw.async_turn_on()
    await sw.async_turn_off()

    assert [(vin, req.command_type) for vin, req in fake_cars_api.commands] == [("VIN1", 3), ("VIN1", 4)]


@pytest.mark.asyncio
async def test_ac_switch_updates_coordinator(monkeypatch, fake_cars_api):
    from types import SimpleNamespace

    returned = make_car("VIN1", nickname="Fresh").car_detail

    async def _create(self, vin, request):
        return SimpleNamespace(car=returned)

    monkeypatch.setattr(fake_cars_api, "api_command_create", _create)

    class Coordinator:
        def __init__(self, data):
            self.data = data

        def async_set_updated_data(self, data):
            self.data = data

    coord = Coordinator([make_car("VIN1", detail=False)])
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"client": object(), "coordinator": coord, "cars": coord.data}}}})()
    entry = type("E", (), {"entry_id": "e1"})()

    added = []
    await switch_mod.async_setup_entry(hass, entry, added.extend)
    await added[0].async_turn_on()

    assert coord.data[0].car_detail is returned
