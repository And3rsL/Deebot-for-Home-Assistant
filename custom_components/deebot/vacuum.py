"""Support for Deebot Vaccums."""
import base64
import logging
from typing import Optional, Dict, Any, Union, List
from deebotozmo import (
    EcoVacsAPI,
    FAN_SPEED_QUIET,
    FAN_SPEED_NORMAL,
    FAN_SPEED_MAX,
    FAN_SPEED_MAXPLUS,
)
from homeassistant.util import slugify
from .const import *

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


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for vacbot in hub.vacbots:
        new_devices.append(DeebotVacuum(hass, vacbot, hub))

    if new_devices:
        async_add_devices(new_devices)


class DeebotVacuum(VacuumEntity):
    """Deebot Vacuums"""

    def __init__(self, hass, vacbot, hub):
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
        self._live_map_path = (
            hub.config.get(CONF_LIVEMAPPATH) + self._name + "_liveMap.png"
        )

        self.att_data = {}

        _LOGGER.debug("Vacuum initialized: %s", self.name)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        self.device.statusEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.device.batteryEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.device.roomEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.device.livemapEvents.subscribe(self.on_map_updated)
        self.device.fanspeedEvents.subscribe(self.on_fan_change)

    def on_fan_change(self, fan_speed):
        self._fan_speed = fan_speed

    def on_map_updated(self, map):
        try:
            if self._live_map != map:
                self._live_map = map
                with open(self._live_map_path, "wb") as fh:
                    fh.write(base64.decodebytes(map))
        except KeyError:
            _LOGGER.warning(
                "Can't access local folder: %s",
                self._live_map_path,
            )

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
        return SUPPORT_DEEBOT

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        if self.device.vacuum_status is not None and self.device.is_available == True:
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

        if command == "spot_area":
            await self.hass.async_add_executor_job(
                self.device.SpotArea, params["rooms"], params["cleanings"]
            )
            return

        if command == "custom_area":
            await self.hass.async_add_executor_job(
                self.device.CustomArea, params["coordinates"], params["cleanings"]
            )
            return

        if command == "set_water":
            await self.hass.async_add_executor_job(
                self.device.SetWaterLevel, params["amount"]
            )
            return

        if command == "relocate":
            await self.hass.async_add_executor_job(self.device.Relocate)
            return

        if command == "auto_clean":
            self.hass.async_add_executor_job(self.device.Clean, params["type"])
            return

        if command == "refresh_components":
            await self.hass.async_add_executor_job(self.device.refresh_components)
            return

        if command == "refresh_statuses":
            await self.hass.async_add_executor_job(self.device.refresh_statuses)
            return

        if command == "refresh_live_map":
            await self.hass.async_add_executor_job(self.device.refresh_liveMap)
            return

        if command == "save_live_map":
            if self._live_map != self.device.live_map:
                self._live_map = self.device.live_map
                with open(params["path"], "wb") as fh:
                    fh.write(base64.decodebytes(self.device.live_map))

        await self.hass.async_add_executor_job(self.device.exc_command, command, params)

    @property
    def device_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return device specific state attributes.

        Implemented by platform classes. Convention for attribute names
        is lowercase snake_case.
        """
        # Needed for custom vacuum-card (https://github.com/denysdovhan/vacuum-card)
        # Should find a better way without breaking everyone rooms script
        savedRooms = self.device.getSavedRooms()
        if savedRooms is not None:
            self.att_data = {}
            for r in savedRooms:
                # convert room name to snake_case to meet the convention
                room_name = "room_" + slugify(r["subtype"])
                room_values = self.att_data.get(room_name)
                if room_values is None:
                    self.att_data[room_name] = r["id"]
                elif isinstance(room_values, list):
                    room_values.append(r["id"])
                else:
                    # Convert from int to list
                    self.att_data[room_name] = [room_values, r["id"]]

        self.att_data["status"] = STATE_CODE_TO_STATE[self.device.vacuum_status]

        return self.att_data