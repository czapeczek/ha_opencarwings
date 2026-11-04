"""Test helpers that build CarData objects backed by the opencarwings_client models."""
from __future__ import annotations

from datetime import datetime, timezone

from opencarwings_client import Car, CarSerializerList

from custom_components.ha_opencarwings.util import CarData

_DETAIL_DEFAULTS = {
    "tcu_configuration": {},
    "location": {},
    "ev_info": {},
    "send_to_car_location_all": [],
    "route_plans": [],
    "command_type_display": "None",
    "command_result_display": "None",
    "timer_commands": [],
    "sms_config": {},
    "owner": 1,
}
_LIST_DEFAULTS = {"location": {}, "ev_info": {}}


def make_list_car(vin: str = "VIN1", **fields) -> CarSerializerList:
    data = {**_LIST_DEFAULTS, "vin": vin, **fields}
    return CarSerializerList.from_dict(data)


def make_detail_car(vin: str = "VIN1", **fields) -> Car:
    data = {**_DETAIL_DEFAULTS, "vin": vin, **fields}
    return Car.from_dict(data)


def make_car(vin: str = "VIN1", detail: bool = True, **fields) -> CarData:
    """Build a CarData. `fields` are API fields, e.g. nickname, ev_info={...}, location={...}."""
    if detail:
        return CarData(vin=vin, car_detail=make_detail_car(vin, **fields))
    return CarData(vin=vin, list_car=make_list_car(vin, **fields))


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)
