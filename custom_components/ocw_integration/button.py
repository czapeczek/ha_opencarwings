"""Button platform providing a manual refresh button for OpenCARWINGS."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from homeassistant.components.button import ButtonEntity
from typing import Any

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")

    # Create a single per-entry refresh button
    entities = [OpenCarWingsRefreshButton(entry.entry_id, coordinator=coordinator)]

    # Create per-car command buttons for each car
    cars = data.get("cars", [])
    for car in cars:
        if car.get("vin"):
            # Data refresh and charging commands
            entities.append(CarRefreshButton(entry.entry_id, car))
            entities.append(CarChargeStartButton(entry.entry_id, car))
            entities.append(CarChargeStart80Button(entry.entry_id, car))
            
            # Horn and lights
            entities.append(CarHornButton(entry.entry_id, car))
            entities.append(CarLightsButton(entry.entry_id, car))
            entities.append(CarHornLightsButton(entry.entry_id, car))
            entities.append(CarStopHornLightsButton(entry.entry_id, car))
            
            # Door control (requires PIN)
            entities.append(CarDoorUnlockButton(entry.entry_id, car))
            entities.append(CarDoorLockButton(entry.entry_id, car))
            
            # Engine control (requires PIN)
            entities.append(CarRemoteStartButton(entry.entry_id, car))
            entities.append(CarRemoteStopButton(entry.entry_id, car))

    # Tests set hass on the entity for direct method calls
    for ent in entities:
        ent.hass = hass

    async_add_entities(entities)


class OpenCarWingsRefreshButton(ButtonEntity):
    """Button that triggers a coordinator refresh when pressed."""

    def __init__(self, entry_id: str, coordinator=None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._attr_icon = "mdi:refresh"

    @property
    def name(self) -> str:
        return "OpenCARWINGS Refresh"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_refresh_{self._entry_id}"

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


class CommandButton(ButtonEntity):
    """Base button that exposes the latest API command response."""

    def _store_command_response(self, command_type: int, response: dict) -> None:
        data = self.hass.data[DOMAIN][self._entry_id]
        responses = data.setdefault("last_command_responses", {})
        responses[self._vin] = {
            "command_type": command_type,
            "message": response.get("message") if isinstance(response, dict) else None,
            "car": response.get("car") if isinstance(response, dict) else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.async_write_ha_state()

    def _get_car_timestamp(self, coordinator) -> str | None:
        cars = getattr(coordinator, 'data', None) or []
        if isinstance(cars, list):
            for car in cars:
                if isinstance(car, dict) and car.get('vin') == self._vin:
                    ev = car.get('ev_info') or {}
                    return ev.get('last_updated') or car.get('last_connection')
        return None

    async def _async_follow_up_refresh(self, coordinator, initial_ts: str | None) -> None:
        for _ in range(12):
            await asyncio.sleep(5)
            try:
                await coordinator.async_request_refresh()
            except Exception:
                return
            if self._get_car_timestamp(coordinator) != initial_ts:
                return

    def _command_attributes(self) -> dict[str, Any]:
        response = (
            self.hass.data.get(DOMAIN, {})
            .get(self._entry_id, {})
            .get("last_command_responses", {})
            .get(self._vin, {})
        )
        return {
            "entry_id": self._entry_id,
            "vin": self._vin,
            "last_command_type": response.get("command_type"),
            "last_command_message": response.get("message"),
            "last_command_car": response.get("car"),
            "last_command_at": response.get("timestamp"),
        }


class CarRefreshButton(CommandButton):
    """Button that sends a 'Refresh data' command for a specific car."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._attr_icon = "mdi:refresh"

    @property
    def name(self) -> str:
        # Friendly label: prefer car nickname, then model name, then VIN
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Request data refresh"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_refresh_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        """Press the button to send a 'Refresh data' command to the API for this car."""
        client = hass_client(self.hass, self._entry_id)
        try:
            response = await client.async_request_car_refresh(self._vin)
            self._store_command_response(1, response)
        except Exception:  # pragma: no cover - network
            _LOGGER.exception("Failed to request car refresh for %s", self._vin)
            raise

        # The vehicle update is asynchronous. Poll the server briefly so this
        # button returns the newly requested vehicle data instead of the old cache.
        coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
        if not coordinator:
            return

        initial_ts = self._get_car_timestamp(coordinator)
        updated = False
        for attempt in range(5):
            try:
                await coordinator.async_request_refresh()
            except Exception:  # pragma: no cover - coordinator failure
                _LOGGER.exception('Failed to refresh data after requesting car refresh for %s', self._vin)
                raise

            if self._get_car_timestamp(coordinator) != initial_ts:
                updated = True
                break

            if attempt < 4:
                await asyncio.sleep(2)

        if not updated and hasattr(self.hass, 'async_create_task'):
            self.hass.async_create_task(
                self._async_follow_up_refresh(coordinator, initial_ts)
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


def hass_client(hass, entry_id: str):
    """Helper to get the API client stored in hass.data."""
    return hass.data[DOMAIN][entry_id]["client"]


def hass_command_pin(hass, entry_id: str) -> str | None:
    """Return the configured command PIN, preferring current options."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        return None
    options = getattr(entry, "options", {}) or {}
    data = getattr(entry, "data", {}) or {}
    pin = options.get("command_pin", data.get("command_pin", ""))
    return pin.strip() or None if isinstance(pin, str) else None


