import pytest

from custom_components.ha_opencarwings import device_tracker as tracker_mod


@pytest.mark.asyncio
async def test_tracker_handles_various_location_formats():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [
        {"vin": "VIN1", "last_location": {"lat": "50.0", "lon": "20.0"}},
        {"vin": "VIN2", "location": {"latitude": "51.5", "longitude": "21.5"}},
        {"vin": "VIN3", "last_location": [{"lat": "52.0", "lon": "22.0"}]},
        {"vin": "VIN4", "ev_info": {"last_location": {"lat": "53,0", "lon": "23,0"}}},
    ]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    # Build map of vin->tracker
    by_vin = {t.unique_id.split("_")[-1]: t for t in trackers}

    assert round(by_vin["VIN1"].latitude, 3) == 50.0
    assert round(by_vin["VIN1"].longitude, 3) == 20.0

    assert round(by_vin["VIN2"].latitude, 3) == 51.5
    assert round(by_vin["VIN2"].longitude, 3) == 21.5

    assert round(by_vin["VIN3"].latitude, 3) == 52.0
    assert round(by_vin["VIN3"].longitude, 3) == 22.0

    # comma as decimal separator should be handled
    assert round(by_vin["VIN4"].latitude, 3) == 53.0
    assert round(by_vin["VIN4"].longitude, 3) == 23.0