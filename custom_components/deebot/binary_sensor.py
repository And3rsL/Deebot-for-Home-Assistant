"""Support for Deebot Sensor."""
import logging
from typing import Optional, Dict, Any

from deebotozmo.events import WaterInfoEvent, EventListener
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN
from .helpers import get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add binary_sensor for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for vacbot in hub.vacbots:
        new_devices.append(DeebotMopAttachedBinarySensor(vacbot, "mop_attached"))

    if new_devices:
        async_add_devices(new_devices)


class DeebotMopAttachedBinarySensor(BinarySensorEntity):
    """Deebot mop attached binary sensor"""

    def __init__(self, vacuum_bot: VacuumBot, device_id: str):
        """Initialize the Sensor."""
        self._vacuum_bot: VacuumBot = vacuum_bot
        self._id: str = device_id

        if self._vacuum_bot.vacuum.nick is not None:
            self._name: str = self._vacuum_bot.vacuum.nick
        else:
            # In case there is no nickname defined, use the device id
            self._name = self._vacuum_bot.vacuum.did

        self._name += f"_{device_id}"
        self._mop_attached = False

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return f"{self._vacuum_bot.vacuum.did}_{self._id}"

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def is_on(self):
        return self._mop_attached

    @property
    def icon(self) -> Optional[str]:
        """Return the icon to use in the frontend, if any."""
        return "mdi:water" if self.is_on else "mdi:water-off"

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return False

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return get_device_info(self._vacuum_bot)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_event(event: WaterInfoEvent):
            self._mop_attached = event.mopAttached
            self.async_write_ha_state()

        listener: EventListener = self._vacuum_bot.waterEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe())
