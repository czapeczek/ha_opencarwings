import pytest

from custom_components.ha_opencarwings import binary_sensor as binary_sensor_mod
from custom_components.ha_opencarwings.binary_sensor import CAR_BINARY_SENSORS
from tests.helpers import make_car


async def _setup(cars):
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": cars}}}})()
    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await binary_sensor_mod.async_setup_entry(hass, entry, add)
    return {e.unique_id: e for e in added}


@pytest.mark.asyncio
async def test_binary_sensor_states_and_device_classes():
    by_id = await _setup([make_car(
        "VIN1",
        nickname="Leafy",
        ev_info={
            "plugged_in": True,
            "charging": True,
            "quick_charging": False,
            "ac_status": False,
            "charge_finish": False,
            "batt_heater_status": True,
            "eco_mode": True,
            "car_running": False,
            "obc_6kw_avail": True,
            "batt_heater_avail": False,
        },
    )])

    assert len(by_id) == len(CAR_BINARY_SENSORS)

    plug = by_id["ha_opencarwings_plugged_in_VIN1"]
    assert plug.is_on is True
    assert plug.device_class == "plug"
    assert plug.name == "Leafy Charging cable connected"

    charging = by_id["ha_opencarwings_charging_VIN1"]
    assert charging.is_on is True
    assert charging.device_class == "battery_charging"

    quick = by_id["ha_opencarwings_quick_charging_VIN1"]
    assert quick.is_on is False
    assert quick.device_class == "battery_charging"

    ac = by_id["ha_opencarwings_ac_status_VIN1"]
    assert ac.is_on is False
    assert ac.device_class == "power"

    charge_finish = by_id["ha_opencarwings_charge_finish_VIN1"]
    assert charge_finish.is_on is False
    assert charge_finish.device_class is None

    heater = by_id["ha_opencarwings_batt_heater_status_VIN1"]
    assert heater.is_on is True
    assert heater.device_class == "power"

    eco = by_id["ha_opencarwings_eco_mode_VIN1"]
    assert eco.is_on is True
    assert eco.device_class is None

    running = by_id["ha_opencarwings_car_running_VIN1"]
    assert running.is_on is False
    assert running.device_class == "running"
    assert running.entity_category is None

    obc = by_id["ha_opencarwings_obc_6kw_avail_VIN1"]
    assert obc.is_on is True
    assert obc.entity_category == "diagnostic"

    heater_avail = by_id["ha_opencarwings_batt_heater_avail_VIN1"]
    assert heater_avail.is_on is False
    assert heater_avail.entity_category == "diagnostic"

    assert list(ac.device_info["identifiers"])[0][1] == "VIN1"


@pytest.mark.asyncio
async def test_binary_sensor_unknown_when_value_missing():
    by_id = await _setup([make_car("VIN1", ev_info={})])
    assert by_id["ha_opencarwings_plugged_in_VIN1"].is_on is None
