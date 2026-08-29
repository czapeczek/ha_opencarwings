"""Button platform providing a manual refresh button for OpenCARWINGS."""
from __future__ import annotations

import logging

import opencarwings_client
from opencarwings_client import ApiClient, ApiCommandCreateRequest, CommandResponse

from homeassistant.components.button import ButtonEntity
from typing import Any, List

from . import DOMAIN
from .util import CarData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")

    # Create a single per-entry refresh button
    entities: List[OpenCarwingsButton] = [OpenCarWingsRefreshButton(entry.entry_id, coordinator=coordinator)]

    # Create per-car API refresh buttons for each car
    cars: List[CarData] = data.get("cars", [])
    for car in cars:
        if car.vin:
            entities.append(CarRefreshButton(entry.entry_id, car, coordinator=coordinator))
            entities.append(CarChargeStartButton(entry.entry_id, car, coordinator=coordinator))
            entities.append(CarChargeStart80Button(entry.entry_id, car, coordinator=coordinator))
            entities.append(CarDoorLockButton(entry.entry_id, car, coordinator=coordinator))
            entities.append(CarDoorUnLockButton(entry.entry_id, car, coordinator=coordinator))
            entities.append(CarHornButton(entry.entry_id, car, coordinator=coordinator))
            entities.append(CarLightsButton(entry.entry_id, car, coordinator=coordinator))
            entities.append(CarHornAndLightsButton(entry.entry_id, car, coordinator=coordinator))
            entities.append(CarStopHornAndLightsButton(entry.entry_id, car, coordinator=coordinator))
            entities.append(CarRemoteStartButton(entry.entry_id, car, coordinator=coordinator))
            entities.append(CarRemoteStopButton(entry.entry_id, car, coordinator=coordinator))

    # Tests set hass on the entity for direct method calls
    for ent in entities:
        ent.hass = hass

    async_add_entities(entities)

def hass_client(hass, entry_id: str) -> ApiClient:
    """Helper to get the API client stored in hass.data."""
    return hass.data[DOMAIN][entry_id]["client"]

class OpenCarwingsButton(ButtonEntity):

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.vin
        self._coordinator = coordinator



    @property
    def device_info(self) -> dict[str, Any]:
        return self._car.car_model_data()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}

class OpenCarWingsCommandButton(OpenCarwingsButton):

    def __init__(self, command_id: int, entry_id: str, car: CarData, coordinator=None, command_payload: dict|None = None, command_pin: str|None = None) -> None:
        super().__init__(entry_id, car, coordinator)
        self._command_id = command_id
        self._command_payload = command_payload
        self._command_pin = command_pin

    @property
    def is_available(self) -> bool:
        car_instance = self._car.get_latest_car()
        if car_instance is not None and hasattr(car_instance, "supported_commands"):
            return self._command_id in car_instance.supported_commands
        return False

    async def async_press(self) -> None:
        """Press the button to send a 'Refresh data' command to the API for this car."""
        client = hass_client(self.hass, self._entry_id)
        cars_api = opencarwings_client.CarsApi(client)
        try:
            command_result: CommandResponse = await cars_api.api_command_create(self._vin, ApiCommandCreateRequest(
                command_type=self._command_id,
                command_payload=self._command_payload,
                command_pin=self._command_pin
            ))
            try:
                if self._coordinator:
                    if self._vin in self._coordinator.data:
                        new_data = self._coordinator.data
                        car_curr_data: CarData = new_data[self._vin]
                        car_curr_data.car_detail = command_result.car
                        new_data[self._vin] = car_curr_data
                        await self._coordinator.async_update(new_data)
            except Exception:  # pragma: no cover - coordinator failure
                _LOGGER.exception("Failed to update coordinator data after requesting charge start for %s", self._vin)
        except Exception:  # pragma: no cover - network
            _LOGGER.exception("Failed to request data refresh for %s", self._vin)
            raise

class OpenCarWingsRefreshButton(OpenCarwingsButton):
    """Button that triggers a coordinator refresh when pressed."""

    def __init__(self, entry_id: str, coordinator=None) -> None:
        super().__init__(entry_id, CarData(vin=""), coordinator)
        self._entry_id = entry_id
        self._coordinator = coordinator

    @property
    def name(self) -> str:
        return "OpenCARWINGS Refresh"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_refresh_{self._entry_id}"

    async def async_press(self) -> None:
        """Press the button to force an immediate coordinator refresh."""
        if not self._coordinator:
            _LOGGER.warning("Refresh button pressed but coordinator is not available for %s", self._entry_id)
            return
        try:
            await self._coordinator.async_request_refresh()
        except Exception:  # pragma: no cover - network or unexpected
            _LOGGER.exception("Failed to refresh OpenCARWINGS data for %s", self._entry_id)
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id}


