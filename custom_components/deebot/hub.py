"""Hub module."""
import asyncio
import logging
import random
import string
from typing import Any, List, Mapping

import aiohttp
from aiohttp import ClientError
from deebotozmo import Configuration, create_instances
from deebotozmo.mqtt_client import MqttClient
from deebotozmo.util import md5
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.const import (
    CONF_DEVICES,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client

from .const import CONF_CLIENT_DEVICE_ID, CONF_CONTINENT, CONF_COUNTRY

_LOGGER = logging.getLogger(__name__)


class DeebotHub:
    """Deebot Hub."""

    def __init__(self, hass: HomeAssistant, config: Mapping[str, Any]):
        self._hass_config: Mapping[str, Any] = config
        self._hass: HomeAssistant = hass
        self.vacuum_bots: List[VacuumBot] = []
        verify_ssl = config.get(CONF_VERIFY_SSL, True)
        self._session: aiohttp.ClientSession = aiohttp_client.async_get_clientsession(
            self._hass, verify_ssl=verify_ssl
        )

        device_id = config.get(CONF_CLIENT_DEVICE_ID)

        if not device_id:
            # Generate a random device ID on each bootup
            device_id = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(12)
            )

        deebot_config = Configuration(
            aiohttp_client.async_get_clientsession(self._hass, verify_ssl=verify_ssl),
            device_id=device_id,
            country=config.get(CONF_COUNTRY, "it").lower(),
            continent=config.get(CONF_CONTINENT, "eu").lower(),
            verify_ssl=config.get(CONF_VERIFY_SSL, True),
        )

        (authenticator, self._api_client) = create_instances(
            deebot_config,
            config.get(CONF_USERNAME, ""),
            md5(config.get(CONF_PASSWORD, "")),
        )

        self._mqtt: MqttClient = MqttClient(deebot_config, authenticator)

    async def async_setup(self) -> None:
        """Init hub."""
        try:
            if self._mqtt:
                self.disconnect()

            await self._mqtt.initialize()

            devices = await self._api_client.get_devices()

            # CREATE VACBOT FOR EACH DEVICE
            for device in devices:
                if device["name"] in self._hass_config.get(CONF_DEVICES, []):
                    vacbot = VacuumBot(self._session, device, self._api_client)

                    await self._mqtt.subscribe(vacbot)
                    _LOGGER.debug("New vacbot found: %s", device["name"])
                    self.vacuum_bots.append(vacbot)

            asyncio.create_task(self._check_status_task())

            _LOGGER.debug("Hub setup complete")
        except Exception as ex:
            msg = "Error during setup"
            _LOGGER.error(msg, exc_info=True)
            raise ConfigEntryNotReady(msg) from ex

    def disconnect(self) -> None:
        """Disconnect hub."""
        self._mqtt.disconnect()

    @property
    def name(self) -> str:
        """Return the name of the hub."""
        return "Deebot Hub"

    async def _check_status_task(self) -> None:
        while True:
            try:
                await asyncio.sleep(60)
                await self._check_status_function()
            except ClientError as ex:
                _LOGGER.warning(
                    "A client error occurred, probably the ecovacs servers are unstable: %s",
                    ex,
                )
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.error(ex, exc_info=True)

    async def _check_status_function(self) -> None:
        devices = await self._api_client.get_devices()
        for device in devices:
            bot: VacuumBot
            for bot in self.vacuum_bots:
                if device.did == bot.device_info.did:
                    bot.set_available(device.status == 1)
