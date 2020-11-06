"""Support for Deebot Sensor."""
from typing import Optional

from deebotozmo import *
from homeassistant.components.binary_sensor import BinarySensorEntity

from . import HUB as hub

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Deebot binary sensor platform."""
    hub.update()

    for vacbot in hub.vacbots:
        add_devices([DeebotMopAttachedBinarySensor(vacbot, "mop_attached")], True)


class DeebotMopAttachedBinarySensor(BinarySensorEntity):
    """Deebot mop attached binary sensor"""

    def __init__(self, vacbot: VacBot, device_id: str):
        """Initialize the Sensor."""
        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            self._vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            self._vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = self._vacbot_name + "_" + device_id

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def is_on(self):
        return self._vacbot.mop_attached

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        return "mdi:water" if self.is_on else "mdi:water-off"
