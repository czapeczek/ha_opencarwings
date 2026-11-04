import pytest

from custom_components.ha_opencarwings import device_tracker as tracker_mod
from tests.helpers import make_car

LOC = {"lat": "50.0", "lon": "20.0"}


@pytest.mark.asyncio
async def test_tracker_name_uses_nickname_and_device_name():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [make_car("VIN1", nickname="MyCar", location=LOC)]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    assert len(trackers) == 1
    t = trackers[0]
    assert t.unique_id == "ha_opencarwings_tracker_VIN1"
    assert t.name == "MyCar Tracker"
    assert t.device_info["name"] == "MyCar"
    # tracker should be attached to the car device (use VIN identifier)
    assert list(t.device_info["identifiers"])[0][1] == "VIN1"


@pytest.mark.asyncio
async def test_two_car_trackers_have_unique_devices():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [
        make_car("VIN1", nickname="MyCar", location=LOC),
        make_car("VIN2", nickname="Other", location={"lat": "51.0", "lon": "21.0"}),
    ]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    assert len(trackers) == 2
    ids = {list(t.device_info["identifiers"])[0][1] for t in trackers}
    assert ids == {"VIN1", "VIN2"}


@pytest.mark.asyncio
async def test_tracker_name_falls_back_to_vin_when_no_nickname():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [make_car("VIN1", location=LOC)]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    assert len(trackers) == 1
    t = trackers[0]
    assert t.name == "Car VIN1 Tracker"
    assert t.device_info["name"] == "VIN1"
