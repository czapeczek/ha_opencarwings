from __future__ import annotations
from typing import Any

from homeassistant.components.device_tracker import SourceType

# config_entry may not be available in minimal test stubs; provide a fallback TrackerEntity
try:
    from homeassistant.components.device_tracker.config_entry import TrackerEntity
except Exception:  # pragma: no cover - tests may not provide this
    class TrackerEntity:  # minimal fallback
        def async_on_remove(self, _):
            return
        def async_add_listener(self, _):
            return (lambda: None)


from . import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")

    # Try to force a coordinator refresh before creating entities when possible
    if coordinator and coordinator.data is None:
        try:
            # Request refresh to populate coordinator.data. Different coordinator
            # implementations used in tests might provide either
            # `async_config_entry_first_refresh` or `async_request_refresh`.
            if hasattr(coordinator, "async_config_entry_first_refresh"):
                await coordinator.async_config_entry_first_refresh()
            elif hasattr(coordinator, "async_request_refresh"):
                await coordinator.async_request_refresh()
        except Exception:
            # ignore refresh errors and fall back to cached cars if present
            pass

    cars = coordinator.data if coordinator and coordinator.data is not None else data.get("cars", [])

    entities = []
    for car in cars:
        vin = car.get("vin")
        # skip creating trackers for cars without a valid VIN
        if not vin:
            continue
        ent = CarTracker(entry.entry_id, coordinator, vin, car=car)
        # Tests call entity methods directly; set hass on the entities for testability
        ent.hass = hass
        entities.append(ent)

    async_add_entities(entities)

class CarTracker(TrackerEntity):
    def __init__(self, entry_id: str, coordinator=None, vin: str | None = None, car: dict | None = None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._vin = vin
        # store initial car data if available (tests provide this via hass.data)
        self._car = car or {}

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
        # Prefer nickname when available; fall back to model name. Avoid showing "Car" and VIN in the visible name.
        visible = car.get("nickname") or car.get("model_name") or "Tracker"
        return f"{visible} Tracker"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_tracker_{self._vin}"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    def _get_lat_lon(self):
        car = self._get_car()

        def parse_loc(loc):
            # Accept dicts with 'lat'/'lon' or 'latitude'/'longitude', strings or numbers, or lists containing such dicts
            if isinstance(loc, dict):
                lat = loc.get("lat") if loc.get("lat") is not None else loc.get("latitude")
                lon = loc.get("lon") if loc.get("lon") is not None else loc.get("longitude")
                if lat is None or lon is None:
                    return None, None
                try:
                    return float(str(lat).replace(',', '.')), float(str(lon).replace(',', '.'))
                except Exception:
                    return None, None
            if isinstance(loc, (list, tuple)) and len(loc) > 0:
                return parse_loc(loc[0])
            return None, None

        # Try several possible locations in order of expected usefulness
        candidates = [car.get("last_location"), car.get("location")]
        # Some APIs may include a nested 'last_location' in other fields
        ev = car.get("ev_info") or {}
        if ev.get("last_location"):
            candidates.append(ev.get("last_location"))
        for loc in candidates:
            lat, lon = parse_loc(loc)
            if lat is not None and lon is not None:
                return lat, lon
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
    def available(self) -> bool:
        """Return True when the tracker has a valid lat/lon."""
        lat, lon = self._get_lat_lon()
        return lat is not None and lon is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Expose VIN and basic car data so it's visible on the entity
        car = self._get_car()
        # Prefer raw last_location from ev_info, then last_location, then location
        ev = car.get("ev_info") or {}
        raw_ev_loc = ev.get("last_location") if isinstance(ev, dict) else None
        loc = car.get("last_location") if car.get("last_location") is not None else car.get("location")
        if raw_ev_loc is not None:
            raw = raw_ev_loc
            src = "ev_info.last_location"
        elif loc is not None:
            raw = loc
            src = "last_location" if car.get("last_location") is not None else "location"
        else:
            raw = None
            src = None
        attrs = {"vin": self._vin, **car}
        attrs["last_location_raw"] = raw
        if src:
            attrs["last_location_source"] = src
        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        # Use nickname for device name when available; fall back to model_name
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("nickname") or car.get("model_name")}
