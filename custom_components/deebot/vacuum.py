"""Support for Deebot Vaccums."""
import base64
from typing import Optional, Dict, Any, Union, List

from deebotozmo import *
from homeassistant.util import slugify

from . import HUB as hub

CONF_COUNTRY = "country"
CONF_CONTINENT = "continent"
CONF_DEVICEID = "deviceid"
CONF_LIVEMAPPATH = "livemappath"
CONF_LIVEMAP = "live_map"
CONF_SHOWCOLORROOMS = "show_color_rooms"
DEEBOT_DEVICES = "deebot_devices"

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

STATE_CODE_TO_STATE = {
    'STATE_IDLE': STATE_IDLE,
    'STATE_CLEANING': STATE_CLEANING,
    'STATE_RETURNING': STATE_RETURNING,
    'STATE_DOCKED': STATE_DOCKED,
    'STATE_ERROR': STATE_ERROR,
    'STATE_PAUSED': STATE_PAUSED,
}

ATTR_COMPONENT_PREFIX = "component_"

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Deebot vacuums."""
    if DEEBOT_DEVICES not in hass.data:
        hass.data[DEEBOT_DEVICES] = []

    for vacbot in hub.vacbots:
        vacuum = DeebotVacuum(hass, vacbot)
        add_devices([vacuum])

class DeebotVacuum(VacuumEntity):
    """Deebot Vacuums"""

    def __init__(self, hass, vacbot):
        """Initialize the Deebot Vacuum."""
        self._hass = hass

        self.device = vacbot

        if self.device.vacuum.get("nick", None) is not None:
            self._name = "{}".format(self.device.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            self._name = "{}".format(self.device.vacuum["did"])

        self._fan_speed = None
        self._live_map = None
        self._live_map_path = hub.config.get(CONF_LIVEMAPPATH) + self._name + '_liveMap.png'

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
        if self.device.vacuum_status is not None:
            return STATE_CODE_TO_STATE[self.device.vacuum_status]

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
            await self.hass.async_add_executor_job(self.device.SpotArea, params['rooms'], params['cleanings'])
            return

        if command == 'custom_area':
            await self.hass.async_add_executor_job(self.device.CustomArea, params['coordinates'], params['cleanings'])
            return

        if command == 'set_water':
            await self.hass.async_add_executor_job(self.device.SetWaterLevel, params['amount'])
            return

        if command == 'auto_clean':
            self.hass.async_add_executor_job(self.device.Clean, params['type'])
            return

        if command == 'refresh_components':
            await self.hass.async_add_executor_job(self.device.refresh_components)
            return

        if command == 'refresh_statuses':
            await self.hass.async_add_executor_job(self.device.refresh_statuses)
            return

        if command == 'refresh_live_map':
            await self.hass.async_add_executor_job(self.device.refresh_liveMap)
            return

        if command == 'save_live_map':
            if(self._live_map != self.device.live_map):
                self._live_map = self.device.live_map
                with open(params['path'], "wb") as fh:
                    fh.write(base64.decodebytes(self.device.live_map))

        await self.hass.async_add_executor_job(self.device.exc_command, command, params)

    async def async_update(self):
        """Fetch state from the device."""
        await self.hass.async_add_executor_job(self.device.request_all_statuses)

        try:
            if(self._live_map != self.device.live_map):
                self._live_map = self.device.live_map
                with open(self._live_map_path, "wb") as fh:
                    fh.write(base64.decodebytes(self.device.live_map))
        except KeyError:
            _LOGGER.warning("Can't access local folder: %s", self._live_map_path)

    @property
    def device_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return device specific state attributes.

        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        if self.device.getSavedRooms() is not None:
            rooms: Dict[str, Union[int, List[int]]] = {}
            for r in self.device.getSavedRooms():
                # convert room name to snake_case to meet the convention
                room_name = "room_" + slugify(r["subtype"])
                room_values = rooms.get(room_name)
                if room_values is None:
                    rooms[room_name] = r["id"]
                elif isinstance(room_values, list):
                    room_values.append(r["id"])
                else:
                    # Convert from int to list
                    rooms[room_name] = [room_values, r["id"]]

            return rooms

        return None
