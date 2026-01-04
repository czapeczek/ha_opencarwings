import pytest

from custom_components.ha_opencarwings.config_flow import OpenCARWINGSConfigFlow
from custom_components.ha_opencarwings import config_flow as cfg


class MockClient:
    def __init__(self, hass=None, base_url=None):
        self.base_url = base_url

    async def async_obtain_token(self, username, password):
        if username == "good":
            return {"access": "ax", "refresh": "rx"}
        raise Exception("auth")


@pytest.mark.asyncio
async def test_config_flow_success(monkeypatch):
    monkeypatch.setattr(cfg, "OpenCarWingsAPI", MockClient)

    flow = OpenCARWINGSConfigFlow()
    result = await flow.async_step_user({"username": "good", "password": "p", "api_base_url": "https://custom.example"})

    assert result["type"] == "create_entry"
    assert result["data"]["username"] == "good"
    assert result["data"]["access_token"] == "ax"
    assert result["data"]["api_base_url"] == "https://custom.example"


@pytest.mark.asyncio
async def test_config_flow_scan_interval_selected(monkeypatch):
    monkeypatch.setattr(cfg, "OpenCarWingsAPI", MockClient)

    flow = OpenCARWINGSConfigFlow()
    # provide explicit scan_interval and ensure it's persisted
    result = await flow.async_step_user({"username": "good", "password": "p", "scan_interval": 1})

    assert result["type"] == "create_entry"
    assert result["data"]["scan_interval"] == 1


@pytest.mark.asyncio
async def test_config_flow_auth_failure(monkeypatch):
    monkeypatch.setattr(cfg, "OpenCarWingsAPI", MockClient)

    flow = OpenCARWINGSConfigFlow()
    result = await flow.async_step_user({"username": "bad", "password": "p"})

    # On auth failure, the form is shown with errors
    assert result["type"] == "form"
    assert "base" in result.get("errors", {})
