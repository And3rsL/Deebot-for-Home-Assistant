from homeassistant.components.vacuum import (
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_VERIFY_SSL

DOMAIN = "deebot"
INTEGRATION_VERSION = "main"
ISSUE_URL = "https://github.com/And3rsL/Deebot-for-Home-Assistant/issues"

STARTUP = f"""
-------------------------------------------------------------------
{DOMAIN}
Version: {INTEGRATION_VERSION}
This is a custom component
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

CONF_COUNTRY = "country"
CONF_CONTINENT = "continent"
DEEBOT_DEVICES = f"{DOMAIN}_devices"
STATE_CODE_TO_STATE = {
    "STATE_IDLE": STATE_IDLE,
    "STATE_CLEANING": STATE_CLEANING,
    "STATE_RETURNING": STATE_RETURNING,
    "STATE_DOCKED": STATE_DOCKED,
    "STATE_ERROR": STATE_ERROR,
    "STATE_PAUSED": STATE_PAUSED,
}

CONF_BUMPER = "Bumper"
CONF_MODE_BUMPER = CONF_BUMPER
CONF_MODE_CLOUD = "Cloud (recommended)"

# Bumper has no auth and serves the urls for all countries/continents
BUMPER_CONFIGURATION = {
    CONF_CONTINENT: "eu",
    CONF_COUNTRY: "it",
    CONF_PASSWORD: CONF_BUMPER,
    CONF_USERNAME: CONF_BUMPER,
    CONF_VERIFY_SSL: False  # required as bumper is using self signed certificates
}
