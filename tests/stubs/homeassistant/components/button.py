class ButtonEntity:
    """Minimal ButtonEntity stub for tests."""

    async def async_press(self):
        raise NotImplementedError

    @property
    def unique_id(self):
        return None

    @property
    def name(self):
        raise NotImplementedError

    @property
    def extra_state_attributes(self):
        return {}