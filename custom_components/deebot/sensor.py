"""Support for Deebot Sensor."""
import logging
from typing import Optional, Dict, Any

from deebotozmo import (
    COMPONENT_FILTER,
    COMPONENT_SIDE_BRUSH,
    COMPONENT_MAIN_BRUSH, EventListener,
)
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .helpers import get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for vacbot in hub.vacbots:
        # General
        new_devices.append(DeebotLastCleanImageSensor(vacbot, "last_clean_image"))
        new_devices.append(DeebotWaterLevelSensor(vacbot, "water_level"))

        # Components
        new_devices.append(DeebotComponentSensor(vacbot, COMPONENT_MAIN_BRUSH))
        new_devices.append(DeebotComponentSensor(vacbot, COMPONENT_SIDE_BRUSH))
        new_devices.append(DeebotComponentSensor(vacbot, COMPONENT_FILTER))

        # Stats
        new_devices.append(DeebotStatsSensor(vacbot, "stats_area"))
        new_devices.append(DeebotStatsSensor(vacbot, "stats_time"))
        new_devices.append(DeebotStatsSensor(vacbot, "stats_type"))

    if new_devices:
        async_add_devices(new_devices)


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
    def unique_id(self) -> str:
        """Return an unique ID."""
        return self._vacbot.vacuum.get("did", None) + "_" + self._id

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return True

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return get_device_info(self._vacbot)


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

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        listener: EventListener = self._vacbot.cleanLogsEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.async_on_remove(listener.unsubscribe)


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

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        listener: EventListener = self._vacbot.waterEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.async_on_remove(listener.unsubscribe)


class DeebotComponentSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""
        super(DeebotComponentSensor, self).__init__(vacbot, device_id)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "%"

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

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        listener: EventListener = self._vacbot.lifespanEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.async_on_remove(listener.unsubscribe)


class DeebotStatsSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    def __init__(self, vacbot, device_id):
        """Initialize the Sensor."""
        super(DeebotStatsSensor, self).__init__(vacbot, device_id)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._id == "stats_area":
            return "mq"
        elif self._id == "stats_time":
            return "min"

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""

        if self._id == "stats_area" and self._vacbot.stats_area is not None:
            return int(self._vacbot.stats_area)
        elif self._id == "stats_time" and self._vacbot.stats_time is not None:
            return int(self._vacbot.stats_time / 60)
        elif self._id == "stats_type":
            return self._vacbot.stats_type
        else:
            return STATE_UNKNOWN

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        if self._id == "stats_area":
            return "mdi:floor-plan"
        elif self._id == "stats_time":
            return "mdi:timer-outline"
        elif self._id == "stats_type":
            return "mdi:cog"

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        listener: EventListener = self._vacbot.statsEvents.subscribe(lambda _: self.schedule_update_ha_state())
        self.async_on_remove(listener.unsubscribe)
