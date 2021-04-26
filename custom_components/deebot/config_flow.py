"""Config flow for Deebot integration."""
import logging
import voluptuous as vol
import random
import string
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from .const import DOMAIN
from .const import *
from deebotozmo import EcoVacsAPI, VacBot

_LOGGER = logging.getLogger(__name__)

# Generate a random device ID on each bootup
DEEBOT_API_DEVICEID = "".join(
    random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_COUNTRY): str,
        vol.Required(CONF_CONTINENT): str,
        vol.Optional(CONF_LIVEMAP, default=False): bool,
        vol.Optional(CONF_SHOWCOLORROOMS, default=False): bool,
    }
)


async def validate_input(hass: core.HomeAssistant, data: dict):
    """Validate the user input allows us to connect.
    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    if len(data[CONF_COUNTRY]) != 2:
        raise InvalidCountry

    if len(data[CONF_CONTINENT]) != 2:
        raise InvalidContinent

    return await hass.async_add_executor_job(ConfigEntryRetriveRobots, hass, data)


def ConfigEntryRetriveRobots(hass: core.HomeAssistant, domain_config):
    ecovacs_api = EcoVacsAPI(
        DEEBOT_API_DEVICEID,
        domain_config.get(CONF_USERNAME),
        EcoVacsAPI.md5(domain_config.get(CONF_PASSWORD)),
        domain_config.get(CONF_COUNTRY),
        domain_config.get(CONF_CONTINENT),
    )

    return ecovacs_api.devices()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Deebot."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        self.data = {}
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                self.robot_list = info
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidCountry:
                errors[CONF_COUNTRY] = "invalid_country"
            except InvalidContinent:
                errors[CONF_CONTINENT] = "invalid_continent"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if not errors:
                self.data = user_input

                robot_listDict = {e["name"]: e["nick"] for e in self.robot_list}
                options_schema = vol.Schema(
                    {
                        vol.Required(
                            CONF_DEVICEID, default=list(robot_listDict.keys())
                        ): cv.multi_select(robot_listDict)
                    }
                )

                return self.async_show_form(
                    step_id="robots", data_schema=options_schema, errors=errors
                )

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_robots(self, user_input=None):
        """Handle the robots selection step."""

        errors = {}
        if user_input is not None:
            try:
                if len(user_input[CONF_DEVICEID]) < 1:
                    errors["base"] = "select_robots"
                else:
                    self.data[CONF_DEVICEID] = user_input
                    return self.async_create_entry(
                        title=self.data[CONF_USERNAME], data=self.data
                    )
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        robot_listDict = {e["name"]: e["nick"] for e in self.robot_list}
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICEID, default=list(robot_listDict.keys())
                ): cv.multi_select(robot_listDict)
            }
        )

        return self.async_show_form(
            step_id="robots", data_schema=options_schema, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidCountry(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""


class InvalidContinent(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""