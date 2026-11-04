from custom_components.ha_opencarwings import api


def test_get_client_sets_host_and_token():
    client = api.get_client(None, "https://custom.example", "secret")

    assert client.configuration.host == "https://custom.example"
    assert client.configuration.api_key["Personal API Key"] == "secret"
    assert client.configuration.api_key_prefix["Personal API Key"] == "Token"
    assert client.default_headers["User-Agent"] == "OpenCARWINGS-HomeAssistant/1.0"


def test_get_client_without_token_sets_no_credentials():
    for token in (None, ""):
        client = api.get_client(None, api.DEFAULT_API_BASE, token)

        assert "Personal API Key" not in client.configuration.api_key
        assert client.configuration.host == api.DEFAULT_API_BASE


def test_get_client_uses_integration_rest_client():
    from custom_components.ha_opencarwings.aioclient import RESTClientObject

    assert isinstance(api.get_client(None).rest_client, RESTClientObject)
