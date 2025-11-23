"""Heizoel24 MEX sensor integration."""

from __future__ import annotations

from datetime import timedelta
import logging

import aiohttp

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DATA_URL, DOMAIN, LOGIN_URL

_LOGGER = logging.getLogger(__name__)

DEVICE_PROPERTIES = {
    "MaxVolume": {
        "name": "Oil free capacity",
        "native_unit_of_measurement": UnitOfVolume.LITERS,
        "device_class": SensorDeviceClass.GAS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "attr_icon": "mdi:storage-tank-outline",
    },
    "CurrentVolume": {
        "name": "Oil in stock",
        "native_unit_of_measurement": UnitOfVolume.LITERS,
        "device_class": SensorDeviceClass.VOLUME,
        "state_class": SensorStateClass.TOTAL,
        "attr_icon": "mdi:storage-tank",
    },
    "CurrentVolumePercentage": {
        "name": "Oil fill level",
        "native_unit_of_measurement": PERCENTAGE,
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "attr_icon": "mdi:gauge",
    },
    "Usage": {
        "name": "Oil usage",
        "native_unit_of_measurement": "L/day",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "attr_icon": "mdi:oil",
        "suggested_display_precision": 2,
    },
    "LastOrderPrice": {
        "name": "Last order price",
        "native_unit_of_measurement": "cur/L",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "attr_icon": "mdi:cash",
        "suggested_display_precision": 4,
    },
    "RemainingDays": {
        "name": "Oil remaining",
        "native_unit_of_measurement": UnitOfTime.DAYS,
        "device_class": None,
        "state_class": None,
        "attr_icon": "mdi:timer",
    },
    "BatteryPercentage": {
        "name": "MEX Battery level",
        "native_unit_of_measurement": PERCENTAGE,
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "attr_icon": "mdi:battery",
    },
    "SensorId": {
        "name": "MEX Sensor ID",
        "native_unit_of_measurement": None,
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "attr_icon": "mdi:water-circle",
    },
}

# Time between updating data
SCAN_INTERVAL = timedelta(hours=12)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigType, add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][config.entry_id]

    entities = []
    entities.extend(HeizOel24MexSensor(coordinator, key) for key in DEVICE_PROPERTIES)
    add_entities(entities)


class Heizoel24MexData:
    """Class which gets the data."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize Data constructor."""
        self._auth = {"Login": {"UserName": username, "Password": password}}
        self._data = None

    async def fetch_data(self) -> None:
        """Get the data from the web api."""
        try:
            async with aiohttp.ClientSession() as session:
                loginResult = await session.post(LOGIN_URL, json=self._auth)
                if not (await loginResult.json())["Success"]:
                    raise ConfigEntryAuthFailed
                async with session.get(DATA_URL) as result:
                    self._data = await result.json()
        except ConfigEntryAuthFailed:
            raise
        except Exception as e:
            msg = f"{e.__class__} occurred details: {e}"
            _LOGGER.warning(msg)
            msg = f"Error communicating with API: {e}"
            raise UpdateFailed(msg) from e

    def get_reading(self, property: str) -> any:
        """Get the reading, assuming we have just one sensor."""
        return self.get_data().get(property)

    def get_data(self) -> dict:
        """Get the reading data, assuming we have just one sensor."""
        return self._data.get("Items", [{"0": None}])[0]


# see https://developers.home-assistant.io/docs/integration_fetching_data/
class Heizoel24MexCoordinator(DataUpdateCoordinator):
    """Represents Coordinator for this sensor."""

    def __init__(self, hass: HomeAssistant, heizoel_data) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Heizoel24MexCoordinator",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=SCAN_INTERVAL,
        )
        self.heizoel_data = heizoel_data

    async def _async_update_data(self):
        return await self.heizoel_data.fetch_data()

    def get_reading(self, property: str) -> any:
        """Get the actual reaging."""
        return self.heizoel_data.get_reading(property)

    def get_data(self) -> any:
        """Get the whole reaging data."""
        return self.heizoel_data.get_data()


class HeizOel24MexSensor(CoordinatorEntity, SensorEntity):
    """Implementation of the HeizOel24MexSensor."""

    def __init__(self, coordinator, property) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._property = property
        self._attr_unique_id = DOMAIN + ".mex_" + property

        self._attr_name = DEVICE_PROPERTIES[property]["name"]
        self._attr_native_unit_of_measurement = DEVICE_PROPERTIES[property][
            "native_unit_of_measurement"
        ]
        self._attr_device_class = DEVICE_PROPERTIES[property]["device_class"]
        self._attr_state_class = DEVICE_PROPERTIES[property]["state_class"]
        self._attr_icon = DEVICE_PROPERTIES[property]["attr_icon"]
        self._attr_suggested_display_precision = DEVICE_PROPERTIES[property].get(
            "suggested_display_precision"
        )
        self.update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update()
        self.async_write_ha_state()

    def update(self) -> None:
        """Update the data values."""
        try:
            self._attr_native_value = self.coordinator.get_reading(self._property)
            if self._property == "SensorId":
                self._attr_extra_state_attributes = self.coordinator.get_data()
            if self._property == "LastOrderPrice":
                try:
                    self._attr_native_value = self._attr_native_value/100.0
                except TypeError:
                    _LOGGER.info("Last order price not avalilable")
            if self._property == "MaxVolume":
                try:
                    self._attr_native_value = self._attr_native_value - self.coordinator.get_reading("CurrentVolume")
                except TypeError:
                    _LOGGER.info("Max or current volume not avalilable")
        except Exception as e:
            _LOGGER.warning(f"uexpected problem: {e.__class__} occurred details: {e}")
