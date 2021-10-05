"""Support for Deebot Vaccums."""
import dataclasses
import logging
from typing import Any, Dict, List, Mapping, Optional

import voluptuous as vol
from deebotozmo.commands import (
    Charge,
    Clean,
    FanSpeedLevel,
    PlaySound,
    SetFanSpeed,
    SetRelocationState,
    SetWaterInfo,
)
from deebotozmo.commands.clean import CleanAction, CleanArea, CleanMode
from deebotozmo.commands.custom import CustomCommand
from deebotozmo.event_emitter import EventListener
from deebotozmo.events import (
    BatteryEvent,
    CustomCommandEvent,
    ErrorEvent,
    FanSpeedEvent,
    RoomsEvent,
    StatusEvent,
)
from deebotozmo.models import Room, VacuumState
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.components.vacuum import (
    SUPPORT_BATTERY,
    SUPPORT_FAN_SPEED,
    SUPPORT_LOCATE,
    SUPPORT_MAP,
    SUPPORT_PAUSE,
    SUPPORT_RETURN_HOME,
    SUPPORT_SEND_COMMAND,
    SUPPORT_START,
    SUPPORT_STATE,
    SUPPORT_STOP,
    StateVacuumEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import slugify

from .const import (
    DOMAIN,
    EVENT_BATTERY,
    EVENT_CLEAN_LOGS,
    EVENT_CUSTOM_COMMAND,
    EVENT_ERROR,
    EVENT_FAN_SPEED,
    EVENT_LIFE_SPAN,
    EVENT_MAP,
    EVENT_ROOMS,
    EVENT_STATS,
    EVENT_STATUS,
    EVENT_WATER,
    LAST_ERROR,
    VACUUMSTATE_TO_STATE,
)
from .helpers import get_device_info
from .hub import DeebotHub

_LOGGER = logging.getLogger(__name__)

SUPPORT_DEEBOT: int = (
    SUPPORT_PAUSE
    | SUPPORT_STOP
    | SUPPORT_RETURN_HOME
    | SUPPORT_FAN_SPEED
    | SUPPORT_BATTERY
    | SUPPORT_SEND_COMMAND
    | SUPPORT_LOCATE
    | SUPPORT_MAP
    | SUPPORT_STATE
    | SUPPORT_START
)

# Must be kept in sync with services.yaml
SERVICE_REFRESH = "refresh"
SERVICE_REFRESH_PART = "part"
SERVICE_REFRESH_SCHEMA = {
    vol.Required(SERVICE_REFRESH_PART): vol.In(
        [
            EVENT_STATUS,
            EVENT_ERROR,
            EVENT_FAN_SPEED,
            EVENT_CLEAN_LOGS,
            EVENT_WATER,
            EVENT_BATTERY,
            EVENT_STATS,
            EVENT_LIFE_SPAN,
            EVENT_ROOMS,
            EVENT_MAP,
        ]
    )
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub: DeebotHub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for vacbot in hub.vacuum_bots:
        new_devices.append(DeebotVacuum(hass, vacbot))

    if new_devices:
        async_add_entities(new_devices)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_REFRESH,
        SERVICE_REFRESH_SCHEMA,
        "_service_refresh",
    )


def _unsubscribe_listeners(listeners: List[EventListener]) -> None:
    for listener in listeners:
        listener.unsubscribe()


class DeebotVacuum(StateVacuumEntity):  # type: ignore
    """Deebot Vacuum."""

    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, vacuum_bot: VacuumBot):
        """Initialize the Deebot Vacuum."""
        self._hass: HomeAssistant = hass
        self._device: VacuumBot = vacuum_bot

        if self._device.vacuum.nick is not None:
            name: str = self._device.vacuum.nick
        else:
            # In case there is no nickname defined, use the device id
            name = self._device.vacuum.did

        self._battery: Optional[int] = None
        self._fan_speed: Optional[str] = None
        self._state: Optional[VacuumState] = None
        self._rooms: List[Room] = []
        self._last_error: Optional[ErrorEvent] = None

        self._attr_name = name
        self._attr_unique_id = self._device.vacuum.did

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_battery(event: BatteryEvent) -> None:
            self._battery = event.value
            self.async_write_ha_state()

        async def on_rooms(event: RoomsEvent) -> None:
            self._rooms = event.rooms
            self.async_write_ha_state()

        async def on_fan_speed(event: FanSpeedEvent) -> None:
            self._fan_speed = event.speed
            self.async_write_ha_state()

        async def on_status(event: StatusEvent) -> None:
            self._attr_available = event.available
            self._state = event.state
            self.async_write_ha_state()

        async def on_error(event: ErrorEvent) -> None:
            self._last_error = event
            self.async_write_ha_state()

        async def on_custom_command(event: CustomCommandEvent) -> None:
            self.hass.bus.fire(EVENT_CUSTOM_COMMAND, dataclasses.asdict(event))

        listeners: List[EventListener] = [
            self._device.events.status.subscribe(on_status),
            self._device.events.battery.subscribe(on_battery),
            self._device.events.rooms.subscribe(on_rooms),
            self._device.events.fan_speed.subscribe(on_fan_speed),
            self._device.events.error.subscribe(on_error),
            self._device.events.custom_command.subscribe(on_custom_command),
        ]
        self.async_on_remove(lambda: _unsubscribe_listeners(listeners))

    @property
    def supported_features(self) -> int:
        """Flag vacuum cleaner robot features that are supported."""
        return SUPPORT_DEEBOT

    @property
    def state(self) -> StateType:
        """Return the state of the vacuum cleaner."""
        if self._state is not None and self.available:
            return VACUUMSTATE_TO_STATE[self._state]

    @property
    def battery_level(self) -> Optional[int]:
        """Return the battery level of the vacuum cleaner."""
        return self._battery

    @property
    def fan_speed(self) -> Optional[str]:
        """Return the fan speed of the vacuum cleaner."""
        return self._fan_speed

    @property
    def fan_speed_list(self) -> List[str]:
        """Get the list of available fan speed steps of the vacuum cleaner."""
        return [level.display_name for level in FanSpeedLevel]

    @property
    def extra_state_attributes(self) -> Optional[Mapping[str, Any]]:
        """Return entity specific state attributes.

        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        attributes: Dict[str, Any] = {}
        for room in self._rooms:
            # convert room name to snake_case to meet the convention
            room_name = "room_" + slugify(room.subtype)
            room_values = attributes.get(room_name)
            if room_values is None:
                attributes[room_name] = room.id
            elif isinstance(room_values, list):
                room_values.append(room.id)
            else:
                # Convert from int to list
                attributes[room_name] = [room_values, room.id]

        if self._last_error:
            attributes[
                LAST_ERROR
            ] = f"{self._last_error.description} ({self._last_error.code})"

        return attributes

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return get_device_info(self._device)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set fan speed."""
        await self._device.execute_command(SetFanSpeed(fan_speed))

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Set the vacuum cleaner to return to the dock."""
        await self._device.execute_command(Charge())

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the vacuum cleaner."""
        await self._device.execute_command(Clean(CleanAction.STOP))

    async def async_pause(self) -> None:
        """Pause the vacuum cleaner."""
        await self._device.execute_command(Clean(CleanAction.PAUSE))

    async def async_start(self) -> None:
        """Start the vacuum cleaner."""
        await self._device.execute_command(Clean(CleanAction.START))

    async def async_locate(self, **kwargs: Any) -> None:
        """Locate the vacuum cleaner."""
        await self._device.execute_command(PlaySound())

    async def async_send_command(
        self, command: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        """Send a command to a vacuum cleaner."""
        _LOGGER.debug("async_send_command %s with %s", command, params)

        if command in ["relocate", SetRelocationState.name]:
            await self._device.execute_command(SetRelocationState())
        elif command == "auto_clean":
            clean_type = params.get("type", "auto") if params else "auto"
            if clean_type == "auto":
                _LOGGER.warning('DEPRECATED! Please use "vacuum.start" instead.')
                await self.async_start()
        elif command in ["spot_area", "custom_area", "set_water"]:
            if params is None:
                raise RuntimeError("Params are required!")

            if command in "spot_area":
                await self._device.execute_command(
                    CleanArea(
                        mode=CleanMode.SPOT_AREA,
                        area=str(params["rooms"]),
                        cleanings=params.get("cleanings", 1),
                    )
                )
            elif command == "custom_area":
                await self._device.execute_command(
                    CleanArea(
                        mode=CleanMode.CUSTOM_AREA,
                        area=str(params["coordinates"]),
                        cleanings=params.get("cleanings", 1),
                    )
                )
            elif command == "set_water":
                await self._device.execute_command(SetWaterInfo(params["amount"]))
        else:
            await self._device.execute_command(CustomCommand(command, params))

    async def _service_refresh(self, part: str) -> None:
        """Service to manually refresh."""
        _LOGGER.debug("Manually refresh %s", part)
        if part == EVENT_STATUS:
            self._device.events.status.request_refresh()
        elif part == EVENT_ERROR:
            self._device.events.error.request_refresh()
        elif part == EVENT_FAN_SPEED:
            self._device.events.fan_speed.request_refresh()
        elif part == EVENT_CLEAN_LOGS:
            self._device.events.clean_logs.request_refresh()
        elif part == EVENT_WATER:
            self._device.events.water_info.request_refresh()
        elif part == EVENT_BATTERY:
            self._device.events.battery.request_refresh()
        elif part == EVENT_STATS:
            self._device.events.stats.request_refresh()
        elif part == EVENT_LIFE_SPAN:
            self._device.events.lifespan.request_refresh()
        elif part == EVENT_ROOMS:
            self._device.events.rooms.request_refresh()
        elif part == EVENT_MAP:
            self._device.events.map.request_refresh()
        else:
            _LOGGER.warning('Service "refresh" called with unknown part: %s', part)
