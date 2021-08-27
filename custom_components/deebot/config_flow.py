"""Config flow for Deebot integration."""
import logging
import random
import string

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientError
from deebotozmo.ecovacs_api import EcovacsAPI
from deebotozmo.util import md5
from homeassistant import config_entries
from homeassistant.const import CONF_MODE, CONF_DEVICES
from homeassistant.helpers import aiohttp_client

from .const import *
from .helpers import get_bumper_device_id

_LOGGER = logging.getLogger(__name__)

# Generate a random device ID on each bootup
DEEBOT_API_DEVICEID = "".join(
    random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
)

USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_COUNTRY): str,
        vol.Required(CONF_CONTINENT): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Deebot."""

    VERSION = 3
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        self.data = {}
        self.robot_list = []
        self.mode = None

    async def async_retrieve_bots(self, domain_config: dict):
        ecovacs_api = EcovacsAPI(
            aiohttp_client.async_get_clientsession(self.hass),
            DEEBOT_API_DEVICEID,
            domain_config.get(CONF_USERNAME),
            md5(domain_config.get(CONF_PASSWORD)),
            continent=domain_config.get(CONF_CONTINENT),
            country=domain_config.get(CONF_COUNTRY),
            verify_ssl=domain_config.get(CONF_VERIFY_SSL, True)
        )

        await ecovacs_api.login()
        return await ecovacs_api.get_devices()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            if len(user_input[CONF_COUNTRY]) != 2:
                errors[CONF_COUNTRY] = "invalid_country"

            if len(user_input[CONF_CONTINENT]) != 2:
                errors[CONF_CONTINENT] = "invalid_continent"

            try:
                info = await self.async_retrieve_bots(user_input)
                self.robot_list = info
            except ClientError as e:
                _LOGGER.debug("Cannot connect", e, exc_info=True)
                errors["base"] = "cannot_connect"
            except ValueError as e:
                _LOGGER.debug("Invalid auth", e, exc_info=True)
                errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.error("Unexpected exception", e, exc_info=True)
                errors["base"] = "unknown"

            if not errors:
                self.data.update(user_input)
                return await self.async_step_robots()

        if self.show_advanced_options and self.mode is None:
            return await self.async_step_user_advanced()

        return self.async_show_form(
            step_id="user", data_schema=USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_user_advanced(self, user_input=None):
        """Handle an advanced mode flow initialized by the user."""
        if user_input is not None:
            self.mode = user_input.get(CONF_MODE, CONF_MODE_CLOUD)
            if self.mode == CONF_MODE_BUMPER:
                config = {
                    **BUMPER_CONFIGURATION,
                    CONF_CLIENT_DEVICE_ID: get_bumper_device_id(self.hass)
                }
                return await self.async_step_user(user_input=config)

            return await self.async_step_user()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_MODE, default=CONF_MODE_CLOUD): vol.In(
                    [CONF_MODE_CLOUD, CONF_MODE_BUMPER]
                )
            }
        )

        return self.async_show_form(
            step_id="user_advanced", data_schema=data_schema
        )

    async def async_step_robots(self, user_input=None):
        """Handle the robots selection step."""

        errors = {}
        if user_input is not None:
            try:
                if len(user_input[CONF_DEVICES]) < 1:
                    errors["base"] = "select_robots"
                else:
                    self.data.update(user_input)
                    return self.async_create_entry(
                        title=self.data[CONF_USERNAME], data=self.data
                    )
            except Exception as e:
                _LOGGER.error("Unexpected exception", e, exc_info=True)
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        robot_listDict = {e["name"]: e.get("nick", e["name"]) for e in self.robot_list}
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICES, default=list(robot_listDict.keys())
                ): cv.multi_select(robot_listDict)
            }
        )

        return self.async_show_form(
            step_id="robots", data_schema=options_schema, errors=errors
        )
