"""Support for Deebot Sensor."""
import logging
from typing import Optional, Dict, Any

from deebotozmo.constants import COMPONENT_MAIN_BRUSH, COMPONENT_SIDE_BRUSH, COMPONENT_FILTER
from deebotozmo.events import CleanLogEvent, WaterInfoEvent, LifeSpanEvent, StatsEvent, EventListener
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .helpers import get_device_info
from .hub import DeebotHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    hub: DeebotHub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for vacbot in hub.vacuum_bots:
        # General
        new_devices.append(DeebotLastCleanImageSensor(vacbot, "last_clean_image"))
        new_devices.append(DeebotWaterLevelSensor(vacbot, "water_level"))

        # Components
        new_devices.append(DeebotComponentSensor(vacbot, COMPONENT_MAIN_BRUSH))
        new_devices.append(DeebotComponentSensor(vacbot, COMPONENT_SIDE_BRUSH))
        new_devices.append(DeebotComponentSensor(vacbot, COMPONENT_FILTER))

        # Stats
        new_devices.append(DeebotStatsSensor(vacbot, "area"))
        new_devices.append(DeebotStatsSensor(vacbot, "time"))
        new_devices.append(DeebotStatsSensor(vacbot, "type"))
        new_devices.append(DeebotStatsSensor(vacbot, "cid"))
        new_devices.append(DeebotStatsSensor(vacbot, "start"))

    if new_devices:
        async_add_devices(new_devices)


class DeebotBaseSensor(Entity):
    """Deebot base sensor"""

    def __init__(self, vacuum_bot: VacuumBot, device_id: str, icon: Optional[str]):
        """Initialize the Sensor."""
        self._vacuum_bot: VacuumBot = vacuum_bot
        self._id: str = device_id

        if self._vacuum_bot.vacuum.nick is not None:
            self._name: str = self._vacuum_bot.vacuum.nick
        else:
            # In case there is no nickname defined, use the device id
            self._name = self._vacuum_bot.vacuum.did

        self._name += f"_{device_id}"
        self._value = None
        self._icon = icon

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return f"{self._vacuum_bot.vacuum.did}_{self._id}"

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return False

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return get_device_info(self._vacuum_bot)

    @property
    def state(self):
        if self._value is not None:
            return self._value
        else:
            return STATE_UNKNOWN

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        return self._icon


class DeebotLastCleanImageSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    def __init__(self, vacuum_bot: VacuumBot, device_id: str):
        """Initialize the Sensor."""
        super(DeebotLastCleanImageSensor, self).__init__(vacuum_bot, device_id, "mdi:image-search")

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: CleanLogEvent):
            if len(event.logs) == 0:
                self._value = None
            else:
                self._value = event.logs[0].imageUrl
            self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.cleanLogsEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotWaterLevelSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    def __init__(self, vacuum_bot: VacuumBot, device_id: str):
        """Initialize the Sensor."""
        super(DeebotWaterLevelSensor, self).__init__(vacuum_bot, device_id, "mdi:water")

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""

        async def on_event(event: WaterInfoEvent):
            self._value = event.amount
            self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.waterEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotComponentSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    def __init__(self, vacuum_bot: VacuumBot, device_id: str):
        """Initialize the Sensor."""
        icon = "mdi:air-filter" if device_id == COMPONENT_FILTER else "mdi:broom"
        super(DeebotComponentSensor, self).__init__(vacuum_bot, device_id, icon)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "%"

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""

        async def on_event(event: LifeSpanEvent):
            if self._id == event.type:
                self._value = event.percent
                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.lifespanEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotStatsSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    def __init__(self, vacuum_bot: VacuumBot, type: str):
        """Initialize the Sensor."""
        icon = None
        if type == "area":
            icon = "mdi:floor-plan"
        elif type == "time":
            icon = "mdi:timer-outline"
        elif type == "type":
            icon = "mdi:cog"
        super(DeebotStatsSensor, self).__init__(vacuum_bot, f"stats_{type}", icon)
        self._type = type

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._type == "area":
            return "mq"
        elif self._type == "time":
            return "min"

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""

        async def on_event(event: StatsEvent):
            if hasattr(event, self._type):
                self._value = getattr(event, self._type)

                if self._type == "time":
                    self._value = round(self._value / 60)

                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.statsEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)
