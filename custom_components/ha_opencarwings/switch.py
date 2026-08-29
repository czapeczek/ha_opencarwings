"""Switch platform to control car climate (A/C) as a simple switch."""
from __future__ import annotations

from typing import Any, List
import logging

import opencarwings_client
from opencarwings_client import ApiClient, ApiCommandCreateRequest, CommandResponse

from homeassistant.components.switch import SwitchEntity

from . import DOMAIN
from .util import CarData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    cars: List[CarData] = data.get("cars", [])

    entities = []
    for car in cars:
        if car.vin:
            ent = CarACSwitch(entry.entry_id, car)
            # Tests call entity methods directly; set hass here for testability
            ent.hass = hass
            entities.append(ent)

    async_add_entities(entities)


class CarACSwitch(SwitchEntity):
    """Represents the car A/C as a switch."""

    def __init__(self, entry_id: str, car: CarData) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.vin
        # state: True = on, False = off (no real-time state unless refreshed)
        self._is_on = False

    @property
    def name(self) -> str:
        return f"{self._car.car_model_data().get("name", None) or 'Car'} A/C"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_ac_{self._vin}"

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def is_available(self) -> bool:
        car_data = self._car.get_latest_car()
        return car_data is not None and car_data.command_requested == False

    @property
    def device_info(self) -> dict[str, Any]:
        return self._car.car_model_data()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn A/C on by sending command_type 3 to `/api/command/{vin}/`."""
        client = hass_client(self.hass, self._entry_id)
        try:
            cars_api = opencarwings_client.CarsApi(client)
            command_result: CommandResponse = await cars_api.api_command_create(self._vin, ApiCommandCreateRequest(
                command_type=3
            ))
            try:
                coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
                if coordinator:
                    if self._vin in coordinator.data:
                        car_curr_data: CarData = coordinator.data[self._vin]
                        car_curr_data.car_detail = command_result.car
                        coordinator.data[self._vin] = car_curr_data
                        await coordinator.async_update()
            except Exception:  # pragma: no cover - coordinator failure
                _LOGGER.exception("Failed to update coordinator data after requesting charge start for %s", self._vin)

        except Exception:  # pragma: no cover - network
            _LOGGER.exception("Failed to turn A/C on for %s", self._vin)
            raise

    async def async_turn_off(self, **kwargs) -> None:
        """Turn A/C off by sending command_type 4."""
        client = hass_client(self.hass, self._entry_id)
        try:
            cars_api = opencarwings_client.CarsApi(client)
            command_result: CommandResponse = await cars_api.api_command_create(self._vin, ApiCommandCreateRequest(
                command_type=4
            ))
            try:
                coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
                if coordinator:
                    if self._vin in coordinator.data:
                        car_curr_data: CarData = coordinator.data[self._vin]
                        car_curr_data.car_detail = command_result.car
                        coordinator.data[self._vin] = car_curr_data
                        await coordinator.async_update()
            except Exception:  # pragma: no cover - coordinator failure
                _LOGGER.exception("Failed to update coordinator data after requesting charge start for %s", self._vin)

        except Exception:  # pragma: no cover - network
            _LOGGER.exception("Failed to turn A/C off for %s", self._vin)
            raise


def hass_client(hass, entry_id: str) -> ApiClient:
    """Helper to get the API client stored in hass.data."""
    return hass.data[DOMAIN][entry_id]["client"]
