from __future__ import annotations
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity

from . import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")
    cars = coordinator.data if coordinator and coordinator.data is not None else data.get("cars", [])

    entities = [CarTracker(entry.entry_id, coordinator, car.get("vin")) for car in cars]
    # Tests call entity methods directly; set hass on the entities for testability
    for ent in entities:
        ent.hass = hass
    async_add_entities(entities)

class CarTracker(TrackerEntity):
    def __init__(self, entry_id: str, coordinator=None, vin: str | None = None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._vin = vin
        self._car = None

    def _get_car(self) -> dict:
        if self._coordinator and self._coordinator.data is not None:
            for c in self._coordinator.data:
                if c.get("vin") == self._vin:
                    return c
            return {}
        return self._car or {}

    async def async_added_to_hass(self) -> None:
        # allow tests to set hass on the entity before this is called
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    @property
    def name(self) -> str:
        car = self._get_car()
        return f"{car.get('model_name') or f'Car {self._vin}'} Tracker"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_tracker_{self._vin}"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    def _get_lat_lon(self):
        car = self._get_car()
        loc = car.get("last_location") or car.get("location")
        if isinstance(loc, dict):
            lat = loc.get("lat") or loc.get("latitude")
            lon = loc.get("lon") or loc.get("longitude")
            if lat is not None and lon is not None:
                return float(lat), float(lon)
        return None, None

    @property
    def latitude(self) -> float | None:
        return self._get_lat_lon()[0]

    @property
    def longitude(self) -> float | None:
        return self._get_lat_lon()[1]

    @property
    def location_name(self) -> str | None:
        # optionally show a zone/description
        loc = self._get_car().get("last_location") or self._get_car().get("location")
        if isinstance(loc, dict):
            return loc.get("name") or loc.get("address")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Expose VIN and basic car data so it's visible on the entity
        car = self._get_car()
        return {"vin": self._vin, **car}

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name")}
