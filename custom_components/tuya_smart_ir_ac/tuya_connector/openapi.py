#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from __future__ import annotations

import aiohttp
import asyncio
import hashlib
import hmac
import json
import time
from typing import Any

from .openlogging import get_module_logger, filter_logger
from .version import VERSION


logger = get_module_logger("openapi")

# Constants
TUYA_ERROR_CODE_TOKEN_INVALID = 1010
TO_B_REFRESH_TOKEN_API = "/v1.0/token/{}"
TO_B_TOKEN_API = "/v1.0/token"

# Pre-computed SHA256 hash for empty payloads to save CPU cycles on GET/DELETE requests
EMPTY_PAYLOAD_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class TuyaTokenInfo:
    """Tuya token info storage and validation."""

    def __init__(self, token_response: dict[str, Any]):
        """Initialize TuyaTokenInfo."""
        result = token_response.get("result", {})

        # Calculate absolute expiration time in milliseconds
        self.expire_time = (
            token_response.get("t", 0)
            + result.get("expire", result.get("expire_time", 0)) * 1000
        )
        self.access_token = result.get("access_token", "")
        self.refresh_token = result.get("refresh_token", "")
        self.uid = result.get("uid", "")

    @property
    def is_valid(self) -> bool:
        """Check if the token is still valid (with a 60-second safety buffer)."""
        current_time_ms = int(time.time() * 1000)
        return (self.expire_time - 60000) > current_time_ms


class TuyaOpenAPI:
    """Tuya Open API client optimized for high concurrency."""

    def __init__(
        self,
        endpoint: str,
        access_id: str,
        access_secret: str,
        lang: str = "en",
        session: aiohttp.ClientSession | None = None,
    ):
        """Initialize TuyaOpenAPI."""
        self.endpoint = endpoint
        self.access_id = access_id
        # Pre-encode secret for faster HMAC operations
        self.access_secret_bytes = access_secret.encode("utf-8")
        self.lang = lang

        self.token_info: TuyaTokenInfo | None = None
        self.dev_channel: str = ""
        
        self._session: aiohttp.ClientSession | None = session
        self._owns_session: bool = session is None
        self._token_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy instantiation of the aiohttp session to ensure correct event loop binding."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    def _calculate_sign(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        payload_str: str = "",
    ) -> tuple[str, str]:
        """Calculate Tuya signature synchronously for maximum performance."""
        # 1. Content-SHA256 based on the exact pre-serialized string
        if payload_str:
            content_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest().lower()
        else:
            content_hash = EMPTY_PAYLOAD_SHA256

        # 2. URL and query string
        url_path = path
        if params:
            # Fast query string builder using comprehensions
            query_string = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
            url_path = f"{path}?{query_string}"

        # 3. Signed string assembly
        str_to_sign = f"{method}\n{content_hash}\n\n{url_path}"

        # 4. Final Signature
        timestamp = str(int(time.time() * 1000))
        
        access_token = ""
        if self.token_info and not path.startswith(TO_B_TOKEN_API):
            access_token = self.token_info.access_token

        message = f"{self.access_id}{access_token}{timestamp}{str_to_sign}".encode("utf-8")

        sign = hmac.new(
            self.access_secret_bytes,
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest().upper()

        return sign, timestamp

    async def _refresh_access_token_if_need(self, path: str) -> None:
        """Refresh token thread-safely using double-checked locking."""
        if path.startswith(TO_B_TOKEN_API) or not self.is_connected:
            return

        if self.token_info and self.token_info.is_valid:
            return

        async with self._token_lock:
            # Check again after acquiring lock to prevent duplicate refreshes
            if self.token_info and self.token_info.is_valid:
                return

            # Use _execute_request directly to bypass the __request auto-retry wrapper
            response = await self._execute_request(
                "GET",
                TO_B_REFRESH_TOKEN_API.format(self.token_info.refresh_token),
                None,
                None
            )
            
            if response and response.get("success"):
                self.token_info = TuyaTokenInfo(response)
            else:
                # If the refresh token itself is invalid, reconnect from scratch safely
                logger.debug("Refresh token failed. Requesting a completely new token...")
                self.token_info = None
                await self.connect()

    def set_dev_channel(self, dev_channel: str) -> None:
        """Set dev channel (Synchronous since it's just a property assignment)."""
        self.dev_channel = dev_channel

    async def connect(self) -> dict[str, Any] | None:
        """Connect to Tuya Cloud and initialize tokens."""
        response = await self.get(TO_B_TOKEN_API, {"grant_type": 1})

        if response and response.get("success"):
            self.token_info = TuyaTokenInfo(response)
            
        return response

    async def close(self) -> None:
        """Close the underlying aiohttp client session cleanly if owned."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        else:
            logger.debug("Skipping session close because the session is managed externally.")

    @property
    def is_connected(self) -> bool:
        """Check if connected to Tuya cloud."""
        return bool(self.token_info and self.token_info.access_token)

    async def __request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Request wrapper with automatic retry logic for invalid tokens."""
        result = await self._execute_request(method, path, params, body)

        # Retry logic: if token is invalid (1010), reconnect and retry exactly once
        if result and result.get("code", -1) == TUYA_ERROR_CODE_TOKEN_INVALID:
            logger.warning("Token invalid (1010) detected. Attempting automatic reconnection...")
            self.token_info = None
            await self.connect()
            result = await self._execute_request(method, path, params, body)

        return result

    async def _execute_request(
        self, 
        method: str, 
        path: str, 
        params: dict[str, Any] | None, 
        body: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Helper method to execute the actual HTTP request."""
        await self._refresh_access_token_if_need(path)
        
        # --- BULLETPROOF SERIALIZATION ---
        # Serialize once, compactly, to guarantee hash perfectly matches HTTP body
        payload_str = ""
        request_kwargs = {}
        
        if body is not None:
            payload_str = json.dumps(body, separators=(",", ":"))
            request_kwargs["data"] = payload_str # Invia la stringa esatta, bypassando la serializzazione automatica di aiohttp
        
        sign, timestamp = self._calculate_sign(method, path, params, payload_str)
        
        headers = {
            "client_id": self.access_id,
            "sign": sign,
            "sign_method": "HMAC-SHA256",
            "access_token": self.token_info.access_token if self.token_info else "",
            "t": timestamp,
            "lang": self.lang,
            "dev_lang": "python",
            "dev_version": VERSION,
            "dev_channel": f"cloud_{self.dev_channel}",
        }
        
        # Imposta esplicitamente il Content-Type visto che stiamo passando dati grezzi
        if payload_str:
            headers["Content-Type"] = "application/json"

        logger.debug(
            "Request: method=%s, url=%s, params=%s, body=%s, t=%s",
            method,
            self.endpoint + path,
            params,
            filter_logger(body),
            timestamp
        )

        session = await self._get_session()
        try:
            # Sfrutta **request_kwargs per passare "data=..." solo se è presente un body
            async with session.request(
                method, self.endpoint + path, params=params, headers=headers, **request_kwargs
            ) as response:
                if not response.ok:
                    logger.error("HTTP Response error: code=%s, body=%s", response.status, await response.text())
                    return None
                return await response.json()
        except Exception as e:
            logger.error("Failed to execute Tuya request: %s", e)
            return None

    async def get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Http Get."""
        return await self.__request("GET", path, params, None)

    async def post(
        self, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Http Post."""
        return await self.__request("POST", path, None, body)

    async def put(
        self, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Http Put."""
        return await self.__request("PUT", path, None, body)

    async def delete(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Http Delete."""
        return await self.__request("DELETE", path, params, None)