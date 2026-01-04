import pytest

from custom_components.ha_opencarwings import device_tracker as tracker_mod


@pytest.mark.asyncio
async def test_no_tracker_created_without_vin():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [{"model_name": "M1", "last_location": {"lat": "50.0", "lon": "20.0"}}]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    assert len(trackers) == 0


@pytest.mark.asyncio
async def test_tracker_available_false_when_no_location():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"cars": [{"vin": "VIN1", "model_name": "M1"}]}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    assert len(trackers) == 1
    t = trackers[0]
    assert t.unique_id == "ha_opencarwings_tracker_VIN1"
    assert t.available is False


@pytest.mark.asyncio
async def test_coordinator_refresh_before_creation():
    # coordinator with no data but an async_request_refresh that populates data
    class FakeCoordinator:
        def __init__(self):
            self.data = None

        async def async_request_refresh(self):
            self.data = [{"vin": "VIN1", "last_location": {"lat": "50.0", "lon": "20.0"}}]

    coord = FakeCoordinator()
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"coordinator": coord}}}})()

    trackers = []

    def tr_add(entities):
        trackers.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await tracker_mod.async_setup_entry(hass, entry, tr_add)

    assert len(trackers) == 1
    t = trackers[0]
    assert t.unique_id == "ha_opencarwings_tracker_VIN1"
    assert t.available is True