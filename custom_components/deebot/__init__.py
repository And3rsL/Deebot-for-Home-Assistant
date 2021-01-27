"""Support for Deebot Vaccums."""
import asyncio
import logging
import async_timeout
import time
import random
import string
import base64
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from datetime import timedelta
from deebotozmo import *
from homeassistant.util import Throttle
from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_HOMEASSISTANT_STOP

REQUIREMENTS = ['deebotozmo==1.7.8']

CONF_COUNTRY = "country"
CONF_CONTINENT = "continent"
CONF_DEVICEID = "deviceid"
CONF_LIVEMAPPATH = "livemappath"
CONF_LIVEMAP = "live_map"
CONF_SHOWCOLORROOMS = "show_color_rooms"
DEEBOT_DEVICES = "deebot_devices"

# Generate a random device ID on each bootup
DEEBOT_API_DEVICEID = "".join(
    random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
)

_LOGGER = logging.getLogger(__name__)

HUB = None
DOMAIN = 'deebot'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_COUNTRY): vol.All(vol.Lower, cv.string),
        vol.Required(CONF_CONTINENT): vol.All(vol.Lower, cv.string),
        vol.Required(CONF_DEVICEID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_LIVEMAP, default=True): cv.boolean,
        vol.Optional(CONF_SHOWCOLORROOMS, default=False): cv.boolean,
        vol.Optional(CONF_LIVEMAPPATH, default='www/'): cv.string
    }),
}, extra=vol.ALLOW_EXTRA)

def setup(hass, config):
    """Set up the Deebot."""
    global HUB

    HUB = DeebotHub(config[DOMAIN])

    for component in ('sensor', 'binary_sensor', 'vacuum'):
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    return True

class DeebotHub(Entity):
    """Deebot Hub"""

    def __init__(self, domain_config):
        """Initialize the Deebot Vacuum."""

        self.config = domain_config
        self._lock = threading.Lock()
        
        self.ecovacs_api = EcoVacsAPI(
            DEEBOT_API_DEVICEID,
            domain_config.get(CONF_USERNAME),
            EcoVacsAPI.md5(domain_config.get(CONF_PASSWORD)),
            domain_config.get(CONF_COUNTRY),
            domain_config.get(CONF_CONTINENT)
            )

        devices = self.ecovacs_api.devices()
        liveMapEnabled = domain_config.get(CONF_LIVEMAP)
        liveMapRooms = domain_config.get(CONF_SHOWCOLORROOMS)
        country = domain_config.get(CONF_COUNTRY).lower()
        continent = domain_config.get(CONF_CONTINENT).lower()
        self.vacbots = []

        # CREATE VACBOT FOR EACH DEVICE
        for device in devices:
            if device['name'] in domain_config.get(CONF_DEVICEID):
                vacbot = VacBot(
                    self.ecovacs_api.uid,
                    self.ecovacs_api.resource,
                    self.ecovacs_api.user_access_token,
                    device,
                    country,
                    continent,
                    liveMapEnabled,
                    liveMapRooms
                )
                
                _LOGGER.debug("New vacbot found: " + device['name'])

                self.vacbots.append(vacbot)

        _LOGGER.debug("Hub initialized")

    @Throttle(timedelta(seconds=10))
    def update(self):
        """ Update all statuses. """
        try:
            for vacbot in self.vacbots:
                vacbot.request_all_statuses()
        except Exception as ex:
            _LOGGER.error('Update failed: %s', ex)
            raise

    @property
    def name(self):
        """ Return the name of the hub."""
        return "Deebot Hub"