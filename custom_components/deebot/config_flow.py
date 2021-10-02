"""Config flow for Deebot integration."""
import logging
import random
import string
from typing import Any, Dict, List, Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientError
from deebotozmo.ecovacs_api import EcovacsAPI
from deebotozmo.models import Vacuum
from deebotozmo.util import md5
from homeassistant import config_entries
from homeassistant.const import (
    CONF_DEVICES,
    CONF_MODE,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import (
    BUMPER_CONFIGURATION,
    CONF_CLIENT_DEVICE_ID,
    CONF_CONTINENT,
    CONF_COUNTRY,
    CONF_MODE_BUMPER,
    CONF_MODE_CLOUD,
    DOMAIN,
)
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


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore
    """Handle a config flow for Deebot."""

    VERSION = 3
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}
        self._robot_list: List[Vacuum] = []
        self._mode: Optional[str] = None

    async def _async_retrieve_bots(self, domain_config: Dict[str, Any]) -> List[Vacuum]:
        ecovacs_api = EcovacsAPI(
            aiohttp_client.async_get_clientsession(self.hass),
            DEEBOT_API_DEVICEID,
            domain_config[CONF_USERNAME],
            md5(domain_config[CONF_PASSWORD]),
            continent=domain_config[CONF_CONTINENT],
            country=domain_config[CONF_COUNTRY],
            verify_ssl=domain_config.get(CONF_VERIFY_SSL, True),
        )

        await ecovacs_api.login()
        return await ecovacs_api.get_devices()

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            if len(user_input[CONF_COUNTRY]) != 2:
                errors[CONF_COUNTRY] = "invalid_country"

            if len(user_input[CONF_CONTINENT]) != 2:
                errors[CONF_CONTINENT] = "invalid_continent"

            try:
                info = await self._async_retrieve_bots(user_input)
                self._robot_list = info
            except ClientError:
                _LOGGER.debug("Cannot connect", exc_info=True)
                errors["base"] = "cannot_connect"
            except ValueError:
                _LOGGER.debug("Invalid auth", exc_info=True)
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.error("Unexcdepted exception", exc_info=True)
                errors["base"] = "unknown"

            if not errors:
                self._data.update(user_input)
                return await self.async_step_robots()

        if self.show_advanced_options and self._mode is None:
            return await self.async_step_user_advanced()

        return self.async_show_form(
            step_id="user", data_schema=USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_user_advanced(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle an advanced mode flow initialized by the user."""
        if user_input is not None:
            self._mode = user_input.get(CONF_MODE, CONF_MODE_CLOUD)
            if self._mode == CONF_MODE_BUMPER:
                config = {
                    **BUMPER_CONFIGURATION,
                    CONF_CLIENT_DEVICE_ID: get_bumper_device_id(self.hass),
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

        return self.async_show_form(step_id="user_advanced", data_schema=data_schema)

    async def async_step_robots(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the robots selection step."""

        errors = {}
        if user_input is not None:
            try:
                if len(user_input[CONF_DEVICES]) < 1:
                    errors["base"] = "select_robots"
                else:
                    self._data.update(user_input)
                    return self.async_create_entry(
                        title=self._data[CONF_USERNAME], data=self._data
                    )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.error("Unexpected exception", exc_info=True)
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        robot_list_dict = {
            e["name"]: e.get("nick", e["name"]) for e in self._robot_list
        }
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICES, default=list(robot_list_dict.keys())
                ): cv.multi_select(robot_list_dict)
            }
        )

        return self.async_show_form(
            step_id="robots", data_schema=options_schema, errors=errors
        )
