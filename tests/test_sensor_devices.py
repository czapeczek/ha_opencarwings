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

    # We expect one CarListSensor plus two CarSensor entities
    assert len(added) == 3

    car_entities = [e for e in added if getattr(e, "device_info", None) and e.device_info.get("identifiers")]
    vins = [list(e.device_info["identifiers"])[0][1] for e in car_entities]
    assert set(vins) == {"VIN1", "VIN2"}

    # verify unique ids
    unique_ids = [e.unique_id for e in car_entities]
    assert "ha_opencarwings_car_VIN1" in unique_ids
    assert "ha_opencarwings_car_VIN2" in unique_ids
