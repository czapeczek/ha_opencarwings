"""Sensor platform for OpenCARWINGS listing cars."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional, cast, List
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import ATTR_ATTRIBUTION, PERCENTAGE
from homeassistant.helpers.update_coordinator import CoordinatorEntity

try:
    from homeassistant.helpers.entity import EntityCategory
except Exception:  # pragma: no cover
    class EntityCategory:  # type: ignore
        DIAGNOSTIC = "diagnostic"

try:
    from homeassistant.components.sensor import SensorDeviceClass
except Exception:  # pragma: no cover
    class SensorDeviceClass:  # type: ignore
        BATTERY = "battery"
        DURATION = "duration"
        ENERGY = "energy"
        TEMPERATURE = "temperature"

from . import DOMAIN
from .util import CarData

_LOGGER = logging.getLogger(__name__)


# -----------------------------
# Helpers
# -----------------------------

def _parse_ts(value: str | None):
    if not value:
        return None
    try:
        # support ISO8601 like `2026-01-04T12:00:00Z` or with microseconds `...10.419903Z`
        if value.endswith("Z"):
            try:
                return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            except ValueError:
                return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(value)
    except Exception as e:
        _LOGGER.exception(e)
        return None


def _format_dt(dt: datetime | None) -> str | None:
    if not dt:
        return None
    try:
        ts = dt.isoformat()
        if ts.endswith("+00:00"):
            ts = ts.replace("+00:00", "Z")
        return ts
    except Exception:
        return None


def _ev_getter(key: str, fallback: str | None = None) -> Callable[[CarData], Any]:
    """Get value from car['ev_info'][key], falling back to car[fallback] or car[key]."""
    def _get(car: CarData):
        car_inf = car.get_latest_car()
        if car_inf is not None:
            if fallback:
                return car_inf.to_dict().get(fallback)
            ev = car_inf.ev_info.to_dict() or {}
            if isinstance(ev, dict) and key in ev:
                return ev.get(key)
            return car_inf.to_dict().get(key)
    return _get

def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        try:
            return float(s)
        except Exception:
            return None

def _round_1(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return round(float(v), 1)
    except Exception:
        return None

# -----------------------------
# Base per-car entity
# -----------------------------

class OpenCarwingsCarEntity(CoordinatorEntity):
    """Base entity for a single car identified by VIN.

    - merges seed car dict (from initial cars list) with coordinator car dict
      so fields like odometer don't disappear if coordinator payload is missing them
    """

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: CarData | None = None) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._vin = vin
        self._seed_car = seed_car

    def _get_car(self) -> CarData:
        if self.coordinator and getattr(self.coordinator, "data", None):
            for c in self.coordinator.data:
                if c.vin == self._vin:
                    return c or CarData(self._vin)
        return self._seed_car or CarData(self._vin)

    def _get_car_dict(self) -> dict:
        car_info = self._get_car().get_latest_car()
        if car_info is None:
            return {}
        return car_info.to_dict()

    @property
    def device_info(self) -> dict[str, Any]:
        return self._get_car().car_model_data()



@dataclass(frozen=True)
class CarSensorSpec:
    key: str
    name: str
    value: Callable[[CarData], Any]
    transform: Optional[Callable[[Any], Any]] = None
    device_class: Optional[str] = None
    unit_of_measurement: Optional[str] = None


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None

def _to_chgtime(v: Any) -> int | None:
    if v is None or (v == 2047 or v == 4095):
        return None
    try:
        return int(v)
    except Exception:
        return None

def _plugged_to_str(v: Any) -> str:
    return "plugged" if bool(v) else "unplugged"


CAR_SENSORS: list[CarSensorSpec] = [
    CarSensorSpec(
        "range_acon",
        "Range (A/C on)",
        _ev_getter("range_acon"),
        transform=_to_float,
        unit_of_measurement="km",
    ),
    CarSensorSpec(
        "range_acoff",
        "Range (A/C off)",
        _ev_getter("range_acoff"),
        transform=_to_float,
        unit_of_measurement="km",
    ),
    CarSensorSpec("soc", "State of Charge", _ev_getter("soc"), transform=_round_1, device_class=SensorDeviceClass.BATTERY, unit_of_measurement=PERCENTAGE),
    CarSensorSpec("soh", "State of Health", _ev_getter("soh"), transform=_round_1, device_class=SensorDeviceClass.BATTERY, unit_of_measurement=PERCENTAGE),
    CarSensorSpec("soc_display", "State of Charge Display", _ev_getter("soc_display"), transform=_round_1, device_class=SensorDeviceClass.BATTERY, unit_of_measurement=PERCENTAGE),
    CarSensorSpec("charge_bars", "Charge Bars", _ev_getter("charge_bars")),
    CarSensorSpec("capacity_bars", "Capacity Bars", _ev_getter("cap_bars")),
    CarSensorSpec("gids", "GIDs", _ev_getter("gids")),
    CarSensorSpec("max_gids", "Maximum GIDs when battery is new", _ev_getter("max_gids")),
    CarSensorSpec("plugged_in", "Charge Cable", _ev_getter("plugged_in"), transform=_plugged_to_str),
    CarSensorSpec("charging", "Charging", _ev_getter("charging")),
    CarSensorSpec("charge_finish", "Charge Finish", _ev_getter("charge_finish")),
    CarSensorSpec("quick_charging", "Quick Charging", _ev_getter("quick_charging")),
    CarSensorSpec("ac_status", "AC Status", _ev_getter("ac_status")),
    CarSensorSpec("eco_mode", "Eco Mode", _ev_getter("eco_mode")),
    CarSensorSpec("car_running", "Running", _ev_getter("car_running")),
    CarSensorSpec("odometer", "Odometer", _ev_getter("", fallback="odometer"), transform=_to_int, unit_of_measurement="km"),
    CarSensorSpec("last_requested_command", "Last Requested Command", _ev_getter("", fallback="command_type_display")),
    CarSensorSpec("full_chg_time", "3 kW/240 V Charge Time", _ev_getter("full_chg_time"), transform=_to_chgtime, unit_of_measurement="s", device_class=SensorDeviceClass.DURATION),
    CarSensorSpec("limit_chg_time", "1 kW/120 V Charge Time", _ev_getter("limit_chg_time"), transform=_to_chgtime, unit_of_measurement="s", device_class=SensorDeviceClass.DURATION),
    CarSensorSpec("obc_6kw", "6.6 kW Charge Time", _ev_getter("obc_6kw"), transform=_to_chgtime, unit_of_measurement="s", device_class=SensorDeviceClass.DURATION),
    CarSensorSpec("obc_6kw_avail", "6.6 kW OBC Exists", _ev_getter("obc_6kw_avail")),
    CarSensorSpec("batt_heater_avail", "Battery Heater Exists", _ev_getter("batt_heater_avail")),
    CarSensorSpec("batt_heater_status", "Battery Heater Active", _ev_getter("batt_heater_status")),
    CarSensorSpec("wh_content", "Battery Wh content", _ev_getter("wh_content"), device_class=SensorDeviceClass.ENERGY, unit_of_measurement="Wh"),
    CarSensorSpec("cabin_temp", "Cabin Temperature", _ev_getter("cabin_temp"), device_class=SensorDeviceClass.TEMPERATURE, unit_of_measurement="°C"),
]


class CarValueSensor(OpenCarwingsCarEntity, SensorEntity):
    """Generic per-car sensor based on CarSensorSpec."""

    def __init__(self, coordinator, entry_id: str, vin: str, spec: CarSensorSpec, seed_car: CarData | None = None) -> None:
        OpenCarwingsCarEntity.__init__(self, coordinator, entry_id, vin, seed_car)
        self._spec = spec
        self._attr_unique_id = f"ha_opencarwings_{spec.key}_{vin}"
        if spec.device_class:
            self._attr_device_class = spec.device_class
        if spec.unit_of_measurement:
            self._attr_native_unit_of_measurement = spec.unit_of_measurement

    @property
    def name(self) -> str:
        car = self._get_car_dict()
        prefix = car.get("nickname") or "Car"
        return f"{prefix} {self._spec.name}"

    @property
    def native_value(self):
        car = self._get_car()
        val = self._spec.value(car)

        if self._spec.transform:
            return self._spec.transform(val)
        return val


# -----------------------------
# Status sensor 
# -----------------------------

class CarStatusSensor(OpenCarwingsCarEntity, SensorEntity):
    """High-level status string for the car (charging, running, ac_on, idle)."""

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: CarData | None = None) -> None:
        super().__init__(coordinator, entry_id, vin, seed_car)
        self._attr_unique_id = f"ha_opencarwings_status_{vin}"

    @property
    def name(self) -> str:
        car = self._get_car_dict()
        prefix = car.get("nickname") or "Car"
        return f"{prefix} Status"

    @property
    def native_value(self) -> str:
        car = self._get_car_dict()
        ev = car.get("ev_info", {}) or {}
        if car.get("command_requested"):
            return "running_command"
        if ev.get("quick_charging"):
            return "quick_charging"
        if ev.get("charging"):
            return "charging"
        if ev.get("car_running"):
            return "running"
        if ev.get("ac_status"):
            return "ac_on"
        if ev.get("batt_heater_status"):
            return "batt_heater"
        return "idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Keep this SMALL and SAFE (optional). Remove entirely if you want no attributes.
        car = self._get_car_dict()
        ev = car.get("ev_info", {}) or {}
        return {
            ATTR_ATTRIBUTION: "Data provided by OpenCARWINGS",
            "last_connection": car.get("last_connection"),
            "last_evinfo": ev.get("last_updated"),
            "signal_level": car.get("signal_level"),
            "carrier": car.get("carrier"),
            "navi_version": car.get("navi_version"),
            "map_version": car.get("map_version"),
            "tcu_version": car.get("tcu_version"),
            "tcu_type": car.get("tcu_type"),
            "soc": ev.get("soc"),
            "range_acoff": ev.get("range_acoff"),
            "color": car.get("color"),
            "raw_car": {
                **car
            }
        }


class CarVehicleHealthSensor(OpenCarwingsCarEntity, SensorEntity):
    """Vehicle Health Report"""

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: CarData | None = None) -> None:
        super().__init__(coordinator, entry_id, vin, seed_car)
        self._attr_unique_id = f"ha_opencarwings_veh_health_report_{vin}"

    @property
    def name(self) -> str:
        car = self._get_car_dict()
        prefix = car.get("nickname") or "Car"
        return f"{prefix} Vehicle Health Report"

    @property
    def native_value(self) -> str:
        car = self._get_car_dict()
        veh_health: dict|None = car.get("veh_health")
        if veh_health is not None:
            return "idle"
        return "unavailable"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Keep this SMALL and SAFE (optional). Remove entirely if you want no attributes.
        car = self._get_car_dict()
        veh_health: dict|None = car.get("veh_health")
        if veh_health is not None:
            return {
                ATTR_ATTRIBUTION: "Data provided by OpenCARWINGS",
                **veh_health
            }
        return {
            ATTR_ATTRIBUTION: "Data provided by OpenCARWINGS",
        }

# -----------------------------
# Diagnostic sensors
# -----------------------------

class CarVINSensor(OpenCarwingsCarEntity, SensorEntity):
    """Per-car diagnostic sensor reporting the VIN."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: CarData | None = None) -> None:
        super().__init__(coordinator, entry_id, vin, seed_car)
        self._attr_unique_id = f"ha_opencarwings_vin_{vin}"

    @property
    def name(self) -> str:
        car = self._get_car_dict()
        prefix = car.get("nickname") or "Car"
        return f"{prefix} VIN"

    @property
    def native_value(self) -> str:
        return self._vin or "unknown"


