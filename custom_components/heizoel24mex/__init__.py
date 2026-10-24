"""The Heizoel24 MEX integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import CONF_LEGACY_SENSOR_ID, DOMAIN, LEGACY_UNIQUE_ID_PREFIX
from .coordinator import Heizoel24MexCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Heizoel24 MEX from a config entry."""
    _async_set_account_unique_id(hass, entry)
    coordinator = Heizoel24MexCoordinator(
        hass, entry, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )
    await coordinator.async_config_entry_first_refresh()
    _async_assign_legacy_sensor(hass, entry, coordinator)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow deleting the device of a sensor that is gone from the account."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None:
        # Not loaded, so it's unknown which sensors still exist
        return False
    return not any(
        domain == DOMAIN and sensor_id in coordinator.data
        for domain, sensor_id in device_entry.identifiers
    )


@callback
def _async_set_account_unique_id(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Identify entries created before the account check by their account.

    This lets the config flow reject adding the same account again.
    """
    if entry.unique_id is not None:
        return
    unique_id = entry.data[CONF_USERNAME].strip().lower()
    if not any(
        other.unique_id == unique_id
        for other in hass.config_entries.async_entries(DOMAIN)
    ):
        hass.config_entries.async_update_entry(entry, unique_id=unique_id)


@callback
def _async_assign_legacy_sensor(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: Heizoel24MexCoordinator
) -> None:
    """Remember which sensor the entities from before multi-sensor support show.

    Those entities always showed the first sensor in the API response. Storing
    its ID lets them keep their unique IDs, and so their history, even if the
    order of the sensors changes later.
    """
    if CONF_LEGACY_SENSOR_ID in entry.data:
        return
    registry = er.async_get(hass)
    if any(
        entity.unique_id.startswith(LEGACY_UNIQUE_ID_PREFIX)
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
    ):
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_LEGACY_SENSOR_ID: next(iter(coordinator.data))},
        )
