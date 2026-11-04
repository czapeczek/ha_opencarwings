import pytest

from opencarwings_client import ApiException

from custom_components.ha_opencarwings import config_flow as cfg
from custom_components.ha_opencarwings.config_flow import OpenCARWINGSConfigFlow
from tests.fakes import make_hass


class FakeClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeAccountApi:
    error = None

    def __init__(self, client):
        pass

    async def account_detail_list(self):
        if type(self).error:
            raise type(self).error
        return type("Account", (), {"username": "alice"})()


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    FakeAccountApi.error = None
    monkeypatch.setattr(cfg, "get_client", lambda hass, base, token: FakeClient())
    monkeypatch.setattr(cfg.opencarwings_client, "AccountApi", FakeAccountApi)


def _flow():
    flow = OpenCARWINGSConfigFlow()
    flow.hass = make_hass()
    return flow


@pytest.mark.asyncio
async def test_config_flow_success():
    result = await _flow().async_step_user({"token": "tok", "api_base_url": "https://custom.example"})

    assert result["type"] == "create_entry"
    assert result["title"] == "alice"
    assert result["data"]["api_token"] == "tok"
    assert result["data"]["api_base_url"] == "https://custom.example"


@pytest.mark.asyncio
async def test_config_flow_scan_interval_selected():
    result = await _flow().async_step_user({"token": "tok", "scan_interval": 1})

    assert result["type"] == "create_entry"
    assert result["data"]["scan_interval"] == 1


@pytest.mark.asyncio
async def test_config_flow_shows_form_without_input():
    result = await _flow().async_step_user()

    assert result["type"] == "form"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_config_flow_auth_failure():
    FakeAccountApi.error = ApiException(status=401, reason="Unauthorized")

    result = await _flow().async_step_user({"token": "bad"})

    assert result["type"] == "form"
    assert result["errors"] == {"base": "auth"}


@pytest.mark.asyncio
async def test_config_flow_unexpected_error():
    FakeAccountApi.error = RuntimeError("boom")

    result = await _flow().async_step_user({"token": "tok"})

    assert result["type"] == "form"
    assert result["errors"] == {"base": "unknown"}
