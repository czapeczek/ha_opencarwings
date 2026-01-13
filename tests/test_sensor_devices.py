import pytest

from custom_components.ha_opencarwings import sensor as sensor_mod


@pytest.mark.asyncio
async def test_sensor_creates_car_entities():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [{"vin": "VIN1", "model_name": "M1"}, {"vin": "VIN2", "model_name": "M2"}]}}}})()

    # Capture added entities
    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await sensor_mod.async_setup_entry(hass, entry, add)

    # We expect one CarListSensor plus EV sensors per car (CarSensor removed as redundant)
    # For two cars: 1 list + (range_on, range_off, soc, soc_display, charge_bars, cable, charging, charge_finish, quick_charging, ac_status, eco_mode, car_running, odometer, full_chg_time, limit_chg_time, obc_6kw, status, last_updated, last_requested, vin) * 2 = 1 + 20*2 = 41
    assert len(added) == 41

    # verify some unique ids for the new sensors (one example per car)
    unique_ids = [getattr(e, 'unique_id', None) for e in added]
    assert 'ha_opencarwings_range_acon_VIN1' in unique_ids
    assert 'ha_opencarwings_range_acoff_VIN2' in unique_ids

    car_entities = [e for e in added if getattr(e, "device_info", None) and e.device_info.get("identifiers")]
    vins = [list(e.device_info["identifiers"])[0][1] for e in car_entities]
    assert set(vins) == {"VIN1", "VIN2"}

    # verify unique ids for car sensors
    unique_ids = [e.unique_id for e in car_entities]

    # ensure per-car sensors (soc, range, plugged, last_updated, last_requested, vin) are associated with the device
    expected_ids = {
        'ha_opencarwings_soc_VIN1', 'ha_opencarwings_soc_display_VIN1', 'ha_opencarwings_range_acon_VIN1', 'ha_opencarwings_range_acoff_VIN1', 'ha_opencarwings_charge_bars_VIN1', 'ha_opencarwings_plugged_in_VIN1', 'ha_opencarwings_charging_VIN1', 'ha_opencarwings_charge_finish_VIN1', 'ha_opencarwings_quick_charging_VIN1', 'ha_opencarwings_ac_status_VIN1', 'ha_opencarwings_eco_mode_VIN1', 'ha_opencarwings_car_running_VIN1', 'ha_opencarwings_odometer_VIN1', 'ha_opencarwings_full_chg_time_VIN1', 'ha_opencarwings_limit_chg_time_VIN1', 'ha_opencarwings_obc_6kw_VIN1', 'ha_opencarwings_last_updated_VIN1', 'ha_opencarwings_last_requested_VIN1', 'ha_opencarwings_vin_VIN1',
        'ha_opencarwings_soc_VIN2', 'ha_opencarwings_soc_display_VIN2', 'ha_opencarwings_range_acon_VIN2', 'ha_opencarwings_range_acoff_VIN2', 'ha_opencarwings_charge_bars_VIN2', 'ha_opencarwings_plugged_in_VIN2', 'ha_opencarwings_charging_VIN2', 'ha_opencarwings_charge_finish_VIN2', 'ha_opencarwings_quick_charging_VIN2', 'ha_opencarwings_ac_status_VIN2', 'ha_opencarwings_eco_mode_VIN2', 'ha_opencarwings_car_running_VIN2', 'ha_opencarwings_odometer_VIN2', 'ha_opencarwings_full_chg_time_VIN2', 'ha_opencarwings_limit_chg_time_VIN2', 'ha_opencarwings_obc_6kw_VIN2', 'ha_opencarwings_last_updated_VIN2', 'ha_opencarwings_last_requested_VIN2', 'ha_opencarwings_vin_VIN2',
    }
    assert expected_ids.issubset(set(unique_ids))
