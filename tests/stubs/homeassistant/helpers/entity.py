class Entity:
    """Minimal entity base used in tests."""

    @property
    def name(self):
        raise NotImplementedError

    @property
    def unique_id(self):
        return None

    @property
    def extra_state_attributes(self):
        return {}

    @property
    def device_info(self):
        return {}

    @property
    def state(self):
        return None
