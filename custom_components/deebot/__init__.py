"""Support for Deebot Vaccums."""
import asyncio
import logging
from typing import Any, Dict

from awesomeversion import AwesomeVersion
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICES, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant

from . import hub
from .const import (
    CONF_BUMPER,
    CONF_CLIENT_DEVICE_ID,
    DOMAIN,
    MIN_REQUIRED_HA_VERSION,
    STARTUP_MESSAGE,
)
from .helpers import get_bumper_device_id

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "vacuum", "camera"]


def is_ha_supported() -> bool:
    """Return True, if current HA version is supported."""
    if AwesomeVersion(HA_VERSION) >= MIN_REQUIRED_HA_VERSION:
        return True

    _LOGGER.error(
        'Unsupported HA version! Please upgrade home assistant at least to "%s"',
        MIN_REQUIRED_HA_VERSION,
    )
    return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""

    if DOMAIN not in hass.data:
        # Print startup message
        _LOGGER.info(STARTUP_MESSAGE)

    if not is_ha_supported():
        return False

    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    deebot_hub = hub.DeebotHub(hass, entry.data)
    await deebot_hub.async_setup()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = deebot_hub
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %d", config_entry.version)

    if config_entry.version == 1:
        new: Dict[str, Any] = {**config_entry.data, CONF_VERIFY_SSL: True}

        device_id = "deviceid"
        devices = new.pop(device_id, {})
        new.pop("show_color_rooms")
        new.pop("live_map")

        new[CONF_DEVICES] = devices.get(device_id, [])

        config_entry.data = {**new}
        config_entry.version = 2

    if config_entry.version == 2:
        new = {**config_entry.data}

        if new.get(CONF_USERNAME) == CONF_BUMPER:
            new[CONF_CLIENT_DEVICE_ID] = get_bumper_device_id(hass)

        config_entry.data = {**new}
        config_entry.version = 3

    _LOGGER.info("Migration to version %d successful", config_entry.version)

    return True
