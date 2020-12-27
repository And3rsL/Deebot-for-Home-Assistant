"""Support for Deebot Sensor."""
from typing import Optional

from deebotozmo import *
from homeassistant.const import (STATE_UNKNOWN)
from homeassistant.helpers.entity import Entity

from . import HUB as hub

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.vacuum import (
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
)

STATE_CODE_TO_STATE = {
    'STATE_IDLE': STATE_IDLE,
    'STATE_CLEANING': STATE_CLEANING,
    'STATE_RETURNING': STATE_RETURNING,
    'STATE_DOCKED': STATE_DOCKED,
    'STATE_ERROR': STATE_ERROR,
    'STATE_PAUSED': STATE_PAUSED,
}


def get_general(vacbot: VacBot):
    return [
        DeebotLastCleanImageSensor(vacbot, "last_clean_image"),
        DeebotWaterLevelSensor(vacbot, "water_level")
    ]


def get_components(vacbot: VacBot):
    return [
        DeebotComponentSensor(vacbot, COMPONENT_MAIN_BRUSH),
        DeebotComponentSensor(vacbot, COMPONENT_SIDE_BRUSH),
        DeebotComponentSensor(vacbot, COMPONENT_FILTER)
    ]


def get_stats(vacbot: VacBot):
    return [
        DeebotStatsSensor(vacbot, "stats_area"),
        DeebotStatsSensor(vacbot, "stats_time"),
        DeebotStatsSensor(vacbot, "stats_type")
    ]


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Deebot sensor."""
    hub.update()

    for vacbot in hub.vacbots:
        # General
        add_devices(get_general(vacbot), True)

        # Components
        add_devices(get_components(vacbot), True)

        # Stats
        add_devices(get_stats(vacbot), True)


class DeebotBaseSensor(Entity):
    """Deebot base sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""

        self._state = STATE_UNKNOWN
        self._vacbot = vacbot
        self._id = device_id

        if self._vacbot.vacuum.get("nick", None) is not None:
            self._vacbot_name = "{}".format(self._vacbot.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            self._vacbot_name = "{}".format(self._vacbot.vacuum["did"])

        self._name = self._vacbot_name + "_" + device_id

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def id(self):
        """Return the internal id"""
        return self._id


class DeebotLastCleanImageSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""
        super(DeebotLastCleanImageSensor, self).__init__(vacbot, device_id)

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        if self._vacbot.last_clean_image is not None:
            return self._vacbot.last_clean_image

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        return "mdi:image-search"


class DeebotWaterLevelSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""
        super(DeebotWaterLevelSensor, self).__init__(vacbot, device_id)

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""

        if self._vacbot.water_level is not None:
            return self._vacbot.water_level

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        return "mdi:water"


class DeebotComponentSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""
        super(DeebotComponentSensor, self).__init__(vacbot, device_id)

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

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        if self._id == COMPONENT_MAIN_BRUSH or self._id == COMPONENT_SIDE_BRUSH:
            return "mdi:broom"
        elif self._id == COMPONENT_FILTER:
            return "mdi:air-filter"


class DeebotStatsSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""
        super(DeebotStatsSensor, self).__init__(vacbot, device_id)

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

        if self._id == 'stats_area' and self._vacbot.stats_area is not None:
            return int(self._vacbot.stats_area)
        elif self._id == 'stats_time' and self._vacbot.stats_time is not None:
            return int(self._vacbot.stats_time / 60)
        elif self._id == 'stats_type':
            return self._vacbot.stats_type
        else:
            return STATE_UNKNOWN

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        if self._id == 'stats_area':
            return "mdi:floor-plan"
        elif self._id == 'stats_time':
            return "mdi:timer-outline"
        elif self._id == 'stats_type':
            return "mdi:cog"
