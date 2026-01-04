from homeassistant import config_entries

class OpenCARWINGSConfigFlow(config_entries.ConfigFlow, domain="ha_opencarwings"):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        return self.async_create_entry(
            title="OpenCARWINGS Integration",
            data={}
        )