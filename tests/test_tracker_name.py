import pytest

from custom_components.ha_opencarwings import device_tracker as tracker_mod


@pytest.mark.asyncio
async def test_tracker_name_uses_nickname_and_device_name():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [{"vin": "VIN1", "nickname": "MyCar", "model_name": "M1", "last_location": {"lat": "50.0", "lon": "20.0"}}]}}}})()

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
    # tracker device should have its own identifier (not the car VIN identifier)
    assert list(t.device_info["identifiers"])[0][1] == "tracker_VIN1"


@pytest.mark.asyncio
async def test_two_car_trackers_have_unique_devices():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [{"vin": "VIN1", "nickname": "MyCar", "model_name": "M1", "last_location": {"lat": "50.0", "lon": "20.0"}}, {"vin": "VIN2", "nickname": "Other", "model_name": "M2", "last_location": {"lat": "51.0", "lon": "21.0"}}]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    assert len(trackers) == 2
    ids = {list(t.device_info["identifiers"])[0][1] for t in trackers}
    assert ids == {"tracker_VIN1", "tracker_VIN2"}


@pytest.mark.asyncio
async def test_tracker_name_falls_back_to_model_and_no_vin_in_name():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [{"vin": "VIN1", "model_name": "M1", "last_location": {"lat": "50.0", "lon": "20.0"}}]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    assert len(trackers) == 1
    t = trackers[0]
    assert t.name == "M1 Tracker"
    assert "VIN1" not in t.name