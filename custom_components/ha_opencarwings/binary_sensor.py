"""Binary sensor platform for OpenCARWINGS on/off car states."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional
import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from . import DOMAIN
from .sensor import EntityCategory, OpenCarwingsCarEntity, _ev_getter
from .util import CarData

_LOGGER = logging.getLogger(__name__)


def _to_bool(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return bool(v)


@dataclass(frozen=True)
class CarBinarySensorSpec:
    key: str
    name: str
    value: Callable[[CarData], Any]
    device_class: Optional[str] = None
    entity_category: Optional[str] = None


CAR_BINARY_SENSORS: list[CarBinarySensorSpec] = [
    # PLUG -> "Plugged in" / "Unplugged"
    CarBinarySensorSpec("plugged_in", "Charging cable connected", _ev_getter("plugged_in"), device_class=BinarySensorDeviceClass.PLUG),
    # BATTERY_CHARGING -> "Charging" / "Not charging"
    CarBinarySensorSpec("charging", "Charging", _ev_getter("charging"), device_class=BinarySensorDeviceClass.BATTERY_CHARGING),
    CarBinarySensorSpec("quick_charging", "Quick Charging", _ev_getter("quick_charging"), device_class=BinarySensorDeviceClass.BATTERY_CHARGING),
    # No device class -> "On" / "Off"
    CarBinarySensorSpec("charge_finish", "Charge Finish", _ev_getter("charge_finish")),
    # POWER -> "On" / "Off"
    CarBinarySensorSpec("ac_status", "AC Status", _ev_getter("ac_status"), device_class=BinarySensorDeviceClass.POWER),
    CarBinarySensorSpec("batt_heater_status", "Battery Heater Active", _ev_getter("batt_heater_status"), device_class=BinarySensorDeviceClass.POWER),
    # No device class -> "On" / "Off"
    CarBinarySensorSpec("eco_mode", "Eco Mode", _ev_getter("eco_mode")),
    # RUNNING -> "Running" / "Not running"
    CarBinarySensorSpec("car_running", "Running", _ev_getter("car_running"), device_class=BinarySensorDeviceClass.RUNNING),
    # Car equipment (diagnostic)
    CarBinarySensorSpec("obc_6kw_avail", "6.6 kW OBC Exists", _ev_getter("obc_6kw_avail"), entity_category=EntityCategory.DIAGNOSTIC),
    CarBinarySensorSpec("batt_heater_avail", "Battery Heater Exists", _ev_getter("batt_heater_avail"), entity_category=EntityCategory.DIAGNOSTIC),
]


class CarBinarySensor(OpenCarwingsCarEntity, BinarySensorEntity):
    """Generic per-car binary sensor based on CarBinarySensorSpec."""

    def __init__(self, coordinator, entry_id: str, vin: str, spec: CarBinarySensorSpec, seed_car: CarData | None = None) -> None:
        OpenCarwingsCarEntity.__init__(self, coordinator, entry_id, vin, seed_car)
        self._spec = spec
        self._attr_unique_id = f"ha_opencarwings_{spec.key}_{vin}"
        if spec.device_class:
            self._attr_device_class = spec.device_class
        if spec.entity_category:
            self._attr_entity_category = spec.entity_category

    @property
    def name(self) -> str:
        car = self._get_car_dict()
        prefix = car.get("nickname") or "Car"
        return f"{prefix} {self._spec.name}"

    @property
    def is_on(self) -> bool | None:
        return _to_bool(self._spec.value(self._get_car()))


def _remove_legacy_sensors(hass, vins: list[str]) -> None:
    """Remove sensor-platform entities that were replaced by binary sensors."""
    try:
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(hass)
    except Exception:
        # Entity registry not available in hass stub
        _LOGGER.debug("Could not access entity registry to remove legacy sensors")
        return

    for vin in vins:
        for spec in CAR_BINARY_SENSORS:
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"ha_opencarwings_{spec.key}_{vin}")
            if entity_id:
                _LOGGER.info("Removing legacy sensor %s (now a binary sensor)", entity_id)
                registry.async_remove(entity_id)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")
    cars: List[CarData] = coordinator.data if coordinator and coordinator.data is not None else data.get("cars", [])

    vins = [car.vin for car in cars if car.vin]
    _remove_legacy_sensors(hass, vins)

    entities: list[BinarySensorEntity] = []
    for car in cars:
        vin = car.vin
        if not vin:
            continue
        for spec in CAR_BINARY_SENSORS:
            entities.append(CarBinarySensor(coordinator, entry.entry_id, vin, spec, seed_car=car))

    async_add_entities(entities)
