"""Support for Deebot Sensor."""
import logging
from typing import Optional, Dict, Any

from deebotozmo.constants import COMPONENT_MAIN_BRUSH, COMPONENT_SIDE_BRUSH, COMPONENT_FILTER
from deebotozmo.events import CleanLogEvent, WaterInfoEvent, LifeSpanEvent, StatsEvent, EventListener, ErrorEvent, \
    StatusEvent
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNKNOWN, CONF_DESCRIPTION

from .const import DOMAIN, LAST_ERROR
from .helpers import get_device_info
from .hub import DeebotHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    hub: DeebotHub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for vacbot in hub.vacuum_bots:
        # General
        new_devices.append(DeebotLastCleanImageSensor(vacbot))
        new_devices.append(DeebotWaterLevelSensor(vacbot))
        new_devices.append(DeebotLastErrorSensor(vacbot))

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


class DeebotBaseSensor(SensorEntity):
    """Deebot base sensor"""

    _attr_should_poll = False
    _attr_entity_registry_enabled_default = False

    def __init__(self, vacuum_bot: VacuumBot, device_id: str):
        """Initialize the Sensor."""
        self._vacuum_bot: VacuumBot = vacuum_bot

        if self._vacuum_bot.vacuum.nick is not None:
            name: str = self._vacuum_bot.vacuum.nick
        else:
            # In case there is no nickname defined, use the device id
            name = self._vacuum_bot.vacuum.did

        self._attr_name = f"{name}_{device_id}"
        self._attr_unique_id = f"{self._vacuum_bot.vacuum.did}_{device_id}"

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return get_device_info(self._vacuum_bot)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: StatusEvent):
            if not event.available:
                self._attr_native_value = STATE_UNKNOWN
                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.statusEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotLastCleanImageSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    _attr_icon = "mdi:image-search"

    def __init__(self, vacuum_bot: VacuumBot):
        """Initialize the Sensor."""
        super(DeebotLastCleanImageSensor, self).__init__(vacuum_bot, "last_clean_image")

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: CleanLogEvent):
            if event.logs:
                self._attr_native_value = event.logs[0].imageUrl
            else:
                self._attr_native_value = STATE_UNKNOWN
            self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.cleanLogsEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotWaterLevelSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    _attr_icon = "mdi:water"

    def __init__(self, vacuum_bot: VacuumBot):
        """Initialize the Sensor."""
        super(DeebotWaterLevelSensor, self).__init__(vacuum_bot, "water_level")

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: WaterInfoEvent):
            if event.amount:
                self._attr_native_value = event.amount
                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.waterEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotComponentSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    _attr_native_unit_of_measurement = "%"

    def __init__(self, vacuum_bot: VacuumBot, device_id: str):
        """Initialize the Sensor."""
        super(DeebotComponentSensor, self).__init__(vacuum_bot, device_id)
        self._attr_icon = "mdi:air-filter" if device_id == COMPONENT_FILTER else "mdi:broom"
        self._id = device_id

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: LifeSpanEvent):
            if self._id == event.type:
                self._attr_native_value = event.percent
                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.lifespanEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotStatsSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    def __init__(self, vacuum_bot: VacuumBot, type: str):
        """Initialize the Sensor."""

        super(DeebotStatsSensor, self).__init__(vacuum_bot, f"stats_{type}")
        self._type = type
        if type == "area":
            self._attr_icon = "mdi:floor-plan"
            self._attr_native_unit_of_measurement = "mq"
        elif type == "time":
            self._attr_icon = "mdi:timer-outline"
            self._attr_native_unit_of_measurement = "min"
        elif type == "type":
            self._attr_icon = "mdi:cog"

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: StatsEvent):
            if hasattr(event, self._type):
                value = getattr(event, self._type)

                if not value:
                    return

                if self._type == "time":
                    self._attr_native_value = round(value / 60)
                else:
                    self._attr_native_value = value

                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.statsEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)


class DeebotLastErrorSensor(DeebotBaseSensor):
    """Deebot Sensor"""

    _attr_icon = "mdi:alert-circle"

    def __init__(self, vacuum_bot: VacuumBot):
        """Initialize the Sensor."""
        super(DeebotLastErrorSensor, self).__init__(vacuum_bot, LAST_ERROR)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: ErrorEvent):
            self._attr_native_value = event.code
            self._attr_extra_state_attributes = {
                CONF_DESCRIPTION: event.description
            }
            self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.errorEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)
