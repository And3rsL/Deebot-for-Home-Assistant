"""Support for Deebot Vaccums."""
import logging
from typing import Optional, Dict, Any

from deebotozmo.commands import *
from deebotozmo.constants import FAN_SPEED_QUIET, FAN_SPEED_NORMAL, FAN_SPEED_MAX, FAN_SPEED_MAXPLUS
from deebotozmo.events import EventListener, BatteryEvent, RoomsEvent, FanSpeedEvent, StatusEvent
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.components.vacuum import SUPPORT_BATTERY, SUPPORT_FAN_SPEED, SUPPORT_LOCATE, SUPPORT_PAUSE, \
    SUPPORT_RETURN_HOME, SUPPORT_SEND_COMMAND, SUPPORT_START, SUPPORT_STATE, VacuumEntity
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from .const import *
from .helpers import get_device_info

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


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for vacbot in hub.vacbots:
        new_devices.append(DeebotVacuum(hass, vacbot))

    if new_devices:
        async_add_devices(new_devices)


def _unsubscribe_listeners(listeners: [EventListener]):
    for listener in listeners:
        listener.unsubscribe()


class DeebotVacuum(VacuumEntity):
    """Deebot Vacuums"""

    def __init__(self, hass: HomeAssistant, vacuum_bot: VacuumBot):
        """Initialize the Deebot Vacuum."""
        self._hass: HomeAssistant = hass
        self._device: VacuumBot = vacuum_bot

        if self._device.vacuum.nick is not None:
            self._name: str = self._device.vacuum.nick
        else:
            # In case there is no nickname defined, use the device id
            self._name = self._device.vacuum.did

        self._battery: Optional[int] = None
        self._fan_speed = None
        self._available = False
        self._state = None

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""

        async def on_battery(event: BatteryEvent):
            self._battery = event.value
            self.async_write_ha_state()

        async def on_rooms(event: RoomsEvent):
            self.async_write_ha_state()

        async def on_fan_speed(event: FanSpeedEvent):
            self._fan_speed = event.speed
            self.async_write_ha_state()

        async def on_status(event: StatusEvent):
            self._available = event.available
            self._state = event.state

        listeners = [
            self._device.statusEvents.subscribe(on_status),
            self._device.batteryEvents.subscribe(on_battery),
            self._device.map.roomsEvents.subscribe(on_rooms),
            self._device.fanSpeedEvents.subscribe(on_fan_speed)
        ]
        self.async_on_remove(lambda: _unsubscribe_listeners(listeners))

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return False

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return self._device.vacuum.did

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
        if self._state is not None and self.available:
            return STATE_CODE_TO_STATE[self._state]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        await self._device.execute_command(Charge())

    @property
    def battery_level(self):
        """Return the battery level of the vacuum cleaner."""
        if self._battery is not None:
            return self._battery

        return super().battery_level

    @property
    def fan_speed(self):
        """Return the fan speed of the vacuum cleaner."""
        return self._fan_speed

    async def async_set_fan_speed(self, fan_speed: str, **kwargs):
        await self._device.execute_command(SetFanSpeed(fan_speed))

    @property
    def fan_speed_list(self):
        """Get the list of available fan speed steps of the vacuum cleaner."""
        return [FAN_SPEED_QUIET, FAN_SPEED_NORMAL, FAN_SPEED_MAX, FAN_SPEED_MAXPLUS]

    async def async_stop(self, **kwargs):
        """Stop the vacuum cleaner."""
        await self._device.execute_command(CleanStop())

    async def async_pause(self):
        """Pause the vacuum cleaner."""
        await self._device.execute_command(CleanPause())

    async def async_start(self):
        """Start the vacuum cleaner."""
        await self._device.execute_command(CleanStart())

    async def async_locate(self, **kwargs):
        """Locate the vacuum cleaner."""
        await self._device.execute_command(PlaySound())

    async def async_send_command(self, command, params=None, **kwargs):
        """Send a command to a vacuum cleaner."""
        _LOGGER.debug("async_send_command %s (%s), %s", command, params, kwargs)

        if command == "spot_area":
            await self._device.execute_command(CleanSpotArea(area=params["rooms"], cleanings=params["cleanings"]))
        elif command == "custom_area":
            await self._device.execute_command(CleanCustomArea(
                map_position=params["coordinates"], cleanings=params["cleanings"]))
        elif command == "set_water":
            await self._device.execute_command(SetWaterLevel(params["amount"]))
        elif command == "relocate":
            await self._device.execute_command(Relocate())
        elif command == "auto_clean":
            await self._device.execute_command(CleanStart(params["type"]))
        # todo really required?
        # if command == "refresh_components":
        #     await self.hass.async_add_executor_job(self.device.refresh_components)
        #     return
        #
        # if command == "refresh_statuses":
        #     await self.hass.async_add_executor_job(self.device.refresh_statuses)
        #     return
        #
        # if command == "refresh_live_map":
        #     await self.hass.async_add_executor_job(self.device.refresh_liveMap)
        #     return
        else:
            await self._device.execute_command(Command(command, params))

    @property
    def device_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return device specific state attributes.

        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        # Needed for custom vacuum-card (https://github.com/denysdovhan/vacuum-card)
        # Should find a better way without breaking everyone rooms script
        rooms = self._device.map.rooms
        if rooms is not None:
            self.att_data = {}
            for r in rooms:
                # convert room name to snake_case to meet the convention
                room_name = "room_" + slugify(r.subtype)
                room_values = self.att_data.get(room_name)
                if room_values is None:
                    self.att_data[room_name] = r.id
                elif isinstance(room_values, list):
                    room_values.append(r.id)
                else:
                    # Convert from int to list
                    self.att_data[room_name] = [room_values, r.id]

        if self._device.vacuum_status:
            self.att_data["status"] = STATE_CODE_TO_STATE[self._device.vacuum_status]

        return self.att_data

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return get_device_info(self._device)
