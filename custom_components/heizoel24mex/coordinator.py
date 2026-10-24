"""Data update coordinator for the Heizoel24 MEX integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DATA_URL, LOGIN_URL, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)

# Time between updating data
SCAN_INTERVAL = timedelta(hours=12)


# see https://developers.home-assistant.io/docs/integration_fetching_data/
class Heizoel24MexCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetches the readings of all MEX sensors of an account from the web API."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, username: str, password: str
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="Heizoel24MexCoordinator",
            update_interval=SCAN_INTERVAL,
        )
        self._auth = {"Login": {"UserName": username, "Password": password}}

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Log in and fetch the readings of the MEX sensors from the web API."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as session:
                async with session.post(LOGIN_URL, json=self._auth) as login_result:
                    if not (await login_result.json())["Success"]:
                        raise ConfigEntryAuthFailed("Login rejected by HeizOel24")
                async with session.get(DATA_URL) as result:
                    result.raise_for_status()
                    data = await result.json()
        except ConfigEntryAuthFailed:
            raise
        except Exception as e:
            _LOGGER.warning("%s occurred details: %s", e.__class__, e)
            msg = f"Error communicating with API: {e}"
            raise UpdateFailed(msg) from e

        # Readings by sensor ID, in the order of the API response
        items = data.get("Items") if isinstance(data, dict) else None
        readings = {
            str(item["SensorId"]): item
            for item in items or []
            if isinstance(item, dict) and item.get("SensorId") is not None
        }
        if not readings:
            raise UpdateFailed("No MEX sensor readings in the API response")
        return readings
