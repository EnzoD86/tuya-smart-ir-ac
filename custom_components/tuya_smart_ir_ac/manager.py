import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from .api import TuyaGenericAPI
from .const import DOMAIN
from .models import TuyaGenericData
from .tuya_connector import TuyaOpenAPI

_LOGGER = logging.getLogger(__package__)


class TuyaIRManager:
    """Manager handling data fetching and command execution for generic IR devices."""

    def __init__(self, hass: HomeAssistant, client: TuyaOpenAPI) -> None:
        """Initialize the generic IR manager."""
        self._hass = hass
        self._api = TuyaGenericAPI(hass, client=client)

    async def async_fetch_data(self, infrared_id: str, device_id: str) -> TuyaGenericData | None:
        """Fetch runtime keys configuration for a generic IR remote controller."""
        _LOGGER.debug("Fetching generic IR data for device %s (IR: %s)", device_id, infrared_id)
        result = await self._api.async_fetch_data(infrared_id, device_id)

        if not result.success:
            _LOGGER.error("Failed to load keys for generic IR device: %s", result.error_info)
            return None

        return result.data

    async def async_send_command(
        self, infrared_id: str, device_id: str, category_id: str, key_id: str, key: str
    ) -> None:
        """Send a specific key command code to a generic IR peripheral."""
        _LOGGER.debug(
            "Sending IR command to device %s - Key: %s (ID: %s), Category: %s",
            device_id, key, key_id, category_id
        )
        result = await self._api.async_send_command(infrared_id, device_id, category_id, key_id, key)
        
        if not result.success:
            _LOGGER.error("Failed to send IR command to device %s: %s", device_id, result.error_info)
            raise ServiceValidationError(
                translation_domain=DOMAIN, 
                translation_key="device_error_send_command"
            )