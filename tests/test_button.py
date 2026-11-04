import pytest

from custom_components.ha_opencarwings import button as button_mod
from custom_components.ha_opencarwings.util import CarData
from tests.helpers import make_car


def _hass(**entry_data):
    return type("H", (), {"data": {"ha_opencarwings": {"e1": entry_data}}})()


async def _setup(hass):
    added = []
    entry = type("E", (), {"entry_id": "e1"})()
    await button_mod.async_setup_entry(hass, entry, added.extend)
    return added


def _by_prefix(added, prefix):
    return next(e for e in added if getattr(e, "unique_id", "").startswith(prefix))


@pytest.mark.asyncio
async def test_refresh_button_created_and_has_unique_id():
    added = await _setup(_hass(coordinator=type("C", (), {"data": None})()))

    assert len(added) == 1
    assert added[0].unique_id == "ha_opencarwings_refresh_e1"


@pytest.mark.asyncio
async def test_refresh_button_triggers_coordinator_refresh():
    class FakeCoordinator:
        called = False

        async def async_request_refresh(self):
            self.called = True

    coord = FakeCoordinator()
    added = await _setup(_hass(coordinator=coord))
    await added[0].async_press()

    assert coord.called is True


@pytest.mark.asyncio
async def test_per_car_buttons_created():
    added = await _setup(_hass(coordinator=None, cars=[make_car("VIN1")]))

    # per-entry refresh button + 11 per-car command buttons
    assert len(added) == 12
    assert _by_prefix(added, "ha_opencarwings_car_refresh_").unique_id == "ha_opencarwings_car_refresh_VIN1"
    assert len({e.unique_id for e in added}) == 12


@pytest.mark.asyncio
async def test_car_buttons_not_created_without_vin():
    added = await _setup(_hass(coordinator=None, cars=[CarData(vin="")]))

    assert len(added) == 1


@pytest.mark.asyncio
async def test_car_button_names_use_nickname_then_vin():
    added = await _setup(_hass(coordinator=None, cars=[make_car("VIN1", nickname="MyCar")]))
    assert _by_prefix(added, "ha_opencarwings_car_refresh_").name == "Request data refresh for MyCar"
    assert _by_prefix(added, "ha_opencarwings_car_chargestart_").name == "Charge start for MyCar"

    added = await _setup(_hass(coordinator=None, cars=[make_car("VIN1")]))
    assert _by_prefix(added, "ha_opencarwings_car_refresh_").name == "Request data refresh for VIN1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unique_id,command_type",
    [
        ("ha_opencarwings_car_refresh_VIN1", 1),
        ("ha_opencarwings_car_chargestart_VIN1", 2),
        ("ha_opencarwings_car_chargestart80_VIN1", 6),
        ("ha_opencarwings_car_doorlock_VIN1", 7),
        ("ha_opencarwings_car_doorunlock_VIN1", 8),
        ("ha_opencarwings_car_horn_VIN1", 9),
        ("ha_opencarwings_car_lights_VIN1", 10),
        ("ha_opencarwings_car_horn_lights_VIN1", 11),
        ("ha_opencarwings_car_stop_horn_lights_VIN1", 12),
        ("ha_opencarwings_car_remote_start_VIN1", 13),
        ("ha_opencarwings_car_remote_stop_VIN1", 14),
    ],
)
async def test_car_button_sends_command(fake_cars_api, unique_id, command_type):
    added = await _setup(_hass(client=object(), coordinator=None, cars=[make_car("VIN1")]))
    button = next(e for e in added if getattr(e, "unique_id", None) == unique_id)

    await button.async_press()

    assert [(vin, req.command_type) for vin, req in fake_cars_api.commands] == [("VIN1", command_type)]


@pytest.mark.asyncio
async def test_command_button_availability_follows_supported_commands():
    added = await _setup(_hass(coordinator=None, cars=[make_car("VIN1", supported_commands=[1, 2])]))

    assert _by_prefix(added, "ha_opencarwings_car_refresh_").is_available is True
    assert _by_prefix(added, "ha_opencarwings_car_chargestart80_").is_available is False


@pytest.mark.asyncio
async def test_command_button_error_propagates(monkeypatch, fake_cars_api):
    async def _fail(self, vin, request):
        raise RuntimeError("boom")

    monkeypatch.setattr(fake_cars_api, "api_command_create", _fail)
    added = await _setup(_hass(client=object(), coordinator=None, cars=[make_car("VIN1")]))

    with pytest.raises(RuntimeError):
        await _by_prefix(added, "ha_opencarwings_car_refresh_").async_press()
