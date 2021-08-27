from deebotozmo.models import VacuumState
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

STARTUP_MESSAGE = f"""
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
CONF_BUMPER = "Bumper"
CONF_MODE_BUMPER = CONF_BUMPER
CONF_MODE_CLOUD = "Cloud (recommended)"
CONF_CLIENT_DEVICE_ID = "client_device_id"

# Bumper has no auth and serves the urls for all countries/continents
BUMPER_CONFIGURATION = {
    CONF_CONTINENT: "eu",
    CONF_COUNTRY: "it",
    CONF_PASSWORD: CONF_BUMPER,
    CONF_USERNAME: CONF_BUMPER,
    CONF_VERIFY_SSL: False  # required as bumper is using self signed certificates
}

DEEBOT_DEVICES = f"{DOMAIN}_devices"

VACUUMSTATE_TO_STATE = {
    VacuumState.STATE_IDLE: STATE_IDLE,
    VacuumState.STATE_CLEANING: STATE_CLEANING,
    VacuumState.STATE_RETURNING: STATE_RETURNING,
    VacuumState.STATE_DOCKED: STATE_DOCKED,
    VacuumState.STATE_ERROR: STATE_ERROR,
    VacuumState.STATE_PAUSED: STATE_PAUSED,
}

LAST_ERROR = "last_error"

EVENT_STATUS = "Status"
EVENT_ERROR = "Error"
EVENT_FAN_SPEED = "Fan speed"
EVENT_CLEAN_LOGS = "Clean logs"
EVENT_WATER = "Water"
EVENT_BATTERY = "Battery"
EVENT_STATS = "Stats"
EVENT_LIFE_SPAN = "Life spans"
EVENT_ROOMS = "Rooms"
EVENT_MAP = "Map"
