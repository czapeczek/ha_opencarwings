import pytest

from custom_components.ha_opencarwings.config_flow import OpenCARWINGSConfigFlow
from custom_components.ha_opencarwings import config_flow as cfg


class MockClient:
    def __init__(self, hass=None):
        pass

    async def async_obtain_token(self, username, password):
        if username == "good":
            return {"access": "ax", "refresh": "rx"}
        raise Exception("auth")


@pytest.mark.asyncio
async def test_config_flow_success(monkeypatch):
    monkeypatch.setattr(cfg, "OpenCarWingsAPI", MockClient)

    flow = OpenCARWINGSConfigFlow()
    result = await flow.async_step_user({"username": "good", "password": "p"})

    assert result["type"] == "create_entry"
    assert result["data"]["username"] == "good"
    assert result["data"]["access_token"] == "ax"


@pytest.mark.asyncio
async def test_config_flow_auth_failure(monkeypatch):
    monkeypatch.setattr(cfg, "OpenCarWingsAPI", MockClient)

    flow = OpenCARWINGSConfigFlow()
    result = await flow.async_step_user({"username": "bad", "password": "p"})

    # On auth failure, the form is shown with errors
    assert result["type"] == "form"
    assert "base" in result.get("errors", {})
