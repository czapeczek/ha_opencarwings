import asyncio

class UpdateFailed(Exception):
    pass

class DataUpdateCoordinator:
    def __init__(self, hass, logger, name: str, update_method, update_interval=None):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_method = update_method
        self.update_interval = update_interval
        self.data = None
        self._listeners = []

    async def async_config_entry_first_refresh(self):
        # perform initial fetch
        self.data = await self.update_method()

    def async_add_listener(self, listener):
        self._listeners.append(listener)

        def _remove():
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return _remove

    async def async_request_refresh(self):
        self.data = await self.update_method()
        for listener in list(self._listeners):
            listener()
