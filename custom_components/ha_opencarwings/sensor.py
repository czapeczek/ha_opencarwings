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
    coordinator = data.get("coordinator")
    cars = coordinator.data if coordinator and coordinator.data is not None else data.get("cars", [])

    # Car list sensor uses coordinator when available
    entities = [CarListSensor(entry.entry_id, cars=cars, coordinator=coordinator)]

    # Create one entity per car so they appear as devices in the Integrations UI
    for car in cars:
        vin = car.get("vin")
        entities.append(CarSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarBatterySensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarRangeACOnSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarRangeACOffSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarSoCSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarChargeCableSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarStatusSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))

    async_add_entities(entities)


class CarListSensor(Entity):
    """Sensor that represents the list of cars for the account."""

    def __init__(self, entry_id: str, cars: list[dict] | None = None, coordinator=None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._cars = cars or []

    @property
    def name(self) -> str:
        return "OpenCARWINGS Cars"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_{self._entry_id}_cars"

    @property
    def state(self) -> int:
        cars = self._coordinator.data if self._coordinator and self._coordinator.data is not None else self._cars
        return len(cars)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cars = self._coordinator.data if self._coordinator and self._coordinator.data is not None else self._cars
        # Provide car list as attributes: list of VINs and per-car details
        return {
            ATTR_ATTRIBUTION: "Data provided by OpenCARWINGS",
            "cars": cars,
            "car_vins": [c.get("vin") for c in cars if c.get("vin")],
        }

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    async def async_update(self) -> None:  # pragma: no cover - optional polling
        # Data is managed by DataUpdateCoordinator
        pass


class CarSensor(Entity):
    """Entity representing a single car (shows up as a device)."""

    def __init__(self, entry_id: str, car: dict | None = None, coordinator=None, vin: str | None = None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._car = car or {}
        self._vin = vin or self._car.get("vin")

    def _get_car(self) -> dict:
        if self._coordinator and self._coordinator.data is not None:
            for c in self._coordinator.data:
                if c.get("vin") == self._vin:
                    return c
            return self._car
        return self._car

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        car = self._get_car()
        return car.get("model_name") or f"Car {self._vin}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_{self._vin}"

    @property
    def state(self) -> str:
        car = self._get_car()
        return car.get("model_name") or self._vin

    @property
    def device_info(self) -> dict:
        car = self._get_car()
        # Provide device registry information so the car shows as a device
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self.name,
            "manufacturer": car.get("make"),
            "model": car.get("model_name"),
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        car = self._get_car()
        return {"vin": self._vin, **car}


class CarBatterySensor(Entity):
    """Sensor exposing battery level for the car (if available)."""

    def __init__(self, entry_id: str, car: dict | None = None, coordinator=None, vin: str | None = None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._car = car or {}
        self._vin = vin or self._car.get("vin")

    def _get_car(self) -> dict:
        if self._coordinator and self._coordinator.data is not None:
            for c in self._coordinator.data:
                if c.get("vin") == self._vin:
                    return c
            return self._car
        return self._car

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        car = self._get_car()
        return f"{car.get('model_name') or 'Car'} Battery"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_battery_{self._vin}"

    @property
    def state(self) -> int | None:
        car = self._get_car()
        # Prefer battery_level or state_of_charge field names if present
        return car.get("battery_level") or car.get("state_of_charge")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        car = self._get_car()
        return {"vin": self._vin, **car}


class CarRangeACOnSensor(Entity):
    """Sensor for driving range with A/C on (if available)."""

    def __init__(self, entry_id: str, car: dict | None = None, coordinator=None, vin: str | None = None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._car = car or {}
        self._vin = vin or self._car.get("vin")

    def _get_car(self) -> dict:
        if self._coordinator and self._coordinator.data is not None:
            for c in self._coordinator.data:
                if c.get("vin") == self._vin:
                    return c
            return self._car
        return self._car

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        car = self._get_car()
        return f"{car.get('model_name') or 'Car'} Range (A/C on)"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_range_acon_{self._vin}"

    @property
    def state(self) -> int | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("range_acon") or car.get("range_acon")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}



class CarRangeACOffSensor(Entity):
    """Sensor for driving range with A/C off (if available)."""

    def __init__(self, entry_id: str, car: dict | None = None, coordinator=None, vin: str | None = None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._car = car or {}
        self._vin = vin or self._car.get("vin")

    def _get_car(self) -> dict:
        if self._coordinator and self._coordinator.data is not None:
            for c in self._coordinator.data:
                if c.get("vin") == self._vin:
                    return c
            return self._car
        return self._car

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        car = self._get_car()
        return f"{car.get('model_name') or 'Car'} Range (A/C off)"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_range_acoff_{self._vin}"

    @property
    def state(self) -> int | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("range_acoff") or car.get("range_acoff")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}



class CarSoCSensor(Entity):
    """Sensor for state of charge (percentage)."""

    def __init__(self, entry_id: str, car: dict | None = None, coordinator=None, vin: str | None = None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._car = car or {}
        self._vin = vin or self._car.get("vin")

    def _get_car(self) -> dict:
        if self._coordinator and self._coordinator.data is not None:
            for c in self._coordinator.data:
                if c.get("vin") == self._vin:
                    return c
            return self._car
        return self._car

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        car = self._get_car()
        return f"{car.get('model_name') or 'Car'} State of Charge"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_soc_{self._vin}"

    @property
    def state(self) -> int | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("soc") or ev.get("soc_display") or car.get("state_of_charge") or car.get("battery_level")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}



class CarChargeCableSensor(Entity):
    """Sensor indicating if charge cable is plugged in."""

    def __init__(self, entry_id: str, car: dict | None = None, coordinator=None, vin: str | None = None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._car = car or {}
        self._vin = vin or self._car.get("vin")

    def _get_car(self) -> dict:
        if self._coordinator and self._coordinator.data is not None:
            for c in self._coordinator.data:
                if c.get("vin") == self._vin:
                    return c
            return self._car
        return self._car

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        car = self._get_car()
        return f"{car.get('model_name') or 'Car'} Charge Cable"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_plugged_in_{self._vin}"

    @property
    def state(self) -> str | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        plugged = ev.get("plugged_in") if isinstance(ev, dict) else None
        if plugged is None:
            plugged = car.get("plugged_in")
        return "plugged" if plugged else "unplugged"

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}



class CarStatusSensor(Entity):
    """High-level status string for the car (charging, running, ac_on, idle)."""

    def __init__(self, entry_id: str, car: dict | None = None, coordinator=None, vin: str | None = None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._car = car or {}
        self._vin = vin or self._car.get("vin")

    def _get_car(self) -> dict:
        if self._coordinator and self._coordinator.data is not None:
            for c in self._coordinator.data:
                if c.get("vin") == self._vin:
                    return c
            return self._car
        return self._car

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        car = self._get_car()
        return f"{car.get('model_name') or 'Car'} Status"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_status_{self._vin}"

    @property
    def state(self) -> str:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        if ev.get("charging"):
            return "charging"
        if ev.get("car_running"):
            return "running"
        if ev.get("ac_status"):
            return "ac_on"
        return "idle"

    @property
    def device_info(self) -> dict:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name")}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        car = self._get_car()
        return {"vin": self._vin, "battery_raw": car.get("battery")}

