import asyncio
import logging
from typing import Any, Literal

from homeassistant.core import HomeAssistant

from .models import (
    TuyaAPIResult,
    TuyaClimateData,
    TuyaGenericData,
    TuyaSensorData,
)
from .tuya_connector import TuyaOpenAPI

_LOGGER = logging.getLogger(__package__)


class TuyaBaseAPI:
    """Base class that centralizes and normalizes the output of all Tuya APIs."""

    def __init__(self, hass: HomeAssistant, client: TuyaOpenAPI, log_prefix: str = "") -> None:
        """Initialize the base API client."""
        self._hass = hass
        self._client = client
        self._log_prefix = f"{log_prefix} " if log_prefix else ""

    async def _request(
        self, 
        method: Literal["GET", "POST"], 
        url: str, 
        payload: Any = None, 
        factory: Any = None
    ) -> TuyaAPIResult:
        """Execute the request and ALWAYS return a TuyaAPIResult, safely parsing data if a factory is provided."""
        try:
            _LOGGER.debug("%sAPI request %s url: %s payload: %s", self._log_prefix, method, url, payload)
            if method == "GET":
                result = await self._client.get(url, params=payload)
            else:
                result = await self._client.post(url, body=payload)
            _LOGGER.debug("%sAPI response: %s", self._log_prefix, result)
        except Exception as err:
            # Level 1: The HTTP client crashed (Timeout, Network Offline, etc.)
            return TuyaAPIResult(
                success=False,
                error_code="HTTP_CONN_FAIL",
                error_msg=str(err)
            )

        # Level 2: The client returned None
        if result is None:
            return TuyaAPIResult(
                success=False,
                error_code="HTTP_ERROR",
                error_msg="Empty or invalid HTTP response from cloud"
            )

        # Level 3: Tuya responded but reported a business/logic failure
        if not result.get("success"):
            return TuyaAPIResult(
                success=False,
                error_code=result.get("code", "Unknown"),
                error_msg=result.get("msg", "No specific error message provided")
            )

        data = result.get("result")
        
        # If a factory function is provided, securely convert raw data into the domain model
        if factory and data is not None:
            try:
                data = factory(data)
            except Exception as parse_err:
                _LOGGER.error("%sFailed to parse Tuya response with factory: %s", self._log_prefix, parse_err)
                return TuyaAPIResult(
                    success=False,
                    error_code="PARSE_ERROR",
                    error_msg=f"Failed to map raw response into model: {parse_err}"
                )

        # Absolute success with structured model data
        return TuyaAPIResult(success=True, data=data)


class TuyaClimateAPI(TuyaBaseAPI):
    """API client wrapper for Tuya Infrared Air Conditioner devices."""

    async def async_fetch_all_data(self, climate_ids: list[str]) -> TuyaAPIResult:
        """Fetch runtime status for multiple climate devices in a single batch request."""
        url = f"/v1.0/cloud/rc/infrared/ac/status/batch?device_ids={','.join(climate_ids)}"
        return await self._request("GET", url, factory=TuyaClimateData.from_batch_data)

    async def async_fetch_data(self, infrared_id: str, climate_id: str) -> TuyaAPIResult:
        """Fetch runtime state matrix properties for a single targeted climate entity."""
        url = f"/v2.0/infrareds/{infrared_id}/remotes/{climate_id}/ac/status"
        return await self._request("GET", url, factory=TuyaClimateData.from_raw_data)

    async def async_fetch_hub_properties(self, infrared_id: str) -> TuyaAPIResult:
        """Fetch the IR hub device shadow properties (onboard ambient temperature/humidity)."""
        url = f"/v2.0/cloud/thing/{infrared_id}/shadow/properties"
        return await self._request("GET", url)

    async def async_send_command(self, infrared_id: str, climate_id: str, code: str, value: Any) -> TuyaAPIResult:
        """Send a single discrete infrared command to the targeted air conditioner."""
        url = f"/v2.0/infrareds/{infrared_id}/air-conditioners/{climate_id}/command"
        return await self._request("POST", url, {"code": code, "value": value})

    async def async_send_multiple_command(
        self, infrared_id: str, climate_id: str, power: Any, mode: Any, temp: Any, wind: Any
    ) -> TuyaAPIResult:
        """Send a macro scene state combination command matrix mapping multiple parameters."""
        url = f"/v2.0/infrareds/{infrared_id}/air-conditioners/{climate_id}/scenes/command"
        return await self._request("POST", url, {"power": power, "mode": mode, "temp": temp, "wind": wind})


class TuyaGenericAPI(TuyaBaseAPI):
    """API client wrapper for generic mapped Infrared raw remotes."""

    async def async_fetch_data(self, infrared_id: str, device_id: str) -> TuyaAPIResult:
        """Fetch mapped key layout assignments array configuration for a generic IR remote remote."""
        url = f"/v2.0/infrareds/{infrared_id}/remotes/{device_id}/keys"
        return await self._request("GET", url, factory=TuyaGenericData.from_raw_data)

    async def async_send_command(
        self, infrared_id: str, device_id: str, category_id: str, key_id: str, key: str
    ) -> TuyaAPIResult:
        """Transmit raw key pulse sequences targeting standard remote controller layouts."""
        url = f"/v2.0/infrareds/{infrared_id}/remotes/{device_id}/raw/command"
        return await self._request("POST", url, {"category_id": category_id, "key_id": key_id, "key": key})


class TuyaSensorAPI(TuyaBaseAPI):
    """API client wrapper interacting with standalone environmental Temperature/Humidity sensors."""

    async def async_fetch_data(self, device_id: str) -> TuyaAPIResult:
        """Fetch runtime shadow state metrics for a single physical temperature/humidity sensor."""
        url = f"/v2.0/cloud/thing/{device_id}/shadow/properties"
        return await self._request("GET", url, factory=TuyaSensorData.from_raw_data)

    async def async_fetch_all_data(self, device_ids: list[str]) -> TuyaAPIResult:
        """Fetch runtime states for multiple sensors concurrently and map them into a typed dictionary."""
        semaphore = asyncio.Semaphore(3)

        async def _fetch_with_semaphore(device_id: str) -> TuyaAPIResult:
            async with semaphore:
                return await self.async_fetch_data(device_id)

        tasks = [_fetch_with_semaphore(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        devices = {}
        for device_id, result in zip(device_ids, results):
            if result.success:
                devices[device_id] = result.data
            else:
                _LOGGER.warning("%sCould not fetch data for Temperature/Humidity sensor %s: %s", self._log_prefix, device_id, result.error_info)

        return TuyaAPIResult(success=True, data=devices)