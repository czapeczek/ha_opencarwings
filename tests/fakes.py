"""Fakes for the opencarwings_client API used by the integration tests."""
from __future__ import annotations

from types import SimpleNamespace

from tests.helpers import make_detail_car, make_list_car


class FakeCarsApi:
    """Stand-in for opencarwings_client.CarsApi."""

    cars = ["VIN1", "VIN2"]
    commands: list[tuple] = []

    def __init__(self, client=None):
        self.client = client

    async def api_car_list(self):
        return [make_list_car(vin) for vin in self.cars]

    async def api_car_read(self, vin):
        return make_detail_car(vin, nickname=f"Car {vin}", odometer=1000)

    async def api_command_create(self, vin, request):
        type(self).commands.append((vin, request))
        return SimpleNamespace(car=make_detail_car(vin))


def make_hass(data=None, config_entries=None):
    async def _executor(func, *args):
        return func(*args)

    return type("H", (), {
        "data": data if data is not None else {},
        "config_entries": config_entries,
        "async_add_executor_job": staticmethod(_executor),
    })()


class FakeConfigEntries:
    def __init__(self):
        self.forwarded = None
        self.unloaded = None
        self.reauth = []

    async def async_forward_entry_setups(self, entry, platforms):
        self.forwarded = (entry, platforms)

    async def async_unload_platforms(self, entry, platforms):
        self.unloaded = (entry, platforms)
        return True

    def async_start_reauth(self, entry_id):
        self.reauth.append(entry_id)
