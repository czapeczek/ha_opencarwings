import os
import sys

# Ensure repo root is on sys.path so `custom_components` imports work
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Ensure that tests/stubs is prepended to sys.path so our minimal "homeassistant" stub is importable
STUBS = os.path.join(os.path.dirname(__file__), "stubs")
if STUBS not in sys.path:
    sys.path.insert(0, STUBS)


import pytest


@pytest.fixture(autouse=True)
def fake_cars_api(monkeypatch):
    """Route opencarwings_client.CarsApi to an in-memory fake for every test."""
    import opencarwings_client
    from tests.fakes import FakeCarsApi

    FakeCarsApi.commands = []
    monkeypatch.setattr(opencarwings_client, "CarsApi", FakeCarsApi)
    return FakeCarsApi