class CarRefreshButton(OpenCarWingsCommandButton):
    """Button that sends a 'Refresh data' command for a specific car."""

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        super().__init__(1, entry_id, car, coordinator)

    @property
    def name(self) -> str:
        car_instance = self._car.get_latest_car()
        # Friendly label: prefer car nickname, then model name, then VIN
        label = (car_instance.nickname or self._vin) if car_instance is not None else self._vin
        return f"Request data refresh for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_refresh_{self._vin}"


class CarChargeStartButton(OpenCarWingsCommandButton):
    """Button that sends a 'Charge start' command for a specific car."""

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        super().__init__(2, entry_id, car, coordinator)

    @property
    def name(self) -> str:
        car_instance = self._car.get_latest_car()
        # Friendly label: prefer car nickname, then model name, then VIN
        label = (car_instance.nickname or self._vin) if car_instance is not None else self._vin
        return f"Charge start for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_chargestart_{self._vin}"

class CarChargeStart80Button(OpenCarWingsCommandButton):
    """Button that sends a 'Charge start 80%' command for a specific car."""

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        super().__init__(6, entry_id, car, coordinator)

    @property
    def name(self) -> str:
        car_instance = self._car.get_latest_car()
        # Friendly label: prefer car nickname, then model name, then VIN
        label = (car_instance.nickname or self._vin) if car_instance is not None else self._vin
        return f"Charge start 80% for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_chargestart80_{self._vin}"

class CarDoorLockButton(OpenCarWingsCommandButton):
    """Button that sends a 'Charge start 80%' command for a specific car."""

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        super().__init__(7, entry_id, car, coordinator)

    @property
    def name(self) -> str:
        car_instance = self._car.get_latest_car()
        # Friendly label: prefer car nickname, then model name, then VIN
        label = (car_instance.nickname or self._vin) if car_instance is not None else self._vin
        return f"Unlock Doors for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_doorlock_{self._vin}"

class CarDoorUnLockButton(OpenCarWingsCommandButton):

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        super().__init__(8, entry_id, car, coordinator)

    @property
    def name(self) -> str:
        car_instance = self._car.get_latest_car()
        # Friendly label: prefer car nickname, then model name, then VIN
        label = (car_instance.nickname or self._vin) if car_instance is not None else self._vin
        return f"Unlock Doors for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_doorunlock_{self._vin}"

class CarHornButton(OpenCarWingsCommandButton):

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        super().__init__(9, entry_id, car, coordinator)

    @property
    def name(self) -> str:
        car_instance = self._car.get_latest_car()
        # Friendly label: prefer car nickname, then model name, then VIN
        label = (car_instance.nickname or self._vin) if car_instance is not None else self._vin
        return f"Horn for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_horn_{self._vin}"

class CarLightsButton(OpenCarWingsCommandButton):

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        super().__init__(10, entry_id, car, coordinator)

    @property
    def name(self) -> str:
        car_instance = self._car.get_latest_car()
        # Friendly label: prefer car nickname, then model name, then VIN
        label = (car_instance.nickname or self._vin) if car_instance is not None else self._vin
        return f"Lights for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_lights_{self._vin}"

class CarHornAndLightsButton(OpenCarWingsCommandButton):

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        super().__init__(11, entry_id, car, coordinator)

    @property
    def name(self) -> str:
        car_instance = self._car.get_latest_car()
        # Friendly label: prefer car nickname, then model name, then VIN
        label = (car_instance.nickname or self._vin) if car_instance is not None else self._vin
        return f"Horn & Lights for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_horn_lights_{self._vin}"

class CarStopHornAndLightsButton(OpenCarWingsCommandButton):

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        super().__init__(12, entry_id, car, coordinator)

    @property
    def name(self) -> str:
        car_instance = self._car.get_latest_car()
        # Friendly label: prefer car nickname, then model name, then VIN
        label = (car_instance.nickname or self._vin) if car_instance is not None else self._vin
        return f"Stop Horn & Lights for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_stop_horn_lights_{self._vin}"

class CarRemoteStartButton(OpenCarWingsCommandButton):

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        super().__init__(13, entry_id, car, coordinator)

    @property
    def name(self) -> str:
        car_instance = self._car.get_latest_car()
        # Friendly label: prefer car nickname, then model name, then VIN
        label = (car_instance.nickname or self._vin) if car_instance is not None else self._vin
        return f"Remote Start for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_remote_start_{self._vin}"

class CarRemoteStopButton(OpenCarWingsCommandButton):

    def __init__(self, entry_id: str, car: CarData, coordinator=None) -> None:
        super().__init__(14, entry_id, car, coordinator)

    @property
    def name(self) -> str:
        car_instance = self._car.get_latest_car()
        # Friendly label: prefer car nickname, then model name, then VIN
        label = (car_instance.nickname or self._vin) if car_instance is not None else self._vin
        return f"Remote Stop for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_remote_stop_{self._vin}"