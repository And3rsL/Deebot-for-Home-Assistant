from homeassistant.components.vacuum import (
    PLATFORM_SCHEMA,
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
    SUPPORT_BATTERY,
    SUPPORT_FAN_SPEED,
    SUPPORT_LOCATE,
    SUPPORT_PAUSE,
    SUPPORT_RETURN_HOME,
    SUPPORT_SEND_COMMAND,
    SUPPORT_START,
    SUPPORT_STATE,
    VacuumEntity,
)

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
CONF_DEVICEID = "deviceid"
CONF_LIVEMAP = "live_map"
CONF_SHOWCOLORROOMS = "show_color_rooms"
DEEBOT_DEVICES = f"{DOMAIN}_devices"
STATE_CODE_TO_STATE = {
    "STATE_IDLE": STATE_IDLE,
    "STATE_CLEANING": STATE_CLEANING,
    "STATE_RETURNING": STATE_RETURNING,
    "STATE_DOCKED": STATE_DOCKED,
    "STATE_ERROR": STATE_ERROR,
    "STATE_PAUSED": STATE_PAUSED,
}