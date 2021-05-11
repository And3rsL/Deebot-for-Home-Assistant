"""Config flow for Deebot integration."""
import logging
import random
import string

import voluptuous as vol
from deebotozmo import EcoVacsAPI

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_MODE, CONF_DEVICES
from .const import *

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

ROBOTS_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_LIVEMAP, default=False): bool,
        vol.Optional(CONF_SHOWCOLORROOMS, default=False): bool,
    }
)


def ConfigEntryRetriveRobots(domain_config: dict):

    ecovacs_api = EcoVacsAPI(
        DEEBOT_API_DEVICEID,
        domain_config.get(CONF_USERNAME),
        EcoVacsAPI.md5(domain_config.get(CONF_PASSWORD)),
        domain_config.get(CONF_COUNTRY),
        domain_config.get(CONF_CONTINENT),
        verify_ssl=domain_config.get(CONF_VERIFY_SSL, True)
    )

    return ecovacs_api.devices()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Deebot."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        self.data = {}
        self.robot_list = []
        self.mode = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            if len(user_input[CONF_COUNTRY]) != 2:
                errors[CONF_COUNTRY] = "invalid_country"

            if len(user_input[CONF_CONTINENT]) != 2:
                errors[CONF_CONTINENT] = "invalid_continent"

            try:
                info = await self.hass.async_add_executor_job(ConfigEntryRetriveRobots, user_input)
                self.robot_list = info
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
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
                return await self.async_step_user(user_input=BUMPER_CONFIGURATION)

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
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        robot_listDict = {e["name"]: e["nick"] for e in self.robot_list}
        options_schema = ROBOTS_DATA_SCHEMA.extend(
            {
                vol.Required(
                    CONF_DEVICES, default=list(robot_listDict.keys())
                ): cv.multi_select(robot_listDict)
            }
        )

        return self.async_show_form(
            step_id="robots", data_schema=options_schema, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
