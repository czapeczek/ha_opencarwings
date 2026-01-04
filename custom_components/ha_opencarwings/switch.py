"""Switch platform to control car climate (A/C) as a simple switch."""
from __future__ import annotations

from typing import Any
import logging

from homeassistant.components.switch import SwitchEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    cars = data.get("cars", [])

    entities = []
    for car in cars:
        if car.get("vin"):
            ent = CarACSwitch(entry.entry_id, car)
            # Tests call entity methods directly; set hass here for testability
            ent.hass = hass
            entities.append(ent)

    async_add_entities(entities)


class CarACSwitch(SwitchEntity):
    """Represents the car A/C as a switch."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        # state: True = on, False = off (no real-time state unless refreshed)
        self._is_on = False

    @property
    def name(self) -> str:
        return f"{self._car.get('model_name') or 'Car'} A/C"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_ac_{self._vin}"

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_turn_on(self, **kwargs) -> None:
        """Turn A/C on by sending command_type 3 to `/api/command/{vin}/`."""
        client = hass_client(self.hass, self._entry_id)
        try:
            await client.async_request("POST", f"/api/command/{self._vin}/", json={"vin": self._vin, "command_type": 3})
            self._is_on = True
        except Exception:  # pragma: no cover - network
            _LOGGER.exception("Failed to turn A/C on for %s", self._vin)
            raise

    async def async_turn_off(self, **kwargs) -> None:
        """Turn A/C off by sending command_type 4."""
        client = hass_client(self.hass, self._entry_id)
        try:
            await client.async_request("POST", f"/api/command/{self._vin}/", json={"vin": self._vin, "command_type": 4})
            self._is_on = False
        except Exception:  # pragma: no cover - network
            _LOGGER.exception("Failed to turn A/C off for %s", self._vin)
            raise


def hass_client(hass, entry_id: str):
    """Helper to get the API client stored in hass.data."""
    return hass.data[DOMAIN][entry_id]["client"]