class CarChargeStartButton(CommandButton):
    """Button that sends a 'Charge start' command for a specific car."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 2  # Charge start
        self._attr_icon = "mdi:battery-charging"

    @property
    def name(self) -> str:
        # Friendly label: prefer car nickname, then model name, then VIN
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Charge start"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_chargestart_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        """Press the button to send a 'Charge start' command to the API for this car."""
        client = hass_client(self.hass, self._entry_id)
        try:
            response = await client.async_send_command(self._vin, self._command_type)
            self._store_command_response(self._command_type, response)
        except Exception:  # pragma: no cover - network
            _LOGGER.exception("Failed to send command %s for %s", self._command_type, self._vin)
            raise

        # Trigger a coordinator refresh after sending the command
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:  # pragma: no cover - coordinator failure
            _LOGGER.exception("Failed to trigger coordinator refresh after command for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


class CarChargeStart80Button(CommandButton):
    """Button that sends a 'Charge start 80%' command for a specific car."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 6  # Charge start 80%
        self._attr_icon = "mdi:battery-80"

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Start charge untill 80%"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_chargestart80_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            response = await client.async_send_command(self._vin, self._command_type)
            self._store_command_response(self._command_type, response)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


class CarACOnButton(CommandButton):
    """Button that sends 'A/C on' command for a specific car."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 3  # A/C on
        self._attr_icon = "mdi:air-conditioner"

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"A/C on for {label}"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_ac_on_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            response = await client.async_send_command(self._vin, self._command_type)
            self._store_command_response(self._command_type, response)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


class CarACOffButton(CommandButton):
    """Button that sends 'A/C off' command for a specific car."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 4  # A/C off
        self._attr_icon = "mdi:air-conditioner"

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"A/C off for {label}"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_ac_off_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            response = await client.async_send_command(self._vin, self._command_type)
            self._store_command_response(self._command_type, response)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


class CarHornButton(CommandButton):
    """Button that sends 'Horn' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 9  # Horn
        self._attr_icon = "mdi:bullhorn"

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Horn ON"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_horn_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = hass_command_pin(self.hass, self._entry_id)
            response = await client.async_send_command(self._vin, self._command_type, pin)
            self._store_command_response(self._command_type, response)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


class CarLightsButton(CommandButton):
    """Button that sends 'Lights' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 10  # Lights
        self._attr_icon = "mdi:car-light-high"

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Lights ON"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_lights_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = hass_command_pin(self.hass, self._entry_id)
            response = await client.async_send_command(self._vin, self._command_type, pin)
            self._store_command_response(self._command_type, response)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


class CarHornLightsButton(CommandButton):
    """Button that sends 'Horn & Lights' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 11  # Horn & Lights
        self._attr_icon = "mdi:alarm-light"

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Horn & Lights ON"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_horn_lights_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = hass_command_pin(self.hass, self._entry_id)
            response = await client.async_send_command(self._vin, self._command_type, pin)
            self._store_command_response(self._command_type, response)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


class CarStopHornLightsButton(CommandButton):
    """Button that sends 'Stop Horn & Light' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 12  # Stop Horn & light
        self._attr_icon = "mdi:alarm-light-off"

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Horn & Lights OFF"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_stop_horn_lights_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = hass_command_pin(self.hass, self._entry_id)
            response = await client.async_send_command(self._vin, self._command_type, pin)
            self._store_command_response(self._command_type, response)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


class CarDoorUnlockButton(CommandButton):
    """Button that sends 'Door unlock' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 7  # Door unlock
        self._attr_icon = "mdi:lock-open-variant"

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Door UNLOCK"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_door_unlock_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = hass_command_pin(self.hass, self._entry_id)
            response = await client.async_send_command(self._vin, self._command_type, pin)
            self._store_command_response(self._command_type, response)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


class CarDoorLockButton(CommandButton):
    """Button that sends 'Door lock' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 8  # Door lock
        self._attr_icon = "mdi:lock"

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Door LOCK"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_door_lock_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = hass_command_pin(self.hass, self._entry_id)
            response = await client.async_send_command(self._vin, self._command_type, pin)
            self._store_command_response(self._command_type, response)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


class CarRemoteStartButton(CommandButton):
    """Button that sends 'Remote Start' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 13  # Remote Start
        self._attr_icon = "mdi:engine"

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Remote START"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_remote_start_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = hass_command_pin(self.hass, self._entry_id)
            response = await client.async_send_command(self._vin, self._command_type, pin)
            self._store_command_response(self._command_type, response)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()


class CarRemoteStopButton(CommandButton):
    """Button that sends 'Remote Stop' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 14  # Remote Stop
        self._attr_icon = "mdi:engine-off"

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Remote STOP"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_car_remote_stop_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = hass_command_pin(self.hass, self._entry_id)
            response = await client.async_send_command(self._vin, self._command_type, pin)
            self._store_command_response(self._command_type, response)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._command_attributes()