class CarLastUpdatedSensor(OpenCarwingsCarEntity, SensorEntity):
    """Diagnostic: timestamp provided by the car (ev_info.last_updated or location or last_connection)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: CarData | None = None) -> None:
        super().__init__(coordinator, entry_id, vin, seed_car)
        self._attr_unique_id = f"ha_opencarwings_last_updated_{vin}"

    @property
    def name(self) -> str:
        car = self._get_car_dict()
        prefix = car.get("nickname")or "Car"
        return f"{prefix} Last Updated"

    @property
    def native_value(self) -> str:
        car = self._get_car_dict()
        ev = car.get("ev_info") or {}
        loc = car.get("location") or {}
        ts = ev.get("last_updated") or loc.get("last_updated") or car.get("last_connection")
        parsed = _parse_ts(ts) if isinstance(ts, str) else None
        if parsed:
            return _format_dt(parsed) or parsed.isoformat()
        return "unknown"


class CarLastRequestedSensor(OpenCarwingsCarEntity, SensorEntity):
    """Diagnostic: last time the integration requested data from the API."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: CarData | None = None) -> None:
        super().__init__(coordinator, entry_id, vin, seed_car)
        self._attr_unique_id = f"ha_opencarwings_last_requested_{vin}"

    @property
    def name(self) -> str:
        car = self._get_car_dict()
        prefix = car.get("nickname") or car.get("model_name") or "Car"
        return f"{prefix} Last Requested"

    @property
    def native_value(self) -> str:
        coord = self.coordinator
        dt = getattr(coord, "last_update_time", None) if coord else None
        return _format_dt(dt) or "unknown"


