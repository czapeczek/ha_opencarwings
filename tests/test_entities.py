import pytest

from custom_components.ha_opencarwings import sensor as sensor_mod
from tests.helpers import make_car
from custom_components.ha_opencarwings.sensor import CAR_SENSORS


@pytest.mark.asyncio
async def test_battery_and_location_and_switch_creation(monkeypatch):
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [make_car("VIN1", location={"lat": "50.0", "lon": "20.0"}, ev_info={"range_acon": 120, "range_acoff": 140, "soc": 80, "plugged_in": True, "charging": False})]}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    # set up sensors
    await sensor_mod.async_setup_entry(hass, entry, add)

    # Expect CarListSensor plus the generic value sensors and
    # status, last_updated, last_requested and vin for the car
    assert len(added) == 1 + len(CAR_SENSORS) + 4

    # new EV sensors
    def _val(e):
        return getattr(e, "native_value", getattr(e, "state", None))

    soc = next(x for x in added if x.unique_id == "ha_opencarwings_soc_VIN1")
    assert _val(soc) == 80

    range_on = next(x for x in added if x.unique_id == "ha_opencarwings_range_acon_VIN1")
    assert _val(range_on) == 120

    range_off = next(x for x in added if x.unique_id == "ha_opencarwings_range_acoff_VIN1")
    assert _val(range_off) == 140

    plug = next(x for x in added if x.unique_id == "ha_opencarwings_plugged_in_VIN1")
    assert _val(plug) == "plugged"

    status = next(x for x in added if x.unique_id == "ha_opencarwings_status_VIN1")
    assert _val(status) == "idle"

    # Now test switch creation
    sw_added = []

    def sw_add(entities):
        sw_added.extend(entities)

    from custom_components.ha_opencarwings import switch as switch_mod
    await switch_mod.async_setup_entry(hass, entry, sw_add)
    assert len(sw_added) == 1
    sw = sw_added[0]
    assert sw.unique_id == "ha_opencarwings_ac_VIN1"

    # device_tracker should create a tracker for the car
    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    from custom_components.ha_opencarwings import device_tracker as tracker_mod
    await tracker_mod.async_setup_entry(hass, entry, tr_add)
    assert len(trackers) == 1
    t = trackers[0]
    assert t.unique_id == "ha_opencarwings_tracker_VIN1"
    assert t.latitude == 50.0
    assert t.longitude == 20.0
