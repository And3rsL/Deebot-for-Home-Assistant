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
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from .const import *

_LOGGER = logging.getLogger(__name__)

# Generate a random device ID on each bootup
DEEBOT_API_DEVICEID = "".join(
    random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
)


class DeebotHub:
    """Deebot Hub"""

    def __init__(self, hass: HomeAssistant, config: Mapping[str, Any]):
        """Initialize the Deebot Vacuum."""

        self._config: Mapping[str, Any] = config
        self._hass: HomeAssistant = hass
        self._country: str = config.get(CONF_COUNTRY).lower()
        self._continent: str = config.get(CONF_CONTINENT).lower()
        self.vacuum_bots: [VacuumBot] = []
        self._verify_ssl = config.get(CONF_VERIFY_SSL, True)
        self._session: aiohttp.ClientSession = aiohttp_client.async_get_clientsession(self._hass,
                                                                                      verify_ssl=self._verify_ssl)

        self._ecovacs_api = EcovacsAPI(
            self._session,
            DEEBOT_API_DEVICEID,
            config.get(CONF_USERNAME),
            md5(config.get(CONF_PASSWORD)),
            self._country,
            self._continent,
            verify_ssl=self._verify_ssl
        )

    async def async_setup(self):
        try:
            await self._ecovacs_api.login()
            devices = await self._ecovacs_api.get_devices()

            # CREATE VACBOT FOR EACH DEVICE
            for device in devices:
                if device["name"] in self._config.get(CONF_DEVICES):
                    vacbot = VacuumBot(
                        self._session,
                        await self._ecovacs_api.get_request_auth(),
                        device,
                        self._country,
                        self._continent,
                        verify_ssl=self._verify_ssl
                    )

                    _LOGGER.debug("New vacbot found: " + device["name"])
                    self.vacuum_bots.append(vacbot)

            _LOGGER.debug("Hub setup complete")
        except Exception as err:
            # Todo better error handling
            raise ConfigEntryNotReady(
                f"Error during setup"
            ) from err

    @property
    def name(self):
        """ Return the name of the hub."""
        return "Deebot Hub"
