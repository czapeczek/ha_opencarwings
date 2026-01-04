from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")

    cached_cars = data.get("cars", []) or []
    vins: list[str] = []

    for car in cached_cars:
        vin = car.get("vin")
        if vin and vin not in vins:
            vins.append(vin)

    if coordinator and coordinator.data:
        for car in coordinator.data:
            vin = car.get("vin")
            if vin and vin not in vins:
                vins.append(vin)

    entities = [CarTracker(entry.entry_id, vin=vin, coordinator=coordinator, hass=hass) for vin in vins]
    async_add_entities(entities)


class CarTracker(TrackerEntity):
    """GPS tracker per car VIN, driven by DataUpdateCoordinator."""

    def __init__(self, entry_id: str, vin: str, coordinator=None, hass: HomeAssistant | None = None) -> None:
        self._entry_id = entry_id
        self._vin = vin
        self._coordinator = coordinator
        self.hass = hass

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_tracker_{self._entry_id}_{self._vin}"

    @property
    def name(self) -> str:
        car = self._get_car()
        visible = car.get("nickname") or car.get("model_name") or "Car"
        return f"{visible} Tracker"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        if not self._coordinator:
            return True
        return bool(getattr(self._coordinator, "last_update_success", True))

    # --- Data lookup ---
    def _get_car(self) -> dict[str, Any]:
        if self._coordinator and self._coordinator.data:
            for c in self._coordinator.data:
                if c.get("vin") == self._vin:
                    return c

        if self.hass:
            data = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
            for c in (data.get("cars") or []):
                if c.get("vin") == self._vin:
                    return c

        return {"vin": self._vin}

    def _parse_lat_lon(self, loc: Any) -> Tuple[Optional[float], Optional[float]]:
        # dict: lat/lon | latitude/longitude | lng
        if isinstance(loc, dict):
            lat = loc.get("lat", loc.get("latitude"))
            lon = loc.get("lon", loc.get("longitude", loc.get("lng")))
            if lat is None or lon is None:
                for k in ("position", "coords", "coordinate", "gps"):
                    if isinstance(loc.get(k), dict):
                        return self._parse_lat_lon(loc.get(k))
                return None, None
            try:
                return float(str(lat).replace(",", ".")), float(str(lon).replace(",", "."))
            except Exception:
                return None, None

        # list/tuple: [lat, lon] albo [ {lat,lon}, ... ]
        if isinstance(loc, (list, tuple)):
            if len(loc) == 2 and all(isinstance(x, (int, float, str)) for x in loc):
                try:
                    return float(str(loc[0]).replace(",", ".")), float(str(loc[1]).replace(",", "."))
                except Exception:
                    return None, None
            if len(loc) > 0:
                return self._parse_lat_lon(loc[0])

        # string: "lat,lon"
        if isinstance(loc, str) and "," in loc:
            parts = [p.strip() for p in loc.split(",")]
            if len(parts) >= 2:
                try:
                    return float(parts[0].replace(",", ".")), float(parts[1].replace(",", "."))
                except Exception:
                    return None, None

        return None, None

    def _get_lat_lon(self) -> Tuple[Optional[float], Optional[float]]:
        car = self._get_car()

        candidates = []
        candidates.append(car.get("last_location"))
        candidates.append(car.get("location"))

        ev = car.get("ev_info") or {}
        if isinstance(ev, dict):
            candidates.append(ev.get("last_location"))
            candidates.append(ev.get("location"))
            candidates.append(ev.get("position"))
            candidates.append(ev.get("gps"))

        for loc in candidates:
            lat, lon = self._parse_lat_lon(loc)
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
        car = self._get_car()
        loc = car.get("last_location") or car.get("location")
        if isinstance(loc, dict):
            return loc.get("name") or loc.get("address")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        car = self._get_car()
        lat, lon = self._get_lat_lon()
        attrs: dict[str, Any] = {
            "vin": self._vin,
            "latitude": lat,
            "longitude": lon,
        }
        attrs["last_location_raw"] = car.get("last_location")
        attrs["location_raw"] = car.get("location")
        return attrs

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        name = car.get("nickname") or car.get("model_name") or f"Car {self._vin}"
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": name,
            "manufacturer": car.get("make"),
            "model": car.get("model_name"),
        }
