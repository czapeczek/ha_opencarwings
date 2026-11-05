from ..helpers.entity import Entity


class BinarySensorDeviceClass:
    BATTERY_CHARGING = "battery_charging"
    PLUG = "plug"
    POWER = "power"
    RUNNING = "running"


class BinarySensorEntity(Entity):
    """Minimal BinarySensorEntity stub for tests."""

    @property
    def is_on(self):
        return getattr(self, "_attr_is_on", None)

    @property
    def unique_id(self):
        return getattr(self, "_attr_unique_id", None)

    @property
    def device_class(self):
        return getattr(self, "_attr_device_class", None)

    @property
    def entity_category(self):
        return getattr(self, "_attr_entity_category", None)
