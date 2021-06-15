"""Support for Deebot Vaccums."""
import base64
import logging
from typing import Optional, Dict, Any

from deebotozmo.events import EventListener
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.components.camera import Camera

from .const import *
from .helpers import get_device_info
from .hub import DeebotHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    hub: DeebotHub = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []

    for vacbot in hub.vacuum_bots:
        new_devices.append(DeeboLiveCamera(vacbot, "liveMap"))

    if new_devices:
        async_add_devices(new_devices)


class DeeboLiveCamera(Camera):
    """Deebot Live Camera"""

    def __init__(self, vacuum_bot: VacuumBot, device_id: str):
        """Initialize the camera."""
        super().__init__()
        self._vacuum_bot: VacuumBot = vacuum_bot
        self._id: str = device_id

        if self._vacuum_bot.vacuum.nick is not None:
            self._name: str = self._vacuum_bot.vacuum.nick
        else:
            # In case there is no nickname defined, use the device id
            self._name = self._vacuum_bot.vacuum.did

        self._name += f"_{device_id}"

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return f"{self._vacuum_bot.vacuum.did}_{self._id}"

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return get_device_info(self._vacuum_bot)

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return False

    async def async_camera_image(self):
        """Return a still image response from the camera."""
        return base64.decodebytes(self._vacuum_bot.map.base64Image)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""

        async def on_event():
            self.schedule_update_ha_state()

        listener: EventListener = self._vacuum_bot.map.mapEvents.subscribe(on_event)
        self.async_on_remove(listener.unsubscribe)
