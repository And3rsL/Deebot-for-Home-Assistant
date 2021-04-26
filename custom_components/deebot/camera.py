"""Support for Deebot Vaccums."""
import base64
import logging
from typing import Optional, Dict, Any

from homeassistant.components.camera import Camera

from .const import *
from .helpers import get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    if hub.liveMapEnabled:
        new_devices = []

        for vacbot in hub.vacbots:
            new_devices.append(DeeboLiveCamera(vacbot, "liveMap"))

        if new_devices:
            async_add_devices(new_devices)


class DeeboLiveCamera(Camera):
    """Deebot Live Camera"""

    def __init__(self, vacbot, device_id):
        """Initialize the Deebot Vacuum."""
        super().__init__()

        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            self._vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            self._vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = self._vacbot_name + "_" + device_id

        _LOGGER.debug("Camera initialized: %s", self.name)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return self._vacbot.vacuum.get("did", None) + "_" + self._id

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return get_device_info(self._vacbot)

    async def async_camera_image(self):
        """Return a still image response from the camera."""

        return base64.decodebytes(self._vacbot.live_map)
