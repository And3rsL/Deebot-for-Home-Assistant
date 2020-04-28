"""Support for Deebot Vaccums."""
import asyncio
import logging
import async_timeout
import time
import random
import string
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from deebotozmo import *
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_HOMEASSISTANT_STOP

REQUIREMENTS = ['deebotozmo==1.2.9']

CONF_COUNTRY = "country"
CONF_CONTINENT = "continent"
CONF_DEVICEID = "deviceid"
DEEBOT_DEVICES = "deebot_devices"

# Generate a random device ID on each bootup
DEEBOT_API_DEVICEID = "".join(
    random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
)

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
    VacuumDevice,
)

_LOGGER = logging.getLogger(__name__)

SUPPORT_DEEBOT = (
    SUPPORT_BATTERY
    | SUPPORT_FAN_SPEED
    | SUPPORT_LOCATE
    | SUPPORT_PAUSE
    | SUPPORT_RETURN_HOME
    | SUPPORT_SEND_COMMAND
    | SUPPORT_START
    | SUPPORT_STATE
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_COUNTRY): vol.All(vol.Lower, cv.string),
        vol.Required(CONF_CONTINENT): vol.All(vol.Lower, cv.string),
        vol.Required(CONF_DEVICEID): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

STATE_CODE_TO_STATE = {
    'STATE_IDLE': STATE_IDLE,
    'STATE_CLEANING': STATE_CLEANING,
    'STATE_RETURNING': STATE_RETURNING,
    'STATE_DOCKED': STATE_DOCKED,
    'STATE_ERROR': STATE_ERROR,
    'STATE_PAUSED': STATE_PAUSED,
}

ATTR_COMPONENT_PREFIX = "component_"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Deebot vacuums."""
    vacuums = []

    if DEEBOT_DEVICES not in hass.data:
        hass.data[DEEBOT_DEVICES] = []

    # Setting up API credentials
    ecovacs_api = EcoVacsAPI(
        DEEBOT_API_DEVICEID,
        config.get(CONF_USERNAME),
        EcoVacsAPI.md5(config.get(CONF_PASSWORD)),
        config.get(CONF_COUNTRY),
        config.get(CONF_CONTINENT),
    )

    # GET DEVICES
    devices = ecovacs_api.devices()

    # CREATE VACBOT FOR EACH DEVICE
    for device in devices:
        if device['name'] == config.get(CONF_DEVICEID):
            vacbot = VacBot(
                ecovacs_api.uid,
                ecovacs_api.REALM,
                ecovacs_api.resource,
                ecovacs_api.user_access_token,
                device,
                config.get(CONF_CONTINENT).lower(),
                monitor=False,
            )
            hass.data[DEEBOT_DEVICES].append(vacbot)
            vacuums.append(DeebotVacuum(vacbot))
            async_add_entities(vacuums, True)

class DeebotVacuum(VacuumDevice):
    """Deebot Vacuums"""

    def __init__(self, device):
        """Initialize the Deebot Vacuum."""
        self.device = device
        self.device.connect_and_wait_until_ready()
        if self.device.vacuum.get("nick", None) is not None:
            self._name = "{}".format(self.device.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            self._name = "{}".format(self.device.vacuum["did"])

        self._fan_speed = None

        _LOGGER.debug("Vacuum initialized: %s", self.name)

    def on_fan_change(self, fan_speed):
        self._fan_speed = fan_speed
		
    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return True

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return self.device.vacuum.get("did", None)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def supported_features(self):
        """Flag vacuum cleaner robot features that are supported."""
        return SUPPORT_DEEBOT

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        try:
            return STATE_CODE_TO_STATE[self.device.vacuum_status]
        except KeyError:
            _LOGGER.error("STATE not supported: %s", self.device.vacuum_status)
            return None
        return self.device.vacuum_status

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.device.is_available

    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        await self.hass.async_add_executor_job(self.device.Charge)

    @property
    def battery_level(self):
        """Return the battery level of the vacuum cleaner."""
        if self.device.battery_status is not None:
            return self.device.battery_status

        return super().battery_level

    @property
    def fan_speed(self):
        """Return the fan speed of the vacuum cleaner."""
        return self.device.fan_speed

    async def async_set_fan_speed(self, fan_speed, **kwargs):
        await self.hass.async_add_executor_job(self.device.SetFanSpeed, fan_speed)

    @property
    def fan_speed_list(self):
        """Get the list of available fan speed steps of the vacuum cleaner."""
        return [FAN_SPEED_QUIET, FAN_SPEED_NORMAL, FAN_SPEED_MAX, FAN_SPEED_MAXPLUS]

    async def async_pause(self):
        """Pause the vacuum cleaner."""
        await self.hass.async_add_executor_job(self.device.CleanPause)

    async def async_start(self):
        """Start the vacuum cleaner."""
        await self.hass.async_add_executor_job(self.device.CleanResume)

    async def async_locate(self, **kwargs):
        """Locate the vacuum cleaner."""
        await self.hass.async_add_executor_job(self.device.PlaySound)

    async def async_send_command(self, command, params=None, **kwargs):
        """Send a command to a vacuum cleaner."""
        _LOGGER.debug("async_send_command %s (%s), %s", command, params, kwargs)
        
        if command == 'spot_area':
            return self.device.SpotArea(params['rooms'], params['cleanings'])

        if command == 'custom_area':
            return self.device.CustomArea(params['coordinates'], params['cleanings'])

        if command == 'set_water':
            return self.device.SetWaterLevel(params['amount'])

        await self.hass.async_add_executor_job(self.device.exc_command, command, params)

    async def async_update(self):
        """Fetch state from the device."""
        await self.hass.async_add_executor_job(self.device.request_all_statuses)

    @property
    def device_state_attributes(self):
        """Return the device-specific state attributes of this vacuum."""
        data = {}

        data['robot_status'] = STATE_CODE_TO_STATE[self.device.vacuum_status]
        data['water_level'] = self.device.water_level

        for key, val in self.device.components.items():
            attr_name = ATTR_COMPONENT_PREFIX + key
            data[attr_name] = int(val)

        i = 0
        for v in self.device.rooms:
            ke = str(i) + '_' + v['subtype']
            data[ke] = v['id']
            i = i+1
        
        data['last_clean_image'] = self.device.last_clean_image
        return data