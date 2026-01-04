"""Button platform providing a manual refresh button for OpenCARWINGS."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from typing import Any

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")

    # Create a single per-entry refresh button
    entities = [OpenCarWingsRefreshButton(entry.entry_id, coordinator=coordinator)]

    # Tests set hass on the entity for direct method calls
    for ent in entities:
        ent.hass = hass

    async_add_entities(entities)


class OpenCarWingsRefreshButton(ButtonEntity):
    """Button that triggers a coordinator refresh when pressed."""

    def __init__(self, entry_id: str, coordinator=None) -> None:
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