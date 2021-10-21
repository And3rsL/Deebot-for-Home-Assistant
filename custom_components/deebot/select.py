"""Select module."""
import logging
from typing import Any, Dict, List, Optional

from deebotozmo.commands import SetWaterInfo
from deebotozmo.events import StatusEventDto, WaterAmount, WaterInfoEventDto
from deebotozmo.events.event_bus import EventListener
from deebotozmo.vacuum_bot import VacuumBot
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .helpers import get_device_info
from .hub import DeebotHub
from .util import unsubscribe_listeners

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
        new_devices.append(WaterInfoSelect(vacbot))

    if new_devices:
        async_add_entities(new_devices)


class WaterInfoSelect(SelectEntity):  # type: ignore
    """Water info select entity."""

    entity_description = SelectEntityDescription(
        key="water_amount",
        entity_registry_enabled_default=False,
        icon="mdi:water",
    )

    def __init__(self, vacuum_bot: VacuumBot):
        """Initialize the Sensor."""
        self._vacuum_bot: VacuumBot = vacuum_bot

        device_info = self._vacuum_bot.device_info
        if device_info.nick is not None:
            name: str = device_info.nick
        else:
            # In case there is no nickname defined, use the device id
            name = device_info.did

        self._attr_name = f"{name}_{self.entity_description.key}"
        self._attr_unique_id = f"{device_info.did}_{self.entity_description.key}"

        self._attr_options = [amount.display_name for amount in WaterAmount]
        self._attr_current_option: Optional[str] = None

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """Return device specific attributes."""
        return get_device_info(self._vacuum_bot)

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        async def on_status(event: StatusEventDto) -> None:
            if not event.available:
                self._attr_current_option = None
                self.async_write_ha_state()

        async def on_water_info(event: WaterInfoEventDto) -> None:
            self._attr_current_option = event.amount.display_name
            self.async_write_ha_state()

        listeners: List[EventListener] = [
            self._vacuum_bot.events.subscribe(WaterInfoEventDto, on_water_info),
            self._vacuum_bot.events.subscribe(StatusEventDto, on_status),
        ]
        self.async_on_remove(lambda: unsubscribe_listeners(listeners))

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self._vacuum_bot.execute_command(SetWaterInfo(option))
