import asyncio
import random
import logging
import threading
import async_timeout
import string
from datetime import timedelta
from homeassistant.util import Throttle
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from deebotozmo import EcoVacsAPI, VacBot
from .const import *

_LOGGER = logging.getLogger(__name__)

# Generate a random device ID on each bootup
DEEBOT_API_DEVICEID = "".join(
    random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
)


class DeebotHub:
    """Deebot Hub"""

    def __init__(self, hass, domain_config):
        """Initialize the Deebot Vacuum."""

        self.config = domain_config
        self._lock = threading.Lock()
        self.hass = hass

        self.ecovacs_api = EcoVacsAPI(
            DEEBOT_API_DEVICEID,
            domain_config.get(CONF_USERNAME),
            EcoVacsAPI.md5(domain_config.get(CONF_PASSWORD)),
            domain_config.get(CONF_COUNTRY),
            domain_config.get(CONF_CONTINENT),
        )

        devices = self.ecovacs_api.devices()
        liveMapEnabled = domain_config.get(CONF_LIVEMAP)
        liveMapRooms = domain_config.get(CONF_SHOWCOLORROOMS)
        country = domain_config.get(CONF_COUNTRY).lower()
        continent = domain_config.get(CONF_CONTINENT).lower()
        self.vacbots = []

        # CREATE VACBOT FOR EACH DEVICE
        for device in devices:
            if device["name"] in domain_config.get(CONF_DEVICEID)[CONF_DEVICEID]:
                vacbot = VacBot(
                    self.ecovacs_api.uid,
                    self.ecovacs_api.resource,
                    self.ecovacs_api.user_access_token,
                    device,
                    country,
                    continent,
                    liveMapEnabled,
                    liveMapRooms,
                )

                _LOGGER.debug("New vacbot found: " + device["name"])
                vacbot.setScheduleUpdates()

                self.vacbots.append(vacbot)

        _LOGGER.debug("Hub initialized")

    @property
    def name(self):
        """ Return the name of the hub."""
        return "Deebot Hub"