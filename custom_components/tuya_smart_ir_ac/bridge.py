import logging
import json
from collections.abc import Awaitable, Callable
from homeassistant.core import HomeAssistant

from .tuya_connector import TuyaOpenPulsar

_LOGGER = logging.getLogger(__package__)

class TuyaPulsarBridge:
    """Bridge for interfacing the Pulsar thread with Home Assistant."""

    def __init__(self, hass: HomeAssistant, client: TuyaOpenPulsar) -> None:
        """Initialize the Pulsar bridge."""
        self.hass = hass
        self._client = client
        self._handlers: dict[str, list[Callable[[str, dict], Awaitable[None]]]] = {}
        self._client.add_message_listener(self._on_message)

    def register_handler(
        self, dev_id: str, callback: Callable[[str, dict], Awaitable[None]]
    ) -> None:
        """Register a callback handler for a specific device."""
        self._handlers.setdefault(dev_id, []).append(callback)

    async def _on_message(self, decrypt_data: str) -> None:
        """Handle incoming Pulsar messages and dispatch to handlers safely."""
        try:
            data = json.loads(decrypt_data)
            dev_id = data.get("devId")
            handlers = self._handlers.get(dev_id)

            if handlers:
                for handler in handlers:
                    self.hass.async_create_task(handler(dev_id, data))

        except Exception as e:
            _LOGGER.error("Error processing Pulsar message: %s", e)