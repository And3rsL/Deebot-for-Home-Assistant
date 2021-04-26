import logging
import random
import string
import threading

from deebotozmo import EcoVacsAPI, VacBot
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import *

_LOGGER = logging.getLogger(__name__)

# Generate a random device ID on each bootup
DEEBOT_API_DEVICEID = "".join(
    random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
)


class DeebotHub:
    """Deebot Hub"""

    def __init__(self, hass: HomeAssistant, domain_config):
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
        self.liveMapEnabled = liveMapEnabled

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
        
    def disconnect(self):
        for device in self.vacbots:
            device.disconnect()

    @property
    def name(self):
        """ Return the name of the hub."""
        return "Deebot Hub"
