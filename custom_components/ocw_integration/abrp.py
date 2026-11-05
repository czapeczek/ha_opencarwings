"""A Better Routeplanner (ABRP) live telemetry bridge for OpenCARWINGS."""
from __future__ import annotations

import datetime as dt
import json
import logging
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)

# Standard public ABRP API key for v1 generic telemetry (/1/tlm/send)
DEFAULT_ABRP_API_KEY = "32b2162f-9599-4647-8139-66e9f9528370"
ABRP_V1_TLM_URL = "https://api.iternio.com/1/tlm/send"
ABRP_HEARTBEAT_INTERVAL_SECONDS = 30
ABRP_HEARTBEAT_SECONDS = 25  # Allow slight timer jitter for 30s heartbeat
ABRP_ACTIVE_TCU_REFRESH_SECONDS = 60  # Request fresh TCU data every 60s while driving/charging


@dataclass
class SnapshotState:
    """Stores the previous reading state to compute differential power (kW) and speed (km/h)."""

    timestamp_epoch: float
    wh_content: Optional[float]
    lat: Optional[float]
    lon: Optional[float]
    odometer_km: Optional[float]
    ev_updated_iso: Optional[str]
    speed_kmh: Optional[float] = None
    power_kw: Optional[float] = None


def parse_iso_timestamp(iso_str: Optional[str]) -> Optional[float]:
    """Convert an ISO-8601 string (e.g. '2026-10-28T19:50:00Z') to Unix epoch seconds."""
    if not iso_str:
        return None
    try:
        cleaned = str(iso_str).strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(cleaned)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.timestamp()
    except (ValueError, TypeError):
        return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance in kilometers between two GPS coordinates."""
    r_earth = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * r_earth * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def is_car_active(car_data: Dict[str, Any]) -> bool:
    """Return True only when the car is ON (running/driving) or actively charging."""
    ev_info = car_data.get("ev_info") or {}
    if not isinstance(ev_info, dict):
        return False
    car_running = bool(ev_info.get("car_running", False))
    is_charging = bool(ev_info.get("charging", False))
    car_gear = ev_info.get("car_gear", 0)
    return car_running or is_charging or (car_gear not in (0, None, "0"))


def is_car_driving(car_data: Dict[str, Any]) -> bool:
    """Return True only when the car is being driven (ON / in gear and NOT charging)."""
    ev_info = car_data.get("ev_info") or {}
    if not isinstance(ev_info, dict):
        return False
    if bool(ev_info.get("charging", False)):
        return False
    car_running = bool(ev_info.get("car_running", False))
    car_gear = ev_info.get("car_gear", 0)
    return car_running or (car_gear not in (0, None, "0"))


def estimate_carwings_charging_power_kw(ev_info: Dict[str, Any]) -> Optional[float]:
    """Estimate AC/DC charging power (negative kW for ABRP) from OpenCARWINGS TCU charge time registers.

    In CARWINGS protocol, 2047 (0x7FF) and 4095 (0xFFF) mean 'unavailable / not active'.
    """
    if not ev_info.get("charging", False):
        return None

    power_kw: Optional[float] = None
    limit_chg_time = ev_info.get("limit_chg_time")
    full_chg_time = ev_info.get("full_chg_time")
    obc_6kw = ev_info.get("obc_6kw")

    if limit_chg_time is not None and int(limit_chg_time) not in (0, 2047, 4095):
        power_kw = -1.2
    if full_chg_time is not None and int(full_chg_time) not in (0, 2047, 4095):
        power_kw = -3.6
    if obc_6kw is not None and int(obc_6kw) not in (0, 2047, 4095):
        power_kw = -6.6

    return power_kw


def build_abrp_telemetry(
    car_data: Dict[str, Any],
    prev_state: Optional[SnapshotState],
    latest_trip: Optional[Dict[str, Any]] = None,
    use_dash_soc: bool = True,
    gid_wh: float = 80.0,
    car_model: Optional[str] = None,
) -> tuple[Dict[str, Any], SnapshotState]:
    """Map the OpenCARWINGS `Car` object to the `tlm` dictionary expected by ABRP."""
    ev_info: Dict[str, Any] = car_data.get("ev_info") or {}
    loc_info: Dict[str, Any] = car_data.get("location") or {}
    veh_health: Dict[str, Any] = car_data.get("veh_health") or {}

    now_epoch = time.time()
    ev_updated_iso = ev_info.get("last_updated") or car_data.get("last_connection")
    loc_updated_iso = loc_info.get("last_updated")

    ev_epoch = parse_iso_timestamp(ev_updated_iso)
    loc_epoch = parse_iso_timestamp(loc_updated_iso)
    reading_epoch = max(
        [ts for ts in (ev_epoch, loc_epoch) if ts is not None],
        default=now_epoch,
    )

    # ABRP requires `utc` to be the current Unix timestamp on every 30s push
    # to keep the vehicle status as "Online / Live Data".
    utc_to_send = int(now_epoch)

    tlm: Dict[str, Any] = {"utc": utc_to_send}
    if car_model:
        tlm["car_model"] = car_model

    # 1. State of Charge (SoC %)
    soc_display = ev_info.get("soc_display")
    soc_bms = ev_info.get("soc")
    force_display = ev_info.get("force_soc_display", False)

    soc: Optional[float] = None
    if (use_dash_soc or force_display) and soc_display is not None and float(soc_display) > 0:
        soc = round(float(soc_display), 2)
    elif soc_bms is not None and float(soc_bms) >= 0:
        soc = round(float(soc_bms), 2)
    elif soc_display is not None:
        soc = round(float(soc_display), 2)

    if soc is not None:
        tlm["soc"] = soc

    # 2. State of Health (SoH %)
    soh_raw = ev_info.get("soh")
    soh: Optional[float] = None
    if soh_raw is not None and float(soh_raw) > 0:
        soh = round(float(soh_raw), 2)
        tlm["soh"] = soh

    # 3. Remaining Energy (SoE in kWh) and Degraded Usable Battery Capacity (capacity in kWh)
    wh_content = ev_info.get("wh_content")
    max_gids = ev_info.get("max_gids")
    gids = ev_info.get("gids")

    curr_wh: Optional[float] = None
    if wh_content is not None and float(wh_content) > 0:
        curr_wh = float(wh_content)
    elif gids is not None and int(gids) > 0:
        curr_wh = float(gids) * gid_wh

    if curr_wh is not None:
        tlm["soe"] = round(curr_wh / 1000.0, 3)

    if max_gids is not None and int(max_gids) > 0:
        soh_factor = (soh / 100.0) if (soh is not None and 0 < soh <= 100.0) else 1.0
        tlm["capacity"] = round(((float(max_gids) * soh_factor) * gid_wh) / 1000.0, 3)
    elif curr_wh is not None and soc is not None and soc > 5.0:
        tlm["capacity"] = round((curr_wh / 1000.0) / (soc / 100.0), 3)

    # 4. Charging and Driving State
    is_charging = bool(ev_info.get("charging", False))
    is_quick_charging = bool(ev_info.get("quick_charging", False))
    car_running = bool(ev_info.get("car_running", False))
    car_gear = ev_info.get("car_gear", 0)

    is_parked = (not car_running) or (car_gear == 0) or is_charging

    tlm["is_charging"] = 1 if is_charging else 0
    tlm["is_dcfc"] = 1 if (is_charging and is_quick_charging) else 0
    tlm["is_parked"] = 1 if is_parked else 0

    # 5. GPS Coordinates (lat / lon)
    curr_lat: Optional[float] = None
    curr_lon: Optional[float] = None
    raw_lat = loc_info.get("lat")
    raw_lon = loc_info.get("lon")
    if raw_lat is not None and raw_lon is not None:
        try:
            lat_f, lon_f = float(raw_lat), float(raw_lon)
            if not (math.isclose(lat_f, 0.0) and math.isclose(lon_f, 0.0)):
                curr_lat, curr_lon = lat_f, lon_f
                tlm["lat"] = round(curr_lat, 6)
                tlm["lon"] = round(curr_lon, 6)
        except (ValueError, TypeError):
            pass

    # 6. Odometer (km) and Tire Pressures (TPMS in kPa)
    odometer_km: Optional[float] = None
    raw_odo = car_data.get("odometer") or veh_health.get("mileage")
    if raw_odo is not None and float(raw_odo) > 0:
        odometer_km = float(raw_odo)
        tlm["odometer"] = round(odometer_km, 1)

    tpms_map = {
        "tire_pressure_fl": veh_health.get("tpms_fl_float") or veh_health.get("tpms_fl"),
        "tire_pressure_fr": veh_health.get("tpms_fr_float") or veh_health.get("tpms_fr"),
        "tire_pressure_rl": veh_health.get("tpms_rl_float") or veh_health.get("tpms_rl"),
        "tire_pressure_rr": veh_health.get("tpms_rr_float") or veh_health.get("tpms_rr"),
    }
    for abrp_key, raw_tpms in tpms_map.items():
        if raw_tpms is not None and float(raw_tpms) > 0:
            val = float(raw_tpms)
            if 10.0 <= val <= 80.0:
                val_kpa = val * 6.89476
            elif 0.8 <= val < 10.0:
                val_kpa = val * 100.0
            else:
                val_kpa = val
            tlm[abrp_key] = round(val_kpa, 1)

    # 7. Vehicle Estimated Range (km)
    ac_on = bool(ev_info.get("ac_status", False))
    raw_range = ev_info.get("range_acon") if ac_on else ev_info.get("range_acoff")
    if raw_range is None:
        raw_range = ev_info.get("range_acoff") or ev_info.get("range_acon")
    if raw_range is not None and float(raw_range) > 0:
        range_val = float(raw_range)
        if range_val > 1000.0:
            range_val = range_val / 1000.0
        tlm["est_battery_range"] = round(range_val, 1)

    # 8. Temperatures (Cabin, External, Battery)
    cabin_temp = ev_info.get("cabin_temp")
    if cabin_temp is not None and float(cabin_temp) != 0.0:
        tlm["cabin_temp"] = round(float(cabin_temp), 1)

    if latest_trip:
        trip_end_epoch = parse_iso_timestamp(latest_trip.get("end_ts"))
        if trip_end_epoch and abs(reading_epoch - trip_end_epoch) <= 1800:
            ext_t = latest_trip.get("outside_temp_end")
            batt_t = latest_trip.get("bda_avg_temp_end")
            if ext_t is not None:
                tlm["ext_temp"] = round(float(ext_t), 1)
            if batt_t is not None and float(batt_t) > -40:
                tlm["batt_temp"] = round(float(batt_t), 1)

    # 9. Speed (km/h) and Power (kW)
    speed_kmh: Optional[float] = None
    power_kw: Optional[float] = None

    if is_parked and not is_charging:
        speed_kmh = 0.0
        power_kw = 0.0
    elif is_charging:
        speed_kmh = 0.0
        power_kw = estimate_carwings_charging_power_kw(ev_info)

    if prev_state is not None and reading_epoch > prev_state.timestamp_epoch:
        dt_hours = (reading_epoch - prev_state.timestamp_epoch) / 3600.0
        if 0.0027 <= dt_hours <= 0.5:
            if curr_wh is not None and prev_state.wh_content is not None:
                delta_kwh = (prev_state.wh_content - curr_wh) / 1000.0
                calc_power = delta_kwh / dt_hours
                if -150.0 <= calc_power <= 200.0:
                    if is_charging and calc_power > 0:
                        calc_power = -calc_power
                    power_kw = round(calc_power, 2)

            if not is_parked:
                if (
                    curr_lat is not None
                    and curr_lon is not None
                    and prev_state.lat is not None
                    and prev_state.lon is not None
                ):
                    dist_km = haversine_km(prev_state.lat, prev_state.lon, curr_lat, curr_lon)
                    calc_speed = dist_km / dt_hours
                    if 0.0 <= calc_speed <= 200.0:
                        speed_kmh = round(calc_speed, 1)
                elif odometer_km is not None and prev_state.odometer_km is not None:
                    dist_km = max(0.0, odometer_km - prev_state.odometer_km)
                    calc_speed = dist_km / dt_hours
                    if 0.0 <= calc_speed <= 200.0:
                        speed_kmh = round(calc_speed, 1)
    elif prev_state is not None and reading_epoch == prev_state.timestamp_epoch:
        # Preserve differential speed/power across 30s heartbeats of the same TCU reading
        if speed_kmh is None:
            speed_kmh = prev_state.speed_kmh
        if power_kw is None:
            power_kw = prev_state.power_kw

    if speed_kmh is not None:
        tlm["speed"] = speed_kmh
    if power_kw is not None:
        tlm["power"] = power_kw

    new_state = SnapshotState(
        timestamp_epoch=reading_epoch,
        wh_content=curr_wh,
        lat=curr_lat,
        lon=curr_lon,
        odometer_km=odometer_km,
        ev_updated_iso=ev_updated_iso,
        speed_kmh=speed_kmh,
        power_kw=power_kw,
    )
    return tlm, new_state


class ABRPBridge:
    """Asynchronous bridge that pushes OpenCARWINGS vehicle telemetry to ABRP."""

    def __init__(
        self,
        hass: Any,
        ocw_client: Any,
        user_token: str,
        api_key: str = DEFAULT_ABRP_API_KEY,
    ) -> None:
        self.hass = hass
        self.ocw_client = ocw_client
        self.user_token = (user_token or "").strip()
        self.api_key = (api_key or DEFAULT_ABRP_API_KEY).strip()

        try:
            import importlib

            aiohttp_mod = importlib.import_module("homeassistant.helpers.aiohttp_client")
            self._session = aiohttp_mod.async_get_clientsession(hass)
        except Exception:  # pragma: no cover - fallback for test stubs
            self._session = getattr(ocw_client, "_session", None)

        self._prev_states: Dict[str, SnapshotState] = {}
        self._last_sent_times: Dict[str, float] = {}
        self._last_tcu_refresh_times: Dict[str, float] = {}
        self._last_car_data: Dict[str, Dict[str, Any]] = {}
        self._last_trips: Dict[str, Optional[Dict[str, Any]]] = {}
        self._was_active: Dict[str, bool] = {}

    async def _async_fetch_latest_trip(self, vin: str) -> Optional[Dict[str, Any]]:
        """Fetch latest probe trip for extra outside/battery temperatures."""
        if hasattr(self.ocw_client, "async_get_latest_trip"):
            return await self.ocw_client.async_get_latest_trip(vin)
        if hasattr(self.ocw_client, "async_request"):
            try:
                resp = await self.ocw_client.async_request(
                    "GET", f"/api/car/{vin}/probe/trips", params={"page_size": 1}
                )
                if getattr(resp, "status", None) == 200:
                    data = await resp.json()
                    results = data.get("results") if isinstance(data, dict) else None
                    if results and isinstance(results, list):
                        return results[0]
            except Exception as err:
                _LOGGER.debug("Could not fetch probe/trips for %s: %s", vin, err)
        return None

    async def async_send_telemetry(self, tlm: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a v1 telemetry payload to ABRP using Home Assistant's aiohttp session."""
        if not self._session or not self.user_token:
            return None

        params = {
            "api_key": self.api_key,
            "token": self.user_token,
            "tlm": json.dumps(tlm, separators=(",", ":")),
        }
        headers = {"Authorization": f"APIKEY {self.api_key}"}

        kwargs: Dict[str, Any] = {"headers": headers, "params": params}
        try:
            from aiohttp import ClientTimeout

            kwargs["timeout"] = ClientTimeout(total=10)
        except Exception:
            pass

        resp = await self._session.post(ABRP_V1_TLM_URL, **kwargs)
        if resp.status not in (200, 201):
            text = await resp.text()
            _LOGGER.warning("ABRP telemetry push failed (%s): %s", resp.status, text)
            return None
        try:
            return await resp.json()
        except Exception:
            return {"status": "ok"}

    async def async_process_cars(
        self, cars: list[Dict[str, Any]], force_heartbeat: bool = False
    ) -> None:
        """Process updated car list from the coordinator and push telemetry to ABRP if needed."""
        if not self.user_token or not isinstance(cars, list):
            return

        for car_data in cars:
            if not isinstance(car_data, dict):
                continue
            vin = str(car_data.get("vin") or "").strip()
            if not vin:
                continue

            try:
                self._last_car_data[vin] = car_data
                active = is_car_active(car_data)
                was_active = self._was_active.get(vin, False)
                self._was_active[vin] = active

                # Only send telemetry to ABRP when the car is ON / charging,
                # or once when transitioning from active -> parked/off.
                if not active and not was_active:
                    continue

                prev_state = self._prev_states.get(vin)
                ev_info = car_data.get("ev_info") or {}
                ev_updated_iso = ev_info.get("last_updated") or car_data.get("last_connection")

                is_new_reading = (
                    prev_state is None
                    or ev_updated_iso != prev_state.ev_updated_iso
                )

                # Only query probe/trips when a new vehicle reading arrives
                if is_new_reading:
                    self._last_trips[vin] = await self._async_fetch_latest_trip(vin)

                tlm, curr_state = build_abrp_telemetry(
                    car_data=car_data,
                    prev_state=prev_state,
                    latest_trip=self._last_trips.get(vin),
                )

                now = time.time()
                last_sent = self._last_sent_times.get(vin, 0.0)
                heartbeat_due = (now - last_sent) >= ABRP_HEARTBEAT_SECONDS
                just_stopped = (not active) and was_active

                if is_new_reading or heartbeat_due or force_heartbeat or just_stopped:
                    resp = await self.async_send_telemetry(tlm)
                    if resp is not None:
                        self._last_sent_times[vin] = now
                        self._prev_states[vin] = curr_state
                        _LOGGER.debug(
                            "Sent ABRP telemetry for %s | SoC: %s%% | SoE: %s kWh | Range: %s km | Resp: %s",
                            vin,
                            tlm.get("soc", "-"),
                            tlm.get("soe", "-"),
                            tlm.get("est_battery_range", "-"),
                            resp,
                        )
            except Exception as err:
                _LOGGER.warning("Error sending telemetry to ABRP for %s: %s", vin, err)

    async def async_heartbeat(self, coordinator: Any = None) -> None:
        """Periodic 30-second callback while ABRP is enabled.

        - Forces a TCU refresh (command_type=1) every 60s ONLY while actively driving.
        - While charging, relies on OpenCARWINGS server updates (zero extra SIM data)
          and only reads from the server + keeps ABRP online every 30s.
        - When parked and off, does nothing.
        """
        if not self.user_token:
            return

        cars = (
            getattr(coordinator, "data", None)
            if coordinator is not None
            else None
        ) or list(self._last_car_data.values())

        if not cars or not isinstance(cars, list):
            return

        now = time.time()
        active_cars = []
        for car_data in cars:
            if not isinstance(car_data, dict):
                continue
            vin = str(car_data.get("vin") or "").strip()
            if not vin or not is_car_active(car_data):
                continue
            active_cars.append(car_data)

            # Force TCU refresh (command_type=1) ONLY while driving (never while charging)
            # to preserve the 20MB/month IoT SIM data allowance.
            last_tcu_req = self._last_tcu_refresh_times.get(vin, 0.0)
            if (
                is_car_driving(car_data)
                and not car_data.get("command_requested", False)
                and (now - last_tcu_req) >= ABRP_ACTIVE_TCU_REFRESH_SECONDS
                and hasattr(self.ocw_client, "async_request_car_refresh")
            ):
                try:
                    await self.ocw_client.async_request_car_refresh(vin)
                    self._last_tcu_refresh_times[vin] = now
                    _LOGGER.debug("Requested 1-min driving TCU refresh (command_type=1) for %s", vin)
                except Exception as err:
                    _LOGGER.debug("Could not request driving TCU refresh for %s: %s", vin, err)

        if not active_cars:
            return

        # Refresh coordinator so both HA entities and ABRP receive the latest OpenCARWINGS data
        if coordinator is not None and hasattr(coordinator, "async_request_refresh"):
            try:
                await coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.debug("Coordinator refresh during ABRP heartbeat failed: %s", err)

        # Ensure ABRP receives a heartbeat at least every 30s even if car reading timestamp hasn't changed yet
        now_after = time.time()
        due_cars = [
            c for c in active_cars
            if (now_after - self._last_sent_times.get(str(c.get("vin") or "").strip(), 0.0)) >= ABRP_HEARTBEAT_SECONDS
        ]
        if due_cars:
            await self.async_process_cars(due_cars, force_heartbeat=True)

