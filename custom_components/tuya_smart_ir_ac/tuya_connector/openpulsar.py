#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import asyncio
import aiohttp
import base64
import hashlib
import json
import ssl
from typing import Callable, Awaitable, Set, Tuple, Optional
from Crypto.Cipher import AES

from .openlogging import get_module_logger

logger = get_module_logger("openpulsar")

# Constants
WEB_SOCKET_QUERY_PARAMS = "?ackTimeoutMillis=3000&subscriptionType=Failover"
PING_INTERVAL_SECONDS = 30
MAX_RECONNECT_DELAY = 60  # Maximum seconds to wait before reconnecting


class TuyaOpenPulsar:
    """Tuya Open Pulsar client natively integrated with asyncio and aiohttp."""

    def __init__(
        self, 
        ws_endpoint: str,
        access_id: str, 
        access_secret: str, 
        topic: str,
        session: Optional[aiohttp.ClientSession] = None,
        ssl_context: Optional[ssl.SSLContext] = None
    ):
        """Initialize the Async Pulsar Client."""
        self._ws_endpoint = ws_endpoint
        self._access_id = access_id
        self._access_secret = access_secret
        self._topic = topic
        
        # Session lifecycle management
        self._session = session
        self._owns_session = session is None

        # Track the live connection state of the WebSocket
        self._is_connected = False

        # SSL context passed from HA, or synchronous fallback (safe outside the event loop)
        self._ssl_context = ssl_context or ssl.create_default_context()
        
        self._stop_event = asyncio.Event()
        self._listeners: Set[Callable[[str], Awaitable[None]]] = set()
        self._task: Optional[asyncio.Task] = None
        
        # Pre-calculate cryptographic assets
        self._access_secret_bytes = access_secret.encode('utf-8')
        self._key_bytes = access_secret[8:24].encode('utf-8')
        self._pwd = self._gen_pwd()
        self._topic_url = (
            f"{self._ws_endpoint}ws/v2/consumer/persistent/"
            f"{self._access_id}/out/{self._topic}/"
            f"{self._access_id}-sub{WEB_SOCKET_QUERY_PARAMS}"
        )

    def is_connected(self) -> bool:
        """Return True if the Pulsar WebSocket client is currently connected."""
        return self._is_connected

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy instantiation of the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    def _gen_pwd(self) -> str:
        """Generate Tuya authentication password token."""
        secret_hash = hashlib.md5(self._access_secret_bytes).hexdigest()
        mix_str = self._access_id + secret_hash
        return hashlib.md5(mix_str.encode('utf-8')).hexdigest()[8:24]

    def add_message_listener(self, listener: Callable[[str], Awaitable[None]]):
        """Register a new async callback for incoming decrypted payloads."""
        self._listeners.add(listener)

    def remove_message_listener(self, listener: Callable[[str], Awaitable[None]]):
        """Unregister an existing async callback."""
        self._listeners.discard(listener)

    async def start(self):
        """Start the asynchronous connection loop."""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._connect_loop())

    async def stop(self):
        """Stop the client and close session only if owned."""
        self._stop_event.set()
        if self._task is not None and not self._task.done():
            self._task.cancel()
            self._task = None
        self._listeners.clear()
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        else:
            logger.debug("Skipping session close because the session is managed externally.")

    async def _connect_loop(self):
        """Main reconnection loop running the WebSocket lifecycle."""
        reconnect_delay = 1
        headers = {
            "Connection": "Upgrade", 
            "username": self._access_id, 
            "password": self._pwd
        }

        while not self._stop_event.is_set():
            try:
                session = await self._get_session()
                
                async with session.ws_connect(
                    self._topic_url, 
                    headers=headers,
                    heartbeat=PING_INTERVAL_SECONDS,
                    ssl=self._ssl_context
                ) as ws:
                    logger.info("Successfully connected to Tuya WebSocket.")
                    reconnect_delay = 1
                    
                    async_msg: aiohttp.WSMessage
                    async for async_msg in ws:
                        if self._stop_event.is_set():
                            break
                            
                        if async_msg.type == aiohttp.WSMsgType.TEXT:
                            if not self._is_connected:
                                self._is_connected = True
                                logger.info("Tuya Pulsar data stream successfully verified and active.")
                                
                            await self._process_message(ws, async_msg.data)
                            
                        elif async_msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
                            
            except aiohttp.ClientError as e:
                logger.debug("WebSocket network error: %s", e)
            except Exception as e:
                logger.exception("Unexpected error in Pulsar loop: %s", e)
            finally:
                # Connection lost or loop interrupted
                self._is_connected = False                
                
            if self._stop_event.is_set():
                break
                
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)

    async def _process_message(self, ws: aiohttp.ClientWebSocketResponse, message: str):
        """Process incoming messages deterministically based on metadata envelope."""
        try:
            message_json = json.loads(message)
            
            # Immediately send ACK response to prevent Pulsar queue congestion
            ack_payload = json.dumps({"messageId": message_json["messageId"]})
            await ws.send_str(ack_payload)
            
            # Parse outer envelope payload
            payload_bytes = base64.b64decode(message_json["payload"])
            data_map = json.loads(payload_bytes.decode('utf-8'))
            
            encrypt_version = data_map.get("encryptVersion", "v1")
            pv = data_map.get("pv")
            raw_data_str = data_map.get("data", "")
            raw_encrypted_bytes = base64.b64decode(raw_data_str)

            # Deterministic routing based on protocol metadata
            if encrypt_version == "v2" and pv == "2.0":
                #logger.debug("Processing message format: AES-GCM (encryptVersion: v2, pv: 2.0)")
                decrypt_data = self._decrypt_gcm(raw_encrypted_bytes)
            else:
                #logger.debug("Processing message format: AES-ECB (encryptVersion: %s, pv: %s)", encrypt_version, pv)
                decrypt_data = self._decrypt_ecb(raw_encrypted_bytes)
            
            # Fan-out decrypted data to registered integration listeners
            for listener in self._listeners:
                try:
                    await listener(decrypt_data)
                except Exception as e:
                    logger.error("Error executing async listener: %s", e)
            
        except Exception as e:
            logger.error("Error processing incoming message payload: %s", e)

    def _decrypt_gcm(self, raw_data: bytes) -> str:
        """Decrypt payload using AES-GCM mode (pv 2.0)."""
        nonce = raw_data[:12]
        ciphertext = raw_data[12:-16]
        tag = raw_data[-16:]
        cipher = AES.new(self._key_bytes, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')

    def _decrypt_ecb(self, raw_data: bytes) -> str:
        """Decrypt payload using AES-ECB mode (Legacy or downgraded pv)."""
        cipher = AES.new(self._key_bytes, AES.MODE_ECB)
        decrypted = cipher.decrypt(raw_data)
        padding_len = decrypted[-1]
        return decrypted[:-padding_len].decode('utf-8')