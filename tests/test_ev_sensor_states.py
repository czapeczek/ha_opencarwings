import pytest

from custom_components.ha_opencarwings import sensor as sensor_mod


@pytest.mark.asyncio
async def test_ev_sensor_states():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [{
        "vin": "VIN1",
        "model_name": "M1",
        "battery_level": 80,
        "odometer": 12345,
        "ev_info": {
            "range_acon": 120,
            "range_acoff": 140,
            "soc": 80,
            "soc_display": 79,
            "charge_bars": 5,
            "plugged_in": True,
            "charging": True,
            "charge_finish": False,
            "quick_charging": True,
            "ac_status": True,
            "eco_mode": True,
            "car_running": False,
            "full_chg_time": 30,
            "limit_chg_time": 60,
            "obc_6kw": 1,
        }
    }]}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await sensor_mod.async_setup_entry(hass, entry, add)

    # verify some of the new sensors return expected states
    def _val(e):
        return getattr(e, "native_value", getattr(e, "state", None))

    charge_bars = next(x for x in added if x.unique_id == "ha_opencarwings_charge_bars_VIN1")
    assert _val(charge_bars) == 5

    soc_display = next(x for x in added if x.unique_id == "ha_opencarwings_soc_display_VIN1")
    assert _val(soc_display) == 79

    odom = next(x for x in added if x.unique_id == "ha_opencarwings_odometer_VIN1")
    assert _val(odom) == 12345

    # Also ensure a string-valued odometer is coerced to int
    hass2 = type("H", (), {"data": {"ha_opencarwings": {"e2": {"cars": [{
        "vin": "VIN2",
        "model_name": "M2",
        "odometer": "54321",
    }]}}}})()

    added2 = []

    def add2(entities):
        added2.extend(entities)

    entry2 = type("E", (), {"entry_id": "e2"})()
    await sensor_mod.async_setup_entry(hass2, entry2, add2)

    odom2 = next(x for x in added2 if x.unique_id == "ha_opencarwings_odometer_VIN2")
    assert _val(odom2) == 54321

    eco = next(x for x in added if x.unique_id == "ha_opencarwings_eco_mode_VIN1")
    assert _val(eco) is True

    running = next(x for x in added if x.unique_id == "ha_opencarwings_car_running_VIN1")
    assert _val(running) is False

    charging = next(x for x in added if x.unique_id == "ha_opencarwings_charging_VIN1")
    assert _val(charging) is True

    charge_finish = next(x for x in added if x.unique_id == "ha_opencarwings_charge_finish_VIN1")
    assert _val(charge_finish) is False

    quick = next(x for x in added if x.unique_id == "ha_opencarwings_quick_charging_VIN1")
    assert _val(quick) is True

    ac = next(x for x in added if x.unique_id == "ha_opencarwings_ac_status_VIN1")
    assert _val(ac) is True

    full = next(x for x in added if x.unique_id == "ha_opencarwings_full_chg_time_VIN1")
    assert _val(full) == 30

    limit = next(x for x in added if x.unique_id == "ha_opencarwings_limit_chg_time_VIN1")
    assert _val(limit) == 60

    obc = next(x for x in added if x.unique_id == "ha_opencarwings_obc_6kw_VIN1")
    assert _val(obc) == 1

    # status sensor should reflect charging first
    status = next(x for x in added if x.unique_id == "ha_opencarwings_status_VIN1")
    assert _val(status) == "charging"
