"""Binary sensor module."""
import logging
from typing import Any, Dict, Optional

from deebotozmo.event_emitter import EventListener
from deebotozmo.events import WaterInfoEvent
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .helpers import get_device_info
from .hub import DeebotHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add binary_sensor for passed config_entry in HA."""
    hub: DeebotHub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for vacbot in hub.vacuum_bots:
        new_devices.append(DeebotMopAttachedBinarySensor(vacbot, "mop_attached"))

    if new_devices:
        async_add_entities(new_devices)


class DeebotMopAttachedBinarySensor(BinarySensorEntity):  # type: ignore
    """Deebot mop attached binary sensor."""

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
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        return "mdi:water" if self.is_on else "mdi:water-off"

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """Return device specific attributes."""
        return get_device_info(self._vacuum_bot)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: WaterInfoEvent) -> None:
            self._attr_is_on = event.mop_attached
            self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.events.water_info.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)
