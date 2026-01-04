from __future__ import annotations
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity

from . import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    cars = data.get("cars", [])
    entities = [CarTracker(entry.entry_id, car) for car in cars]
    # Tests call entity methods directly; set hass on the entities for testability
    for ent in entities:
        ent.hass = hass
    async_add_entities(entities)

class CarTracker(TrackerEntity):
    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")

    @property
    def name(self) -> str:
        return f"{self._car.get('model_name') or f'Car {self._vin}'} Tracker"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_tracker_{self._vin}"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    def _get_lat_lon(self):
        loc = self._car.get("last_location") or self._car.get("location")
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
        # opcjonalnie: pokaże nazwę strefy / opis
        loc = self._car.get("last_location") or self._car.get("location")
        if isinstance(loc, dict):
            return loc.get("name") or loc.get("address")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Expose VIN and basic car data so it's visible on the entity
        return {"vin": self._vin, **self._car}

    @property
    def device_info(self) -> dict[str, Any]:
        # Create a separate device for the tracker itself (not the car device).
        # Use a distinct identifier to prevent the tracker being grouped under
        # the car device while keeping a friendly device name (nickname or model).
        return {
            "identifiers": {(DOMAIN, f"tracker_{self._vin}" )},
            "name": self._car.get("nickname") or self._car.get("model_name"),
        }