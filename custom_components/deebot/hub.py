import logging
import random
import string
from typing import Any, Mapping, Optional

import aiohttp
from deebotozmo.ecovacs_api import EcovacsAPI
from deebotozmo.ecovacs_mqtt import EcovacsMqtt
from deebotozmo.util import md5
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.const import CONF_DEVICES
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client

from .const import *

_LOGGER = logging.getLogger(__name__)


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

        if config.get(CONF_USERNAME) == CONF_BUMPER:
            try:
                location_name = hass.config.location_name.strip().replace(' ', '_')
            except:
                location_name = ""
            device_id = f"Deebot-4-HA_{location_name}"
        else:
            # Generate a random device ID on each bootup
            device_id = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(12)
            )

        self._mqtt: Optional[EcovacsMqtt] = None
        self._ecovacs_api = EcovacsAPI(
            self._session,
            device_id,
            config.get(CONF_USERNAME),
            md5(config.get(CONF_PASSWORD)),
            continent=self._continent,
            country=self._country,
            verify_ssl=self._verify_ssl
        )

    async def async_setup(self):
        try:
            await self._ecovacs_api.login()
            auth = await self._ecovacs_api.get_request_auth()

            self._mqtt = EcovacsMqtt(auth, continent=self._continent)

            devices = await self._ecovacs_api.get_devices()

            # CREATE VACBOT FOR EACH DEVICE
            for device in devices:
                if device["name"] in self._config.get(CONF_DEVICES):
                    vacbot = VacuumBot(
                        self._session,
                        auth,
                        device,
                        continent=self._continent,
                        country=self._country,
                        verify_ssl=self._verify_ssl
                    )

                    await self._mqtt.subscribe(vacbot)
                    _LOGGER.debug("New vacbot found: " + device["name"])
                    self.vacuum_bots.append(vacbot)

            _LOGGER.debug("Hub setup complete")
        except Exception as err:
            # Todo better error handling
            raise ConfigEntryNotReady(
                f"Error during setup"
            ) from err

    def disconnect(self) -> None:
        self._mqtt.disconnect()

    @property
    def name(self):
        """ Return the name of the hub."""
        return "Deebot Hub"
