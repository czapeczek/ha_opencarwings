class SwitchEntity:
    """Minimal SwitchEntity stub."""

    @property
    def is_on(self):
        return False

    async def async_turn_on(self, **kwargs):
        raise NotImplementedError

    async def async_turn_off(self, **kwargs):
        raise NotImplementedError
