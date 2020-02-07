"""Support for Ecovacs Ecovacs Vaccums."""
import asyncio
import logging
import async_timeout
import time
from deebotozmo import *

from homeassistant.components.vacuum import (
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

from . import ECOVACS_DEVICES

_LOGGER = logging.getLogger(__name__)

SUPPORT_ECOVACS = (
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

ATTR_ERROR = "error"
ATTR_COMPONENT_PREFIX = "component_"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Ecovacs vacuums."""
    vacuums = []

    for device in hass.data[ECOVACS_DEVICES]:
        vacuums.append(EcovacsVacuum(device))
    _LOGGER.debug("Adding Deebot Vacuums to Home Assistant: %s", vacuums)
	
    async_add_entities(vacuums, True)


class EcovacsVacuum(VacuumDevice):
    """Ecovacs Vacuums such as Deebot."""

    def __init__(self, device):
        """Initialize the Ecovacs Vacuum."""
        self.device = device
        self.device.connect_and_wait_until_ready()
        if self.device.vacuum.get("nick", None) is not None:
            self._name = "{}".format(self.device.vacuum["nick"])
        else:
            # In case there is no nickname defined, use the device id
            self._name = "{}".format(self.device.vacuum["did"])

        self._fan_speed = None
        self._error = None
        _LOGGER.debug("Vacuum initialized: %s", self.name)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        self.device.statusEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.device.batteryEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.device.lifespanEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.device.fanspeedEvents.subscribe(self.on_fan_change)
        self.device.errorEvents.subscribe(self.on_error)

    def on_error(self, error):
        """Handle an error event from the robot.

        This will not change the entity's state. If the error caused the state
        to change, that will come through as a separate on_status event
        """
        if error == "no_error":
            self._error = None
        else:
            self._error = error

        self.hass.bus.fire(
            "ecovacs_error", {"entity_id": self.entity_id, "error": error}
        )
        self.schedule_update_ha_state()
		
    def on_fan_change(self, fan_speed):
        self._fan_speed = fan_speed
        self.schedule_update_ha_state()
		
    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return False

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
        return SUPPORT_ECOVACS

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
        await self.hass.async_add_job(self.device.Charge)

    @property
    def battery_level(self):
        """Return the battery level of the vacuum cleaner."""
        if self.device.battery_status is not None:
            return self.device.battery_status

        return super().battery_level

    @property
    def fan_speed(self):
        """Return the fan speed of the vacuum cleaner."""
        return self._fan_speed

    async def async_set_fan_speed(self, fan_speed, **kwargs):
        await self.hass.async_add_job(self.device.SetFanSpeed, fan_speed)

    @property
    def fan_speed_list(self):
        """Get the list of available fan speed steps of the vacuum cleaner."""
        return [FAN_SPEED_QUIET, FAN_SPEED_NORMAL, FAN_SPEED_MAX, FAN_SPEED_MAXPLUS]

    async def async_pause(self):
        """Pause the vacuum cleaner."""
        await self.hass.async_add_job(self.device.CleanPause)

    async def async_start(self):
        """Start the vacuum cleaner."""
        await self.hass.async_add_job(self.device.CleanResume)

    async def async_locate(self, **kwargs):
        """Locate the vacuum cleaner."""
        await self.hass.async_add_job(self.device.PlaySound)

    async def async_send_command(self, command, params=None, **kwargs):
        """Send a command to a vacuum cleaner."""
        _LOGGER.debug("async_send_command %s (%s), %s", command, params, kwargs)
        await self.hass.async_add_job(self.device.exc_command, command, params)
        return True

    @property
    def device_state_attributes(self):
        """Return the device-specific state attributes of this vacuum."""
        data = {}
        data[ATTR_ERROR] = self._error

        for key, val in self.device.components.items():
            attr_name = ATTR_COMPONENT_PREFIX + key
            data[attr_name] = int(val)

        return data
