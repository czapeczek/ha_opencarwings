from opencarwings_client import CarSerializerList, Car

from custom_components.ha_opencarwings import DOMAIN


class CarData:
    vin: str
    list_car: CarSerializerList|None = None
    car_detail: Car|None = None

    def __init__(self, vin: str, list_car: CarSerializerList|None = None, car_detail: Car|None = None):
        self.vin = vin
        self.list_car = list_car
        self.car_detail = car_detail

    def get_latest_car(self) -> Car|CarSerializerList|None:
        if self.car_detail:
            return self.car_detail
        return self.list_car

    def car_model_data(self) -> dict:
        car_instance = self.get_latest_car()

        if car_instance is not None:
            base_obj = {
                "identifiers": {(DOMAIN, self.vin)},
                "name": car_instance.nickname or self.vin,
                "manufacturer": "NISSAN",
            }

            car_generation = "LEAF ZE0"
            if not car_instance.vin.startswith("VSK"):
                if isinstance(car_instance, Car):
                    if car_instance.tcu_ver == "06.42":
                        car_generation = "LEAF AZE0"
                    if car_instance.tcu_ver == "TCU032":
                        car_generation = "LEAF AZE0 (2016-17)"
                    if car_instance.tcu_ver == "TCU033":
                        car_generation = "LEAF ZE1"
            else:
                car_generation = "e-NV200"
                if isinstance(car_instance, Car) and car_instance.tcu_ver == "TCU033":
                    car_generation = "e-NV200 40 kWh"

            base_obj["model"] = car_generation

            if isinstance(car_instance, Car):
                base_obj["serial_number"] = car_instance.tcu_model
            if isinstance(car_instance, Car):
                base_obj["sw_version"] = car_instance.tcu_ver

            return base_obj
        return {
            "identifiers": {(DOMAIN, self.vin)},
            "name": self.vin
        }