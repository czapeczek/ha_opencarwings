import pytest

from custom_components.ha_opencarwings import device_tracker as tracker_mod
from tests.helpers import make_car


@pytest.mark.asyncio
async def test_tracker_handles_location_formats():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [
        make_car("VIN1", location={"lat": "50.0", "lon": "20.0"}),
        make_car("VIN2", location={"lat": "51.5", "lon": "21.5"}, detail=False),
        # comma as decimal separator should be handled
        make_car("VIN3", location={"lat": "53,0", "lon": "23,0"}),
        # unparsable coordinates must not raise
        make_car("VIN4", location={"lat": "abc", "lon": "def"}),
    ]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    by_vin = {t.unique_id.split("_")[-1]: t for t in trackers}

    assert round(by_vin["VIN1"].latitude, 3) == 50.0
    assert round(by_vin["VIN1"].longitude, 3) == 20.0

    assert round(by_vin["VIN2"].latitude, 3) == 51.5
    assert round(by_vin["VIN2"].longitude, 3) == 21.5

    assert round(by_vin["VIN3"].latitude, 3) == 53.0
    assert round(by_vin["VIN3"].longitude, 3) == 23.0

    assert by_vin["VIN4"].latitude is None
    assert by_vin["VIN4"].available is False
