import logging
import asyncio
from typing import Any, Literal

from homeassistant.core import HomeAssistant

from .models import(
    TuyaClimateData,
    TuyaGenericData,
    TuyaSensorData,
    TuyaAPIResult
)

_LOGGER = logging.getLogger(__package__)


class TuyaBaseAPI:
    """Base class that centralizes and normalizes the output of all Tuya APIs."""

    def __init__(self, hass: HomeAssistant, client: TuyaOpenAPI) -> None:
        """Initialize the base API client."""
        self._hass = hass
        self._client = client

    async def _request(
        self, 
        method: Literal["GET", "POST"], 
        url: str, 
        payload: Any = None, 
        factory: Any = None
    ) -> TuyaAPIResult:
        """Execute the request and ALWAYS return a TuyaAPIResult, safely parsing data if a factory is provided."""
        try:
            _LOGGER.debug("API request %s url: %s payload: %s", method, url, payload)
            if method == "GET":
                result = await self._client.get(url, params=payload)
            else:
                result = await self._client.post(url, body=payload)
            _LOGGER.debug("API response: %s", result)
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
                _LOGGER.error("Failed to parse Tuya response with factory: %s", parse_err)
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

    async def async_send_command(self, infrared_id: str, climate_id: str, code: str, value: Any) -> TuyaAPIResult:
        url = f"/v2.0/infrareds/{infrared_id}/air-conditioners/{climate_id}/command"
        return await self._request("POST", url, {"code": code, "value": value})

    async def async_send_multiple_command(
        self, infrared_id: str, climate_id: str, power: Any, mode: Any, temp: Any, wind: Any
    ) -> TuyaAPIResult:
        url = f"/v2.0/infrareds/{infrared_id}/air-conditioners/{climate_id}/scenes/command"
        return await self._request("POST", url, {"power": power, "mode": mode, "temp": temp, "wind": wind})


class TuyaGenericAPI(TuyaBaseAPI):
    """API client wrapper for generic mapped Infrared raw remotes."""

    async def async_fetch_data(self, infrared_id: str, device_id: str) -> TuyaAPIResult:
        url = f"/v2.0/infrareds/{infrared_id}/remotes/{device_id}/keys"
        return await self._request("GET", url, factory=TuyaGenericData.from_raw_data)

    async def async_send_command(
        self, infrared_id: str, device_id: str, category_id: str, key_id: str, key: str
    ) -> TuyaAPIResult:
        url = f"/v2.0/infrareds/{infrared_id}/remotes/{device_id}/raw/command"
        return await self._request("POST", url, {"category_id": category_id, "key_id": key_id, "key": key})


class TuyaSensorAPI(TuyaBaseAPI):
    """API client wrapper interacting with cloud-connected physical hardware sensors."""

    async def async_fetch_data(self, device_id: str) -> TuyaAPIResult:
        """Fetch runtime state for a single standalone sensor entity."""
        url = f"/v2.0/cloud/thing/{device_id}/shadow/properties"
        return await self._request("GET", url, factory=TuyaSensorData.from_raw_data)

    async def async_fetch_all_data(self, device_ids: list[str]) -> TuyaAPIResult:
        """Fetch runtime states for multiple sensors concurrently and map them into a typed dictionary."""
        # ARCHITECTURAL NOTE: Tuya does not provide a native batch endpoint for generic/sensor shadow states, 
        # forcing us to make individual requests per device. To prevent a severe performance bottleneck 
        # where polling time scales linearly with the number of sensors (e.g., 5 sensors x 200ms = 1s delay), 
        # we leverage asyncio.gather to fire requests concurrently over the same HTTP Keep-Alive pipeline.
        #
        # RATE LIMITING & SCALABILITY SAFETY:
        # Standard Tuya developer accounts allow ample concurrent GET requests per second. However, 
        # if an environment scales to a massive number of sensors (e.g., 30+) and triggers a Tuya 
        # Rate Limit (HTTP 429 / Code 1010), we can safely throttle concurrency without reverting to 
        # slow sequential execution by introducing an asyncio.Semaphore(3) inside this orchestrator.
        # Currently, partial failures are caught gracefully per-task without crashing the whole coordinator cycle.
        tasks = [self.async_fetch_data(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        devices = {}
        for device_id, result in zip(device_ids, results):
            if result.success:
                devices[device_id] = result.data
            else:
                _LOGGER.warning("Could not fetch data for sensor %s: %s", device_id, result.error_info)

        return TuyaAPIResult(success=True, data=devices)