import asyncio
import logging
import random
import string
from typing import Any, Mapping, Optional

import aiohttp
from aiohttp import ClientError
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

        device_id = config.get(CONF_CLIENT_DEVICE_ID)

        if not device_id:
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

            self._mqtt = EcovacsMqtt(auth, continent=self._continent, country=self._country)

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

            asyncio.create_task(self._check_status_task())

            _LOGGER.debug("Hub setup complete")
        except Exception as e:
            msg = "Error during setup"
            _LOGGER.error(msg, e, exc_info=True)
            raise ConfigEntryNotReady(msg) from e

    def disconnect(self) -> None:
        self._mqtt.disconnect()

    @property
    def name(self):
        """ Return the name of the hub."""
        return "Deebot Hub"

    async def _check_status_task(self):
        while True:
            try:
                await asyncio.sleep(60)
                await self._check_status_function()
            except ClientError as e:
                _LOGGER.warning(f"A client error occurred, probably the ecovacs servers are unstable: {e}")
            except Exception as e:
                _LOGGER.error(f"Unknown exception occurred: {e}")

    async def _check_status_function(self):
        devices = await self._ecovacs_api.get_devices()
        for device in devices:
            bot: VacuumBot
            for bot in self.vacuum_bots:
                if device.did == bot.vacuum.did:
                    bot.set_available(True if device.status == 1 else False)
