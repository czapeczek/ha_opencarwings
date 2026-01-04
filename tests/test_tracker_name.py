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