"""Sensor module."""
import logging
from typing import Any, Callable, Dict, Optional, Type, TypeVar

from deebotozmo.events import (
    CleanLogEventDto,
    ErrorEventDto,
    EventDto,
    LifeSpan,
    LifeSpanEventDto,
    StatsEventDto,
    StatusEventDto,
    TotalStatsEventDto,
    WaterInfoEventDto,
)
from deebotozmo.events.event_bus import EventListener
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DESCRIPTION, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, LAST_ERROR
from .helpers import get_device_info
from .hub import DeebotHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub: DeebotHub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for vacbot in hub.vacuum_bots:
        # General
        new_devices.append(
            GenericSensor(
                CleanLogEventDto,
                vacbot,
                "last_clean_image",
                lambda e: e.logs[0].image_url if e.logs else STATE_UNKNOWN,
                "mdi:image-search",
            )
        )
        new_devices.append(
            GenericSensor(
                WaterInfoEventDto,
                vacbot,
                "water_level",
                lambda e: e.amount,
                "mdi:water",
            )
        )
        new_devices.append(LastErrorSensor(vacbot))

        # Components
        new_devices.append(LifeSpanSensor(vacbot, LifeSpan.BRUSH))
        new_devices.append(LifeSpanSensor(vacbot, LifeSpan.SIDE_BRUSH))
        new_devices.append(LifeSpanSensor(vacbot, LifeSpan.FILTER))

        # Stats
        new_devices.append(
            GenericSensor(
                StatsEventDto,
                vacbot,
                "stats_area",
                lambda e: e.area,
                "mdi:floor-plan",
                "m²",
            )
        )
        new_devices.append(
            GenericSensor(
                StatsEventDto,
                vacbot,
                "stats_time",
                lambda e: round(e.time / 60) if e.time else None,
                "mdi:timer-outline",
                "h",
            )
        )
        new_devices.append(
            GenericSensor(
                StatsEventDto,
                vacbot,
                "stats_type",
                lambda e: e.type,
                "mdi:cog",
            )
        )
        new_devices.append(
            GenericSensor(
                StatsEventDto,
                vacbot,
                "stats_cid",
                lambda e: e.clean_id,
            )
        )
        new_devices.append(
            GenericSensor(
                StatsEventDto,
                vacbot,
                "stats_start",
                lambda e: e.start,
            )
        )

        # TotalStats
        new_devices.append(
            GenericSensor(
                TotalStatsEventDto,
                vacbot,
                "stats_total_area",
                lambda e: e.area,
                "mdi:floor-plan",
                "m²",
            )
        )
        new_devices.append(
            GenericSensor(
                TotalStatsEventDto,
                vacbot,
                "stats_total_time",
                lambda e: round(e.time / 3600),
                "mdi:timer-outline",
                "h",
            )
        )
        new_devices.append(
            GenericSensor(
                TotalStatsEventDto,
                vacbot,
                "stats_total_cleanings",
                lambda e: e.cleanings,
                "mdi:counter",
            )
        )

    if new_devices:
        async_add_entities(new_devices)


class BaseSensor(SensorEntity):  # type: ignore
    """Base sensor."""

    _attr_should_poll = False
    _attr_entity_registry_enabled_default = False

    def __init__(self, vacuum_bot: VacuumBot, sensor_name: str):
        """Initialize the Sensor."""
        self._vacuum_bot: VacuumBot = vacuum_bot

        device_info = self._vacuum_bot.device_info
        if device_info.nick is not None:
            name: str = device_info.nick
        else:
            # In case there is no nickname defined, use the device id
            name = device_info.did

        self._attr_name = f"{name}_{sensor_name}"
        self._attr_unique_id = f"{device_info.did}_{sensor_name}"

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """Return device specific attributes."""
        return get_device_info(self._vacuum_bot)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: StatusEventDto) -> None:
            if not event.available:
                self._attr_native_value = STATE_UNKNOWN
                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.events.subscribe(
            StatusEventDto, on_event
        )
        self.async_on_remove(listener.unsubscribe)


T = TypeVar("T", bound=EventDto)


class GenericSensor(BaseSensor):
    """Generic sensor."""

    _attr_should_poll = False
    _attr_entity_registry_enabled_default = False

    def __init__(  # pylint: disable=too-many-arguments
        self,
        event_type: Type[T],
        vacuum_bot: VacuumBot,
        sensor_name: str,
        extract_value: Callable[[T], StateType],
        icon: Optional[str] = None,
        unit_of_measurement: Optional[str] = None,
    ):
        """Initialize the Sensor."""
        super().__init__(vacuum_bot, sensor_name)
        self._event_type = event_type
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._extract_value = extract_value

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """Return device specific attributes."""
        return get_device_info(self._vacuum_bot)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: T) -> None:
            value = self._extract_value(event)
            if value is not None:
                self._attr_native_value = value
                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.events.subscribe(
            self._event_type, on_event
        )
        self.async_on_remove(listener.unsubscribe)


class LastErrorSensor(BaseSensor):
    """Last error sensor."""

    _attr_icon = "mdi:alert-circle"

    def __init__(self, vacuum_bot: VacuumBot):
        """Initialize the Sensor."""
        super().__init__(vacuum_bot, LAST_ERROR)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: ErrorEventDto) -> None:
            self._attr_native_value = event.code
            self._attr_extra_state_attributes = {CONF_DESCRIPTION: event.description}
            self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.events.subscribe(
            ErrorEventDto, on_event
        )
        self.async_on_remove(listener.unsubscribe)


class LifeSpanSensor(BaseSensor):
    """Life span sensor."""

    _attr_native_unit_of_measurement = "%"

    def __init__(self, vacuum_bot: VacuumBot, component: LifeSpan):
        """Initialize the Sensor."""
        sensor_name = component.name.lower()
        super().__init__(vacuum_bot, f"life_span_{sensor_name}")
        self._attr_icon = (
            "mdi:air-filter" if component == LifeSpan.FILTER else "mdi:broom"
        )
        self.component = component

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: LifeSpanEventDto) -> None:
            if event.type == self.component:
                self._attr_native_value = event.percent
                self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.events.subscribe(
            LifeSpanEventDto, on_event
        )
        self.async_on_remove(listener.unsubscribe)
