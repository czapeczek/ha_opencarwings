import pytest

from custom_components.ha_opencarwings import sensor as sensor_mod


class FakeCoordinator:
    def __init__(self, data):
        self.data = data
        self._listeners = []

    def async_add_listener(self, listener):
        self._listeners.append(listener)

        def _remove():
            self._listeners.remove(listener)

        return _remove

    # helper to simulate an update
    def notify(self):
        for l in list(self._listeners):
            l()


@pytest.mark.asyncio
async def test_entities_update_on_coordinator_change():
    # initial data
    car1 = {"vin": "VIN1", "model_name": "M1", "ev_info": {"soc": 70}}
    coord = FakeCoordinator([car1])

    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"coordinator": coord}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await sensor_mod.async_setup_entry(hass, entry, add)

    # find SOC sensor
    soc = next(x for x in added if getattr(x, "unique_id", None) == "ha_opencarwings_soc_VIN1")
    assert soc.state == 70

    # update coordinator data
    car1_updated = {"vin": "VIN1", "model_name": "M1", "ev_info": {"soc": 80}}
    coord.data = [car1_updated]
    coord.notify()

    assert soc.state == 80