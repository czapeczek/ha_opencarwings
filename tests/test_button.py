import pytest

from custom_components.ha_opencarwings import button as button_mod


@pytest.mark.asyncio
async def test_refresh_button_created_and_has_unique_id():
    coord = type("C", (), {"data": None})()
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"coordinator": coord}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await button_mod.async_setup_entry(hass, entry, add)

    assert len(added) == 1
    btn = added[0]
    assert btn.unique_id == "ha_opencarwings_refresh_e1"


@pytest.mark.asyncio
async def test_refresh_button_triggers_coordinator_refresh(monkeypatch):
    class FakeCoordinator:
        def __init__(self):
            self.called = False

        async def async_request_refresh(self):
            self.called = True

    coord = FakeCoordinator()
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"coordinator": coord}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await button_mod.async_setup_entry(hass, entry, add)

    btn = added[0]
    await btn.async_press()

    assert coord.called is True


@pytest.mark.asyncio
async def test_car_refresh_button_created_and_has_unique_id():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"coordinator": None, "cars": [{"vin": "VIN1", "model_name": "M1"}]}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await button_mod.async_setup_entry(hass, entry, add)

    # there should be two buttons: per-entry + per-car
    assert len(added) == 2

    # find the car button
    car_btn = None
    for ent in added:
        if getattr(ent, "unique_id", "").startswith("ha_opencarwings_car_refresh_"):
            car_btn = ent
            break

    assert car_btn is not None
    assert car_btn.unique_id == "ha_opencarwings_car_refresh_VIN1"


@pytest.mark.asyncio
async def test_car_refresh_button_has_friendly_name():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"coordinator": None, "cars": [{"vin": "VIN1", "model_name": "M1", "nickname": "MyCar"}]}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await button_mod.async_setup_entry(hass, entry, add)

    # find car button
    car_btn = None
    for ent in added:
        if getattr(ent, "unique_id", "").startswith("ha_opencarwings_car_refresh_"):
            car_btn = ent
            break

    assert car_btn is not None
    assert car_btn.name == "Request data refresh for MyCar"


@pytest.mark.asyncio
async def test_car_refresh_button_falls_back_to_model_name():
    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"coordinator": None, "cars": [{"vin": "VIN1", "model_name": "M1"}]}}}})()

    added = []

    def add(entities):
        added.extend(entities)

    entry = type("E", (), {"entry_id": "e1"})()
    await button_mod.async_setup_entry(hass, entry, add)

    # find car button
    car_btn = None
    for ent in added:
        if getattr(ent, "unique_id", "").startswith("ha_opencarwings_car_refresh_"):
            car_btn = ent
            break

    assert car_btn is not None
    assert car_btn.name == "Request data refresh for M1"


@pytest.mark.asyncio
async def test_car_refresh_button_calls_api(monkeypatch):
    calls = []

    class MockClient:
        def __init__(self, hass):
            self.hass = hass

        async def async_request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            class R: pass
            return R()

    hass = type("H", (), {"data": {"ha_opencarwings": {"e1": {"client": MockClient(None), "cars": [{"vin": "VIN1", "model_name": "M1"}]}}}})()

    from custom_components.ha_opencarwings import button as button_mod
    entry = type("E", (), {"entry_id": "e1"})()

    added = []
    def add(entities):
        added.extend(entities)

    await button_mod.async_setup_entry(hass, entry, add)

    # find car button
    car_btn = None
    for ent in added:
        if getattr(ent, "unique_id", "").startswith("ha_opencarwings_car_refresh_"):
            car_btn = ent
            break

    assert car_btn is not None

    await car_btn.async_press()

    assert calls[0][0] == "POST"
    assert "/api/command/VIN1/" in calls[0][1]
    assert calls[0][2]["json"]["command_type"] == 1