import pytest

from custom_components.ha_opencarwings import device_tracker as tracker_mod
from tests.helpers import make_car


@pytest.mark.asyncio
async def test_extra_state_attributes_expose_location():
    car = make_car("VIN1", location={"lat": "50.0", "lon": "20.0"})
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [car]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    attrs = trackers[0].extra_state_attributes
    assert attrs.get("lat") == "50.0"
    assert attrs.get("lon") == "20.0"


@pytest.mark.asyncio
async def test_extra_state_attributes_without_location_values():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [make_car("VIN3")]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    attrs = trackers[0].extra_state_attributes
    assert attrs.get("lat") is None
    assert attrs.get("lon") is None
