import logging
import random
import string
import threading

from deebotozmo import EcoVacsAPI, VacBot

from homeassistant.const import CONF_DEVICES
from homeassistant.core import HomeAssistant
from .const import *

_LOGGER = logging.getLogger(__name__)

# Generate a random device ID on each bootup
DEEBOT_API_DEVICEID = "".join(
    random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
)

DEEBOT_COMPANY_EXCLUDE = ["eco-legacy"]
DEEBOT_MODEL_EXCLUDE = []
DEEBOT_DEVICENAME_EXCLUDE = []


class DeebotHub:
    """Deebot Hub"""

    def __init__(self, hass: HomeAssistant, domain_config):
        """Initialize the Deebot Vacuum."""

        self.config = domain_config
        self._lock = threading.Lock()
        self.hass = hass

        verify_ssl = domain_config.get(CONF_VERIFY_SSL, True)
        self.ecovacs_api = EcoVacsAPI(
            DEEBOT_API_DEVICEID,
            domain_config.get(CONF_USERNAME),
            EcoVacsAPI.md5(domain_config.get(CONF_PASSWORD)),
            domain_config.get(CONF_COUNTRY),
            domain_config.get(CONF_CONTINENT),
            verify_ssl=verify_ssl
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
            if device["company"] in DEEBOT_COMPANY_EXCLUDE or device["model"] in DEEBOT_MODEL_EXCLUDE or device["deviceName"] in DEEBOT_DEVICENAME_EXCLUDE:
                _LOGGER.debug("Device '{}' skipped due to being in the excluded list, device details: {}".format(
                  device["name"], device))
                continue

            if device["name"] in domain_config.get(CONF_DEVICES):
                vacbot = VacBot(
                    self.ecovacs_api.uid,
                    self.ecovacs_api.resource,
                    self.ecovacs_api.user_access_token,
                    device,
                    country,
                    continent,
                    liveMapEnabled,
                    liveMapRooms,
                    verify_ssl=verify_ssl
                )

                _LOGGER.debug("New vacbot found: " + device["name"])
                
                self.hass.async_add_executor_job(vacbot.setScheduleUpdates)
                self.vacbots.append(vacbot)

        _LOGGER.debug("Hub initialized")

    def disconnect(self):
        for device in self.vacbots:
            device.disconnect()

    @property
    def name(self):
        """ Return the name of the hub."""
        return "Deebot Hub"
