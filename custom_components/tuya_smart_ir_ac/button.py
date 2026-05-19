import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    MANUFACTURER,
    GENERIC_MODEL,
    CONF_INFRARED_ID,
    CONF_DEVICE_ID,
    DEVICE_TYPE_GENERICS
)
from .models import HubConfigEntry

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant, 
    config_entry: HubConfigEntry, 
    async_add_entities
) -> None:
    """Set up generic IR buttons associated with the specific Hub config entry."""
    active_entities = []
    generics_data = config_entry.options.get(DEVICE_TYPE_GENERICS, [])
    ir_manager = config_entry.runtime_data.ir_manager

    for data in generics_data:
        infrared_id = data.get(CONF_INFRARED_ID)
        device_id = data.get(CONF_DEVICE_ID)
        name = data.get(CONF_NAME)
        
        if not infrared_id or not device_id:
            continue

        try:
            device_data = await ir_manager.async_fetch_data(infrared_id, device_id)
            
            for key_data in device_data.key_list:
                entity = TuyaButton(
                    config_entry=config_entry,
                    ir_manager=ir_manager,
                    infrared_id=infrared_id,
                    device_id=device_id,
                    device_name=name,
                    category_id=device_data.category_id,
                    key_data=key_data
                )
                active_entities.append(entity)
                
        except Exception as e:
            _LOGGER.error(
                "Failed to load keys for generic IR device %s: %s", 
                name, e
            )

    if active_entities:
        async_add_entities(active_entities)


class TuyaButton(ButtonEntity):
    """Representation of a single button on a generic IR remote control."""

    def __init__(
        self, 
        config_entry: HubConfigEntry,
        ir_manager, 
        infrared_id: str, 
        device_id: str, 
        device_name: str,
        category_id: str | None, 
        key_data: Any
    ) -> None:
        """Initialize the IR button entity."""
        self._ir_manager = ir_manager
        self._infrared_id = infrared_id
        self._device_id = device_id
        self._device_name = device_name
        self._category_id = category_id
        self._key = key_data.key
        self._key_id = key_data.key_id
        self._key_name = key_data.key_name

        self._attr_name = f"{device_name} {self._key_name}"
        self._attr_unique_id = f"{infrared_id}_{device_id}_{self._key_id}"

        self._attr_device_info = DeviceInfo(
            name=device_name,
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{device_id}")},
            manufacturer=MANUFACTURER,
            model=GENERIC_MODEL,
        )

    async def async_press(self) -> None:
        _LOGGER.debug("Pressing button '%s' for device %s", self._key_name, self._device_name)
        await self._ir_manager.async_send_command(
            self._infrared_id, 
            self._device_id, 
            self._category_id, 
            self._key_id, 
            self._key
        )