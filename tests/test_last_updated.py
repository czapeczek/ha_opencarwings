import pytest

from custom_components.ha_opencarwings import sensor as sensor_mod


@pytest.mark.asyncio
async def test_last_updated_sensor_reports_latest_timestamp_per_car():
    latest = "2026-01-04T13:00:00Z"
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [
        {"vin": "VIN1", "ev_info": {"last_updated": "2026-01-04T12:00:00Z"}, "location": {"last_updated": "2026-01-04T11:00:00Z"}},
        {"vin": "VIN2", "ev_info": {"last_updated": latest}}
    ]}}}})()

    # Capture added entities
    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await sensor_mod.async_setup_entry(hass, entry, add)

    last1 = [e for e in added if getattr(e, "unique_id", None) == "ha_opencarwings_last_updated_VIN1"]
    last2 = [e for e in added if getattr(e, "unique_id", None) == "ha_opencarwings_last_updated_VIN2"]
    assert len(last1) == 1
    assert len(last2) == 1
    assert last1[0].state == "2026-01-04T12:00:00Z"
    assert last2[0].state == latest

    # entity_category should be diagnostic (stubbed fallback allowed) and device_info present
    assert getattr(last1[0], "entity_category", None) is not None
    assert last1[0].device_info and list(list(last1[0].device_info["identifiers"])[0])[1] == "VIN1"