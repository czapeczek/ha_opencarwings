"""Sensor platform for OpenCARWINGS listing cars."""
from __future__ import annotations

from typing import Any
import logging

from homeassistant.helpers.entity import Entity
try:
    # EntityCategory is available in recent Home Assistant versions
    from homeassistant.helpers.entity import EntityCategory
except Exception:  # pragma: no cover - tests running without hass stubs
    class EntityCategory:  # type: ignore
        DIAGNOSTIC = "diagnostic"
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
        entities.append(CarRangeACOnSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarRangeACOffSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarSoCSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarSoCDisplaySensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarChargeBarsSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarChargeCableSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarChargingSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarChargeFinishSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarQuickChargingSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarACStatusSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarEcoModeSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarRunningSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarOdometerSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarFullChgTimeSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarLimitChgTimeSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarObc6kwSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        entities.append(CarStatusSensor(entry.entry_id, car, coordinator=coordinator, vin=vin))
        # Per-car Last Updated sensor that reads timestamps from the car's data
        entities.append(CarLastUpdatedSensor(entry.entry_id, car=car, coordinator=coordinator, vin=vin))
        # Per-car Last Requested sensor that shows the last coordinator request time
        entities.append(CarLastRequestedSensor(entry.entry_id, car=car, coordinator=coordinator, vin=vin))
        # Per-car VIN diagnostic sensor
        entities.append(CarVINSensor(entry.entry_id, car=car, coordinator=coordinator, vin=vin))

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

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    async def async_update(self) -> None:  # pragma: no cover - optional polling
        # Data is managed by DataUpdateCoordinator
        pass


class CarVINSensor(Entity):
    """Per-car diagnostic sensor reporting the Vehicle Identification Number (VIN)."""

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

    @property
    def name(self) -> str:
        car = self._get_car()
        return f"{car.get('model_name') or 'Car'} VIN"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_vin_{self._vin}"

    @property
    def entity_category(self):
        try:
            from homeassistant.helpers.entity import EntityCategory as _EC
            return _EC.DIAGNOSTIC
        except Exception:
            return "diagnostic"

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}

    @property
    def state(self) -> str:
        return self._vin or "unknown"

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    async def async_update(self) -> None:  # pragma: no cover - optional polling
        # Data is managed by DataUpdateCoordinator
        pass


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


class CarOdometerSensor(Entity):
    """Sensor for odometer (integer)."""

    def __init__(self, entry_id: str, car: dict | None = None, coordinator=None, vin: str | None = None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._car = car or {}
        self._vin = vin or self._car.get("vin")

    def _get_car(self) -> dict:
        if self._coordinator and self._coordinator.data is not None:
            for c in self._coordinator.data:
                if c.get("vin") == self._vin:
                    return {**(self._car or {}), **(c or {})}
        return self._car or {}

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        car = self._get_car()
        return f"{car.get('model_name') or 'Car'} Odometer"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_odometer_{self._vin}"

    @property
    def state(self) -> int | None:
        car = self._get_car()
        # The API supplies odometer as a top-level field on the car object
        val = car.get("odometer")
        if val is None:
            return None
        try:
            return int(val)
        except Exception:
            return None

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}


class CarChargeBarsSensor(Entity):
    """Sensor for charge bars (integer)."""

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
        return f"{car.get('model_name') or 'Car'} Charge Bars"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_charge_bars_{self._vin}"

    @property
    def state(self) -> int | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("charge_bars") or car.get("charge_bars")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}


class CarEcoModeSensor(Entity):
    """Sensor for eco mode (boolean)."""

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
        return f"{car.get('model_name') or 'Car'} Eco Mode"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_eco_mode_{self._vin}"

    @property
    def state(self) -> bool | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("eco_mode") if "eco_mode" in ev else car.get("eco_mode")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}


class CarRunningSensor(Entity):
    """Sensor indicating if car is running (boolean)."""

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
        return f"{car.get('model_name') or 'Car'} Running"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_running_{self._vin}"

    @property
    def state(self) -> bool | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("car_running") if "car_running" in ev else car.get("car_running")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}


class CarChargingSensor(Entity):
    """Sensor indicating if car is charging (boolean)."""

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
        return f"{car.get('model_name') or 'Car'} Charging"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_charging_{self._vin}"

    @property
    def state(self) -> bool | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("charging") if "charging" in ev else car.get("charging")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}


class CarChargeFinishSensor(Entity):
    """Sensor indicating charge finish (boolean)."""

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
        return f"{car.get('model_name') or 'Car'} Charge Finish"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_charge_finish_{self._vin}"

    @property
    def state(self) -> bool | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("charge_finish") if "charge_finish" in ev else car.get("charge_finish")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}


class CarQuickChargingSensor(Entity):
    """Sensor indicating quick charging (boolean)."""

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
        return f"{car.get('model_name') or 'Car'} Quick Charging"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_quick_charging_{self._vin}"

    @property
    def state(self) -> bool | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("quick_charging") if "quick_charging" in ev else car.get("quick_charging")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}


