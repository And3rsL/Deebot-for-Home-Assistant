"""Support for Deebot Vaccums."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICES, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from . import hub
from .const import DOMAIN, STARTUP_MESSAGE

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "vacuum", "camera"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""

    if DOMAIN not in hass.data:
        # Print startup message
        _LOGGER.info(STARTUP_MESSAGE)

    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    deebot_hub = hub.DeebotHub(hass, entry.data)
    await deebot_hub.async_setup()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = deebot_hub
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN][entry.entry_id].disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)
        if len(hass.data[DOMAIN]) == 0:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new = {**config_entry.data,
               CONF_VERIFY_SSL: True}

        device_id = "deviceid"
        devices = new.pop(device_id, {})
        new.pop("show_color_rooms")
        new.pop("live_map")

        new[CONF_DEVICES] = devices.get(device_id, [])

        config_entry.data = {**new}

        config_entry.version = 2

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True
