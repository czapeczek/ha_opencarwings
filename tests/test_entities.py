import pytest

from custom_components.ha_opencarwings import sensor as sensor_mod


@pytest.mark.asyncio
async def test_battery_and_location_and_switch_creation(monkeypatch):
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [{"vin": "VIN1", "model_name": "M1", "battery_level": 80, "last_location": {"lat": "50.0", "lon": "20.0"}, "ev_info": {"range_acon": 120, "range_acoff": 140, "soc": 80, "plugged_in": True, "charging": False}}]}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    # set up sensors
    await sensor_mod.async_setup_entry(hass, entry, add)

    # Expect CarListSensor + CarSensor + Battery plus EV sensors (location moved to device_tracker)
    # Car sensors + Last Updated: list + (car + battery + 5 sensors) + 1 = 9
    assert len(added) == 9

    battery = next(x for x in added if x.unique_id == "ha_opencarwings_battery_VIN1")
    assert battery.state == 80

    # new EV sensors
    soc = next(x for x in added if x.unique_id == "ha_opencarwings_soc_VIN1")
    assert soc.state == 80

    range_on = next(x for x in added if x.unique_id == "ha_opencarwings_range_acon_VIN1")
    assert range_on.state == 120

    range_off = next(x for x in added if x.unique_id == "ha_opencarwings_range_acoff_VIN1")
    assert range_off.state == 140

    plug = next(x for x in added if x.unique_id == "ha_opencarwings_plugged_in_VIN1")
    assert plug.state == "plugged"

    status = next(x for x in added if x.unique_id == "ha_opencarwings_status_VIN1")
    assert status.state == "idle"

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
    # VIN should be visible in attributes
    assert t.extra_state_attributes.get("vin") == "VIN1"
