from deebotozmo import VacBot

from .const import DOMAIN


def get_device_info(vacBot: VacBot):
    device: dict = vacBot.vacuum
    identifiers = set()
    if "did" in device:
        identifiers.add((DOMAIN, device.get("did")))
    if "name" in device:
        identifiers.add((DOMAIN, device.get("name")))

    if not identifiers:
        # we don't get a identifier to identify the device correctly abort
        return None

    return {
        "identifiers": identifiers,
        "name": device.get("nick", "Deebot vacuum"),
        "manufacturer": "Ecovacs",
        "model": device.get("deviceName", "Deebot vacuum"),
        "sw_version": vacBot.fwversion,
    }
