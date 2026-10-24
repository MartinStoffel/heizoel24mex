"""Heizoel24 MEX sensor integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LEGACY_SENSOR_ID, DOMAIN, LEGACY_UNIQUE_ID_PREFIX
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
    "TankCapacity": {
        "name": "Oil tank capacity",
        # MaxVolume as is; the key MaxVolume is taken by "Oil free capacity"
        "source": "MaxVolume",
        "native_unit_of_measurement": UnitOfVolume.LITERS,
        "device_class": SensorDeviceClass.VOLUME_STORAGE,
        "state_class": None,
        "attr_icon": "mdi:barrel",
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
        "device_class": SensorDeviceClass.DURATION,
        "state_class": None,
        "attr_icon": "mdi:timer",
    },
    "BatteryPercentage": {
        "name": "Battery level",
        "native_unit_of_measurement": PERCENTAGE,
        "device_class": SensorDeviceClass.BATTERY,
        "state_class": SensorStateClass.MEASUREMENT,
        # The battery device class shows an icon matching the level
        "attr_icon": None,
        "entity_category": EntityCategory.DIAGNOSTIC,
    },
    "SensorId": {
        "name": "Sensor ID",
        "native_unit_of_measurement": None,
        "device_class": None,
        "state_class": None,
        "attr_icon": "mdi:water-circle",
    },
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors of all MEX sensors, including ones added later."""
    coordinator: Heizoel24MexCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_sensor_ids: set[str] = set()

    @callback
    def _async_add_new_sensors() -> None:
        new_sensor_ids = [i for i in coordinator.data if i not in known_sensor_ids]
        known_sensor_ids.update(new_sensor_ids)
        async_add_entities(
            HeizOel24MexSensor(coordinator, sensor_id, key)
            for sensor_id in new_sensor_ids
            for key in DEVICE_PROPERTIES
        )

    _async_add_new_sensors()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_sensors))


class HeizOel24MexSensor(CoordinatorEntity[Heizoel24MexCoordinator], SensorEntity):
    """A reading of one MEX sensor."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: Heizoel24MexCoordinator, sensor_id: str, key: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_id = sensor_id
        self._key = key
        if sensor_id == coordinator.config_entry.data.get(CONF_LEGACY_SENSOR_ID):
            # Created before multi-sensor support; keep the unique ID and history
            self._attr_unique_id = LEGACY_UNIQUE_ID_PREFIX + key
        else:
            self._attr_unique_id = f"{sensor_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, sensor_id)},
            name=f"MEX {sensor_id}",
            manufacturer="HeizOel24",
            model="MEX",
        )

        properties = DEVICE_PROPERTIES[key]
        # The API field to read, if it differs from the key
        self._source = properties.get("source", key)
        self._attr_name = properties["name"]
        self._attr_native_unit_of_measurement = properties["native_unit_of_measurement"]
        self._attr_device_class = properties["device_class"]
        self._attr_state_class = properties["state_class"]
        self._attr_icon = properties["attr_icon"]
        self._attr_suggested_display_precision = properties.get(
            "suggested_display_precision"
        )
        self._attr_entity_category = properties.get("entity_category")
        self._update_from_coordinator()

    @property
    def available(self) -> bool:
        """Return if the sensor is still reported by the web API."""
        return super().available and self._sensor_id in self.coordinator.data

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_coordinator()
        self.async_write_ha_state()

    def _update_from_coordinator(self) -> None:
        """Update the sensor value from the readings of its MEX sensor."""
        data = self.coordinator.data.get(self._sensor_id)
        if data is None:
            # The sensor is gone from the account; it is shown as unavailable
            return
        value = data.get(self._source)
        try:
            if self._key == "MaxVolume":
                # Free capacity. It must become unknown if a volume is missing:
                # reporting the whole tank would count as consumption in the
                # energy dashboard.
                value = value - data["CurrentVolume"]
            elif self._key == "LastOrderPrice":
                # The API reports the price per 100 L
                value = value / 100.0
            elif self._key == "BatteryPercentage" and not 0 <= value <= 100:
                # Not a battery level, e.g. a placeholder for "no value"
                value = None
        except (KeyError, TypeError):
            _LOGGER.debug("%s of %s is not available", self._key, self._sensor_id)
            value = None
        self._attr_native_value = value
        if self._key == "SensorId":
            # The readings of this MEX sensor only
            self._attr_extra_state_attributes = data
