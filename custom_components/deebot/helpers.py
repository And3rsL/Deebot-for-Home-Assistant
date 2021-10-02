"""Helpers module."""
from typing import Dict, Optional

from deebotozmo.models import Vacuum
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.core import HomeAssistant
from homeassistant.util import uuid

from .const import DOMAIN


def get_device_info(vacuum_bot: VacuumBot) -> Optional[Dict]:
    """Return device info for given vacuum."""
    device: Vacuum = vacuum_bot.vacuum
    identifiers = set()
    if device.did:
        identifiers.add((DOMAIN, device.did))
    if device.name:
        identifiers.add((DOMAIN, device.name))

    if not identifiers:
        # we don't get a identifier to identify the device correctly abort
        return None

    return {
        "identifiers": identifiers,
        "name": device.get("nick", "Deebot vacuum"),
        "manufacturer": "Ecovacs",
        "model": device.get("deviceName", "Deebot vacuum"),
        "sw_version": vacuum_bot.fw_version,
    }


def get_bumper_device_id(hass: HomeAssistant) -> str:
    """Return bumper device id."""
    try:
        location_name = hass.config.location_name.strip().replace(" ", "_")
    except Exception:  # pylint: disable=broad-except
        location_name = ""
    return f"Deebot-4-HA_{location_name}_{uuid.random_uuid_hex()[:4]}"
