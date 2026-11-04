class HomeAssistantError(Exception):
    """Minimal stub for the Home Assistant base exception."""


class ConfigEntryAuthFailed(HomeAssistantError):
    """Raised when credentials are invalid and reauthentication is needed."""
