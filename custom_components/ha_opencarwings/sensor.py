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

    async_add_entities([CarListSensor(entry.entry_id, cars)])


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
