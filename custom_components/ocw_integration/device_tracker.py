from __future__ import annotations
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
try:
    from homeassistant.components.device_tracker import TrackerEntity
except Exception:  # pragma: no cover - tests running without hass stubs
    class TrackerEntity:  # type: ignore
        """Fallback base class used when TrackerEntity cannot be imported in tests."""
        pass

from . import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")

    # If we have a coordinator, prefer its data; ensure it's primed before use
    cars = data.get("cars", [])
    if coordinator:
        if getattr(coordinator, "data", None) is None and hasattr(coordinator, "async_request_refresh"):
            try:
                await coordinator.async_request_refresh()
            except Exception:  # pragma: no cover - network
                pass
        cars = getattr(coordinator, "data", None) or cars

    # Only create trackers for cars with a VIN
    entities = [CarTracker(entry.entry_id, car, coordinator=coordinator) for car in cars if car.get("vin")]
    # Tests call entity methods directly; set hass on the entities for testability
    for ent in entities:
        ent.hass = hass
    async_add_entities(entities)

class CarTracker(CoordinatorEntity, TrackerEntity):
    def __init__(self, entry_id: str, car: dict, coordinator=None) -> None:
        if coordinator is not None:
            CoordinatorEntity.__init__(self, coordinator)
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")

    def _get_car(self) -> dict:
        coordinator = getattr(self, "coordinator", None)
        if coordinator and getattr(coordinator, "data", None):
            for car in coordinator.data:
                if car.get("vin") == self._vin:
                    return {**self._car, **car}
        return self._car

    @property
    def name(self) -> str:
        # Prefer the car nickname, then model name, then a fallback that includes the VIN
        car = self._get_car()
        return f"{car.get('nickname') or car.get('model_name') or f'Car {self._vin}'} Tracker"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_tracker_{self._vin}"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    def _get_lat_lon(self):
        # Look for various forms of last location in the car data.
        car = self._get_car()
        loc = car.get("last_location") or car.get("location")
        if loc is None and isinstance(car.get("ev_info"), dict):
            loc = car.get("ev_info", {}).get("last_location")

        # If the last_location is a list, use the first element.
        if isinstance(loc, list) and len(loc) > 0:
            loc = loc[0]

        if isinstance(loc, dict):
            lat = loc.get("lat") or loc.get("latitude")
            lon = loc.get("lon") or loc.get("longitude")
            if lat is not None and lon is not None:
                # Accept commas as decimal separators ("53,0")
                try:
                    lat_f = float(str(lat).replace(",", "."))
                    lon_f = float(str(lon).replace(",", "."))
                    return lat_f, lon_f
                except Exception:
                    return None, None
        return None, None

    @property
    def latitude(self) -> float | None:
        return self._get_lat_lon()[0]

    @property
    def longitude(self) -> float | None:
        return self._get_lat_lon()[1]

    @property
    def available(self) -> bool:
        lat, lon = self._get_lat_lon()
        return lat is not None and lon is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Expose VIN and basic car data so it's visible on the entity, and
        # provide the raw last location under a single key for callers that
        # want to inspect the original payload.
        car = self._get_car()
        raw_loc = None
        raw_src = None
        if isinstance(car.get("last_location"), dict):
            raw_loc = car.get("last_location")
            raw_src = "last_location"
        elif isinstance(car.get("last_location"), list) and len(car.get("last_location")) > 0:
            raw_loc = car.get("last_location")[0]
            raw_src = "last_location"
        elif isinstance(car.get("location"), dict):
            raw_loc = car.get("location")
            raw_src = "location"
        elif isinstance(car.get("ev_info"), dict):
            raw_loc = car.get("ev_info", {}).get("last_location")
            if raw_loc is not None:
                raw_src = "ev_info.last_location"

        return {**car, "last_location_raw": raw_loc, "last_location_source": raw_src}

    @property
    def device_info(self) -> dict[str, Any]:
        # Attach the tracker to the car device so it appears under the same
        # device as the per-car buttons (use the VIN as the device identifier).
        car = self._get_car()
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": car.get("nickname") or car.get("model_name"),
            "manufacturer": car.get("make"),
            "model": car.get("model_name"),
        }
