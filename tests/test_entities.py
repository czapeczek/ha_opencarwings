import pytest

from custom_components.ha_opencarwings import sensor as sensor_mod


@pytest.mark.asyncio
async def test_battery_and_location_and_switch_creation(monkeypatch):
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [{"vin": "VIN1", "model_name": "M1", "battery_level": 80, "last_location": {"lat": "50.0", "lon": "20.0"}}]}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    # set up sensors
    await sensor_mod.async_setup_entry(hass, entry, add)

    # Expect CarListSensor + CarSensor + Battery + Location (4 entities)
    assert len(added) == 4

    battery = next(x for x in added if x.unique_id == "ha_opencarwings_battery_VIN1")
    assert battery.state == 80

    location = next(x for x in added if x.unique_id == "ha_opencarwings_location_VIN1")
    assert location.state == "50.0,20.0"

    # Now test switch creation
    sw_added = []

    def sw_add(entities):
        sw_added.extend(entities)

    from custom_components.ha_opencarwings import switch as switch_mod
    await switch_mod.async_setup_entry(hass, entry, sw_add)
    assert len(sw_added) == 1
    sw = sw_added[0]
    assert sw.unique_id == "ha_opencarwings_ac_VIN1"
