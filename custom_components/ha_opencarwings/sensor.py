"""Sensor platform for OpenCARWINGS listing cars."""
from __future__ import annotations

from typing import Any
import logging

from homeassistant.helpers.entity import Entity
from homeassistant.const import ATTR_ATTRIBUTION

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    cars = data.get("cars", [])

    entities = [CarListSensor(entry.entry_id, cars)]

    # Create one entity per car so they appear as devices in the Integrations UI
    for car in cars:
        entities.append(CarSensor(entry.entry_id, car))
        entities.append(CarBatterySensor(entry.entry_id, car))
        entities.append(CarRangeACOnSensor(entry.entry_id, car))
        entities.append(CarRangeACOffSensor(entry.entry_id, car))
        entities.append(CarSoCSensor(entry.entry_id, car))
        entities.append(CarChargeCableSensor(entry.entry_id, car))
        entities.append(CarStatusSensor(entry.entry_id, car))

    async_add_entities(entities)


class CarListSensor(Entity):
    """Sensor that represents the list of cars for the account."""

    def __init__(self, entry_id: str, cars: list[dict]) -> None:
        self._entry_id = entry_id
        self._cars = cars
        self._state = len(cars)

    @property
    def name(self) -> str:
        return "OpenCARWINGS Cars"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_{self._entry_id}_cars"

    @property
    def state(self) -> int:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Provide car list as attributes: list of VINs and per-car details
        return {
            ATTR_ATTRIBUTION: "Data provided by OpenCARWINGS",
            "cars": self._cars,
            "car_vins": [c.get("vin") for c in self._cars if c.get("vin")],
        }

    async def async_update(self) -> None:  # pragma: no cover - optional polling
        # Refresh not implemented here; integration-level update should refresh hass.data
        pass


class CarSensor(Entity):
    """Entity representing a single car (shows up as a device)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")

    @property
    def name(self) -> str:
        return self._car.get("model_name") or f"Car {self._vin}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_{self._vin}"

    @property
    def state(self) -> str:
        # Primary state can be the model name or VIN
        return self._car.get("model_name") or self._vin

    @property
    def device_info(self) -> dict:
        # Provide device registry information so the car shows as a device
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self.name,
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"vin": self._vin, **self._car}


class CarBatterySensor(Entity):
    """Sensor exposing battery level for the car (if available)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")

    @property
    def name(self) -> str:
        return f"{self._car.get('model_name') or 'Car'} Battery"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_battery_{self._vin}"

    @property
    def state(self) -> int | None:
        # Prefer battery_level or state_of_charge field names if present
        return self._car.get("battery_level") or self._car.get("state_of_charge")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"vin": self._vin, **self._car}


class CarRangeACOnSensor(Entity):
    """Sensor for driving range with A/C on (if available)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")

    @property
    def name(self) -> str:
        return f"{self._car.get('model_name') or 'Car'} Range (A/C on)"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_range_acon_{self._vin}"

    @property
    def state(self) -> int | None:
        ev = self._car.get("ev_info", {}) or {}
        return ev.get("range_acon") or self._car.get("range_acon")


class CarRangeACOffSensor(Entity):
    """Sensor for driving range with A/C off (if available)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")

    @property
    def name(self) -> str:
        return f"{self._car.get('model_name') or 'Car'} Range (A/C off)"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_range_acoff_{self._vin}"

    @property
    def state(self) -> int | None:
        ev = self._car.get("ev_info", {}) or {}
        return ev.get("range_acoff") or self._car.get("range_acoff")


class CarSoCSensor(Entity):
    """Sensor for state of charge (percentage)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")

    @property
    def name(self) -> str:
        return f"{self._car.get('model_name') or 'Car'} State of Charge"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_soc_{self._vin}"

    @property
    def state(self) -> int | None:
        ev = self._car.get("ev_info", {}) or {}
        return ev.get("soc") or ev.get("soc_display") or self._car.get("state_of_charge") or self._car.get("battery_level")


class CarChargeCableSensor(Entity):
    """Sensor indicating if charge cable is plugged in."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")

    @property
    def name(self) -> str:
        return f"{self._car.get('model_name') or 'Car'} Charge Cable"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_plugged_in_{self._vin}"

    @property
    def state(self) -> str | None:
        ev = self._car.get("ev_info", {}) or {}
        plugged = ev.get("plugged_in") if isinstance(ev, dict) else None
        if plugged is None:
            plugged = self._car.get("plugged_in")
        return "plugged" if plugged else "unplugged"


class CarStatusSensor(Entity):
    """High-level status string for the car (charging, running, ac_on, idle)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")

    @property
    def name(self) -> str:
        return f"{self._car.get('model_name') or 'Car'} Status"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_status_{self._vin}"

    @property
    def state(self) -> str:
        ev = self._car.get("ev_info", {}) or {}
        if ev.get("charging"):
            return "charging"
        if ev.get("car_running"):
            return "running"
        if ev.get("ac_status"):
            return "ac_on"
        return "idle"
    def device_info(self) -> dict:
        return {"identifiers": {(DOMAIN, self._vin)}, "name": self._car.get("model_name")}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"vin": self._vin, "battery_raw": self._car.get("battery")}