# -----------------------------
# Car list sensor
# -----------------------------

class CarListSensor(SensorEntity):
    """Sensor that represents the list of cars for the account."""

    def __init__(self, entry_id: str, cars: list[CarData] | None = None, coordinator=None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._cars = cars or []
        self._attr_unique_id = f"ha_opencarwings_{entry_id}_cars"

    @property
    def name(self) -> str:
        return "OpenCARWINGS Cars"

    @property
    def native_value(self) -> int:
        cars = self._coordinator.data if self._coordinator and self._coordinator.data is not None else self._cars
        return len(cars)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cars = self._coordinator.data if self._coordinator and self._coordinator.data is not None else self._cars
        return {
            ATTR_ATTRIBUTION: "Data provided by OpenCARWINGS",
            "car_vins": [c.vin for c in cars if (c and c.vin)],
        }

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self.async_write_ha_state)
            self.async_on_remove(unsub)


# -----------------------------
# Setup
# -----------------------------

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")
    cars: List[CarData] = coordinator.data if coordinator and coordinator.data is not None else data.get("cars", [])

    entities: list[SensorEntity] = []
    entities.append(CarListSensor(entry.entry_id, cars=cars, coordinator=coordinator))

    for car in cars:
        vin = car.vin
        if not vin:
            continue

        # Generic value sensors
        for spec in CAR_SENSORS:
            entities.append(CarValueSensor(coordinator, entry.entry_id, vin, spec, seed_car=car))

        # Status
        entities.append(CarStatusSensor(coordinator, entry.entry_id, vin, seed_car=car))

        # Diagnostics
        entities.append(CarLastUpdatedSensor(coordinator, entry.entry_id, vin, seed_car=car))
        entities.append(CarLastRequestedSensor(coordinator, entry.entry_id, vin, seed_car=car))
        entities.append(CarVINSensor(coordinator, entry.entry_id, vin, seed_car=car))

    async_add_entities(entities)
