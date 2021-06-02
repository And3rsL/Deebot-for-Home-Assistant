import logging
import random
import string
from typing import Any, Mapping

import aiohttp
from deebotozmo.ecovacs_api import EcovacsAPI
from deebotozmo.util import md5
from deebotozmo.vacuum_bot import VacuumBot

from homeassistant.const import CONF_DEVICES
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
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

        self.config: Mapping[str, Any] = domain_config
        self.hass: HomeAssistant = hass
        self.country: str = domain_config.get(CONF_COUNTRY).lower()
        self.continent: str = domain_config.get(CONF_CONTINENT).lower()
        self.vacbots: [VacuumBot] = []
        self.verify_ssl = domain_config.get(CONF_VERIFY_SSL, True)
        self._session: aiohttp.ClientSession = aiohttp_client.async_get_clientsession(self.hass,
                                                                                      verify_ssl=self.verify_ssl)

        self.ecovacs_api = EcovacsAPI(
            self._session,
            DEEBOT_API_DEVICEID,
            domain_config.get(CONF_USERNAME),
            md5(domain_config.get(CONF_PASSWORD)),
            self.country,
            self.continent,
            verify_ssl=self.verify_ssl
        )

    async def async_initialize(self):
        await self.ecovacs_api.login()
        devices = await self.ecovacs_api.get_devices()

        # CREATE VACBOT FOR EACH DEVICE
        for device in devices:
            if device["name"] in self.config.get(CONF_DEVICES):
                vacbot = VacuumBot(
                    self._session,
                    await self.ecovacs_api.get_request_auth(),
                    device,
                    self.country,
                    self.continent,
                    verify_ssl=self.verify_ssl
                )

                _LOGGER.debug("New vacbot found: " + device["name"])
                self.vacbots.append(vacbot)

        _LOGGER.debug("Hub initialized")

    @property
    def name(self):
        """ Return the name of the hub."""
        return "Deebot Hub"
