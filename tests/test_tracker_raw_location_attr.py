import pytest

from custom_components.ha_opencarwings import device_tracker as tracker_mod


@pytest.mark.asyncio
async def test_last_location_raw_from_car_field():
    car = {"vin": "VIN1", "last_location": {"lat": "50.0", "lon": "20.0"}}
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [car]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    t = trackers[0]
    attrs = t.extra_state_attributes
    assert attrs.get("last_location_raw") == car["last_location"]
    assert attrs.get("last_location_source") == "last_location"


@pytest.mark.asyncio
async def test_last_location_raw_from_ev_info():
    car = {"vin": "VIN2", "ev_info": {"last_location": {"lat": "51.0", "lon": "21.0"}}}
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [car]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    t = trackers[0]
    attrs = t.extra_state_attributes
    assert attrs.get("last_location_raw") == car["ev_info"]["last_location"]
    assert attrs.get("last_location_source") == "ev_info.last_location"


@pytest.mark.asyncio
async def test_last_location_raw_none_when_missing():
    car = {"vin": "VIN3", "model_name": "M3"}
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [car]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    t = trackers[0]
    attrs = t.extra_state_attributes
    assert attrs.get("last_location_raw") is None
    assert attrs.get("last_location_source") is None