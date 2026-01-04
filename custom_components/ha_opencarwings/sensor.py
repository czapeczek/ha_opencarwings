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
