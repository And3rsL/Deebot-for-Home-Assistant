"""Support for Deebot Sensor."""
import asyncio
import logging
import async_timeout
import time
import random
import string
import voluptuous as vol
from homeassistant.helpers.entity import Entity
from homeassistant.const import (STATE_UNKNOWN)
from deebotozmo import *
import base64
from . import HUB as hub
 
_LOGGER = logging.getLogger(__name__)

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

STATE_CODE_TO_STATE = {
    'STATE_IDLE': STATE_IDLE,
    'STATE_CLEANING': STATE_CLEANING,
    'STATE_RETURNING': STATE_RETURNING,
    'STATE_DOCKED': STATE_DOCKED,
    'STATE_ERROR': STATE_ERROR,
    'STATE_PAUSED': STATE_PAUSED,
}

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Deebot sensor."""
    hub.update()

    for vacbot in hub.vacbots:
        # General
        add_devices([DeebotVacStatusSensor(vacbot, "robot_status")], True)
        add_devices([DeebotLastCleanImageSensor(vacbot, "last_clean_image")], True)
        add_devices([DeebotWaterLevelSensor(vacbot, "water_level")], True)

        # Components
        add_devices([DeebotComponentSensor(vacbot, "brush")], True)
        add_devices([DeebotComponentSensor(vacbot, "sideBrush")], True)
        add_devices([DeebotComponentSensor(vacbot, "heap")], True)

        # Stats
        add_devices([DeebotStatsSensor(vacbot, "stats_area")], True)
        add_devices([DeebotStatsSensor(vacbot, "stats_time")], True)
        add_devices([DeebotStatsSensor(vacbot, "stats_type")], True)

        # Rooms
        if vacbot.getSavedRooms() is not None:
            for v in vacbot.getSavedRooms():
                _LOGGER.debug("New room type found: " + v['subtype'])
                add_devices([DeebotRoomSensor(vacbot, v['subtype'])], True)
        else:
            _LOGGER.warning("No rooms found")

class DeebotVacStatusSensor(Entity):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = device_id
        
        if self._vacbot.vacuum.get("nick", None) is not None:
            vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = vacbot_name + "_status"

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        if self._vacbot.vacuum_status is not None:
            return STATE_CODE_TO_STATE[self._vacbot.vacuum_status]

class DeebotLastCleanImageSensor(Entity):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = vacbot_name + "_last_clean_image"

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        if self._vacbot.last_clean_image is not None:
            return self._vacbot.last_clean_image

class DeebotWaterLevelSensor(Entity):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = vacbot_name + "_water_level"

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""

        if self._vacbot.water_level is not None:
            return self._vacbot.water_level

class DeebotComponentSensor(Entity):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = vacbot_name + "_" + device_id

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return '%'

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""

        for key, val in self._vacbot.components.items():
            if key == self._id:
                return int(val)

class DeebotStatsSensor(Entity):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = vacbot_name + "_" + device_id

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._id == 'stats_area':
            return "mq"
        elif self._id == 'stats_time':
            return "min"

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        
        if self._id == 'stats_area':
            return int(self._vacbot.stats_area)
        elif self._id == 'stats_time':
            return int(self._vacbot.stats_time/60)
        elif self._id == 'stats_type':
            return self._vacbot.stats_type
        else:
            return STATE_UNKNOWN

class DeebotRoomSensor(Entity):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = vacbot_name + "_" + device_id

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        room = None

        for v in self._vacbot.getSavedRooms():
            if v['subtype'] == self._id:
                if room is None:
                    room = v['id']
                else:
                    room = room + "," + v['id']

        return room