class CarACStatusSensor(Entity):
    """Sensor indicating AC status (boolean)."""

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
        return f"{car.get('model_name') or 'Car'} AC Status"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_ac_status_{self._vin}"

    @property
    def state(self) -> bool | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("ac_status") if "ac_status" in ev else car.get("ac_status")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}


class CarSoCDisplaySensor(Entity):
    """Sensor for soc_display (number)."""

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
        return f"{car.get('model_name') or 'Car'} State of Charge Display"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_soc_display_{self._vin}"

    @property
    def state(self) -> int | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("soc_display") or car.get("soc_display")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}


class CarFullChgTimeSensor(Entity):
    """Sensor for full_chg_time (integer)."""

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
        return f"{car.get('model_name') or 'Car'} Full Charge Time"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_full_chg_time_{self._vin}"

    @property
    def state(self) -> int | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("full_chg_time") or car.get("full_chg_time")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}


class CarLimitChgTimeSensor(Entity):
    """Sensor for limit_chg_time (integer)."""

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
        return f"{car.get('model_name') or 'Car'} Limit Charge Time"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_limit_chg_time_{self._vin}"

    @property
    def state(self) -> int | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("limit_chg_time") or car.get("limit_chg_time")

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}


class CarObc6kwSensor(Entity):
    """Sensor for obc_6kw (integer)."""

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
        return f"{car.get('model_name') or 'Car'} OBC 6kW"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_obc_6kw_{self._vin}"

    @property
    def state(self) -> int | None:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return ev.get("obc_6kw") or car.get("obc_6kw")

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

class CarLastUpdatedSensor(Entity):
    """Per-car diagnostic sensor reporting the timestamp provided by the car (ev_info.last_updated or location)."""

    # Try to set EntityCategory if available, otherwise fall back to a string constant so tests don't break
    try:
        from homeassistant.helpers.entity import EntityCategory as _EC
        _DIAGNOSTIC = _EC.DIAGNOSTIC
    except Exception:
        _DIAGNOSTIC = "diagnostic"

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

    @property
    def name(self) -> str:
        car = self._get_car()
        return f"{car.get('model_name') or 'Car'} Last Updated"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_last_updated_{self._vin}"

    @property
    def entity_category(self):
        # Mark as diagnostic so HA (and recorder) can treat it as non-essential metadata
        return self._DIAGNOSTIC

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}

    def _parse_ts(self, value: str):
        from datetime import datetime, timezone
        if not value:
            return None
        try:
            # support ISO8601 like `2026-01-04T12:00:00Z` or with microseconds `2026-01-05T00:16:10.419903Z`
            if value.endswith("Z"):
                # Try with microseconds first
                try:
                    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                except ValueError:
                    # Fall back to format without microseconds
                    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(value)
        except Exception:
            return None

    @property
    def state(self) -> str:
        # Prefer the explicit EV-provided last_updated, then location.last_updated, then last_connection
        car = self._get_car()
        ev = car.get("ev_info") or {}
        loc = car.get("location") or {}
        ts = ev.get("last_updated") or loc.get("last_updated") or car.get("last_connection")
        parsed = self._parse_ts(ts) if isinstance(ts, str) else None
        if parsed:
            out = parsed.isoformat()
            if out.endswith("+00:00"):
                out = out.replace("+00:00", "Z")
            return out
        return "unknown"

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    async def async_update(self) -> None:  # pragma: no cover - optional polling
        # Data is managed by DataUpdateCoordinator
        pass


class CarLastRequestedSensor(Entity):
    """Per-car diagnostic sensor reporting the last time the integration requested data from the API."""

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

    @property
    def name(self) -> str:
        car = self._get_car()
        return f"{car.get('model_name') or 'Car'} Last Requested"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_last_requested_{self._vin}"

    @property
    def entity_category(self):
        try:
            from homeassistant.helpers.entity import EntityCategory as _EC
            return _EC.DIAGNOSTIC
        except Exception:
            return "diagnostic"

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {"identifiers": {(DOMAIN, self._vin)}, "name": car.get("model_name"), "manufacturer": car.get("make"), "model": car.get("model_name")}

    def _format_dt(self, dt):
        if not dt:
            return None
        try:
            ts = dt.isoformat()
            if ts.endswith("+00:00"):
                ts = ts.replace("+00:00", "Z")
            return ts
        except Exception:
            return None

    @property
    def state(self) -> str:
        # coordinator.last_update_time is a datetime when the last request occurred
        coord = self._coordinator
        if coord and getattr(coord, "last_update_time", None):
            formatted = self._format_dt(coord.last_update_time)
            return formatted or "unknown"
        return "unknown"

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self._handle_coordinator_update)
            self.async_on_remove(unsub)

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    async def async_update(self) -> None:  # pragma: no cover - optional polling
        # Data is managed by DataUpdateCoordinator
        pass
