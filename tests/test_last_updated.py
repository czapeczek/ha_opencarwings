import pytest
from datetime import datetime, timezone

from custom_components.ha_opencarwings import sensor as sensor_mod


@pytest.mark.asyncio
async def test_last_updated_sensor_reports_latest_timestamp_per_car():
    latest = "2026-01-04T13:00:00Z"
    # Create a fake coordinator that has a last_update_time so we can test the Last Requested sensor
    # Also include actual data so the sensor can find the cars
    coordinator = type("C", (), {
        "last_update_time": datetime(2026, 1, 4, 14, 0, 0, tzinfo=timezone.utc), 
        "data": [
            {"vin": "VIN1", "ev_info": {"last_updated": "2026-01-04T12:00:00Z"}, "location": {"last_updated": "2026-01-04T11:00:00Z"}},
            {"vin": "VIN2", "ev_info": {"last_updated": latest}}
        ]
    })()

    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [
        {"vin": "VIN1", "ev_info": {"last_updated": "2026-01-04T12:00:00Z"}, "location": {"last_updated": "2026-01-04T11:00:00Z"}},
        {"vin": "VIN2", "ev_info": {"last_updated": latest}}
    ], "coordinator": coordinator}}}})()

    # Capture added entities
    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await sensor_mod.async_setup_entry(hass, entry, add)

    def _val(e):
        return getattr(e, "native_value", getattr(e, "state", None))

    last1 = [e for e in added if getattr(e, "unique_id", None) == "ha_opencarwings_last_updated_VIN1"]
    last2 = [e for e in added if getattr(e, "unique_id", None) == "ha_opencarwings_last_updated_VIN2"]
    requested1 = [e for e in added if getattr(e, "unique_id", None) == "ha_opencarwings_last_requested_VIN1"]

    assert len(last1) == 1
    assert len(last2) == 1
    assert len(requested1) == 1
    assert _val(last1[0]) == "2026-01-04T12:00:00Z"
    assert _val(last2[0]) == latest

    # The Last Requested sensor should reflect the coordinator's last_update_time
    assert _val(requested1[0]) == "2026-01-04T14:00:00Z"

    # entity_category should be diagnostic (stubbed fallback allowed) and device_info present
    assert getattr(last1[0], "entity_category", None) is not None
    assert last1[0].device_info and list(list(last1[0].device_info["identifiers"])[0])[1] == "VIN1"


@pytest.mark.asyncio
async def test_last_requested_sensor_unknown_without_coordinator():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [{"vin": "VIN1", "ev_info": {"last_updated": "2026-01-04T12:00:00Z"}}]}}}})()

    # Capture added entities
    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await sensor_mod.async_setup_entry(hass, entry, add)

    requested = [e for e in added if getattr(e, "unique_id", None) == "ha_opencarwings_last_requested_VIN1"]
    assert len(requested) == 1
    def _val(e):
        return getattr(e, "native_value", getattr(e, "state", None))
    assert _val(requested[0]) == "unknown"


@pytest.mark.asyncio
async def test_last_updated_sensor_parses_timestamps_with_microseconds():
    """Test that the sensor correctly parses timestamps with microseconds (real API format)."""
    # Real API format includes microseconds
    ts_with_microseconds = "2026-01-05T00:16:10.419903Z"
    coordinator = type("C", (), {
        "last_update_time": datetime(2026, 1, 5, 0, 16, 10, tzinfo=timezone.utc), 
        "data": [
            {"vin": "VIN1", "ev_info": {"last_updated": ts_with_microseconds}, "location": {"last_updated": "2026-01-05T00:16:10.410231Z"}}
        ]
    })()

    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [
        {"vin": "VIN1", "ev_info": {"last_updated": ts_with_microseconds}, "location": {"last_updated": "2026-01-05T00:16:10.410231Z"}}
    ], "coordinator": coordinator}}}})()

    # Capture added entities
    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await sensor_mod.async_setup_entry(hass, entry, add)

    last1 = [e for e in added if getattr(e, "unique_id", None) == "ha_opencarwings_last_updated_VIN1"]
    
    assert len(last1) == 1
    def _val(e):
        return getattr(e, "native_value", getattr(e, "state", None))
    # The sensor should successfully parse and return the timestamp
    assert _val(last1[0]) == "2026-01-05T00:16:10.419903Z"
    assert _val(last1[0]) != "unknown"
