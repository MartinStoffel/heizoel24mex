"""Heizoel24 MEX sensor integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Heizoel24MexCoordinator

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
        "state_class": None,
        "attr_icon": "mdi:water-circle",
    },
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors."""
    coordinator: Heizoel24MexCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        HeizOel24MexSensor(coordinator, key) for key in DEVICE_PROPERTIES
    )


class HeizOel24MexSensor(CoordinatorEntity[Heizoel24MexCoordinator], SensorEntity):
    """Implementation of the HeizOel24MexSensor."""

    def __init__(self, coordinator: Heizoel24MexCoordinator, key: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = DOMAIN + ".mex_" + key

        properties = DEVICE_PROPERTIES[key]
        self._attr_name = properties["name"]
        self._attr_native_unit_of_measurement = properties["native_unit_of_measurement"]
        self._attr_device_class = properties["device_class"]
        self._attr_state_class = properties["state_class"]
        self._attr_icon = properties["attr_icon"]
        self._attr_suggested_display_precision = properties.get(
            "suggested_display_precision"
        )
        self._update_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_coordinator()
        self.async_write_ha_state()

    def _update_from_coordinator(self) -> None:
        """Update the sensor value from the coordinator data."""
        data = self.coordinator.data
        value = data.get(self._key)
        try:
            if self._key == "MaxVolume":
                # Free capacity. It must become unknown if a volume is missing:
                # reporting the whole tank would count as consumption in the
                # energy dashboard.
                value = value - data["CurrentVolume"]
            elif self._key == "LastOrderPrice":
                # The API reports the price per 100 L
                value = value / 100.0
        except (KeyError, TypeError):
            _LOGGER.debug("%s is not available", self._key)
            value = None
        self._attr_native_value = value
        if self._key == "SensorId":
            self._attr_extra_state_attributes = data
