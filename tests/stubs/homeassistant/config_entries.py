class ConfigFlow:
    """Minimal stub for config flow base class that accepts kwargs like `domain`.

    Provides minimal async helper methods used by tests: `async_create_entry` and
    `async_show_form`.
    """

    def __init_subclass__(cls, **kwargs):
        # Accept and ignore keywords used by Home Assistant (e.g., domain="...")
        return super().__init_subclass__()

    def async_create_entry(self, *, title: str, data: dict):
        # Simulate Home Assistant's return shape for successful creation
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(self, *, step_id: str, data_schema=None, errors=None):
        return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}


class ConfigEntry:
    """Minimal stub representing a config entry."""

    def __init__(self, entry_id: str = "test", title: str = "test", data: dict | None = None):
        self.entry_id = entry_id
        self.title = title
        self.data = data or {}


class OptionsFlow:
    """Minimal stub for options flow base class."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    def async_create_entry(self, *, title: str, data: dict):
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(self, *, step_id: str, data_schema=None, errors=None):
        return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}
