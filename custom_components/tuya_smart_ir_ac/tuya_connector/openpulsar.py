#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import asyncio
import aiohttp
import base64
import hashlib
import json
import logging
from typing import Callable, Awaitable, Set, Tuple, Optional

from Crypto.Cipher import AES

from .openlogging import logger

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
        session: Optional[aiohttp.ClientSession] = None
    ):
        """Initialize the Async Pulsar Client."""
        self._ws_endpoint = ws_endpoint
        self._access_id = access_id
        self._access_secret = access_secret
        self._topic = topic
        
        # Gestione sessione con logica di proprietà
        self._session = session
        self._owns_session = session is None
        
        self._stop_event = asyncio.Event()
        self._listeners: Set[Callable[[str], Awaitable[None]]] = set()
        
        # Pre-calculate cryptographic assets
        self._key_bytes = access_secret[8:24].encode('utf-8')
        self._pwd = self._gen_pwd()
        self._topic_url = (
            f"{self._ws_endpoint}ws/v2/consumer/persistent/"
            f"{self._access_id}/out/{self._topic}/"
            f"{self._access_id}-sub{WEB_SOCKET_QUERY_PARAMS}"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy instantiation of the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    def _gen_pwd(self) -> str:
        """Generate Tuya authentication password token."""
        secret_hash = hashlib.md5(self._access_secret.encode('utf-8')).hexdigest()
        mix_str = self._access_id + secret_hash
        return hashlib.md5(mix_str.encode('utf-8')).hexdigest()[8:24]

    def add_message_listener(self, listener: Callable[[str], Awaitable[None]]):
        self._listeners.add(listener)

    def remove_message_listener(self, listener: Callable[[str], Awaitable[None]]):
        self._listeners.discard(listener)

    def _decrypt_payload(self, raw: str) -> Tuple[str, str]:
        """Decrypt payload."""
        raw_data = base64.b64decode(raw)
        if len(raw_data) > 32:
            try:
                nonce = raw_data[:12]
                ciphertext = raw_data[12:-16]
                tag = raw_data[-16:]
                cipher = AES.new(self._key_bytes, AES.MODE_GCM, nonce=nonce)
                decrypted = cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
                return decrypted, "AES-GCM"
            except Exception:
                pass

        try:
            cipher = AES.new(self._key_bytes, AES.MODE_ECB)
            decrypted = cipher.decrypt(raw_data)
            padding_len = decrypted[-1]
            unpadded = decrypted[:-padding_len].decode('utf-8')
            return unpadded, "AES-ECB"
        except Exception as ecb_err:
            logger.error("Decryption failed for both AES-GCM and AES-ECB modes.")
            raise ecb_err

    async def start(self):
        """Start the asynchronous connection loop."""
        self._stop_event.clear()
        asyncio.create_task(self._connect_loop())

    async def stop(self):
        """Stop the client and close session only if owned."""
        self._stop_event.set()
        self._listeners.clear()
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _connect_loop(self):
        """Main reconnection loop."""
        reconnect_delay = 1
        headers = {
            "Connection": "Upgrade", 
            "username": self._access_id, 
            "password": self._pwd
        }

        while not self._stop_event.is_set():
            try:
                # Otteniamo la sessione (o la creiamo se necessario)
                session = await self._get_session()
                
                async with session.ws_connect(
                    self._topic_url, 
                    headers=headers,
                    heartbeat=PING_INTERVAL_SECONDS,
                    ssl=False
                ) as ws:
                    logger.info("Successfully connected to Tuya WebSocket.")
                    reconnect_delay = 1
                    
                    async for msg in ws:
                        if self._stop_event.is_set():
                            break
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._process_message(ws, msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
                            
            except aiohttp.ClientError as e:
                logger.debug("WebSocket network error: %s", e)
            except Exception as e:
                logger.exception("Unexpected error in Pulsar loop: %s", e)
                
            if self._stop_event.is_set():
                break
                
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)

    async def _process_message(self, ws: aiohttp.ClientWebSocketResponse, message: str):
        """Process messages."""
        try:
            message_json = json.loads(message)
            payload_bytes = base64.b64decode(message_json["payload"])
            data_map = json.loads(payload_bytes.decode('utf-8'))
            
            decrypt_data, protocol_used = self._decrypt_payload(data_map['data'])
            
            for listener in self._listeners:
                try:
                    await listener(decrypt_data)
                except Exception as e:
                    logger.error("Error executing async listener: %s", e)
            
            ack_payload = json.dumps({"messageId": message_json["messageId"]})
            await ws.send_str(ack_payload)
            
        except Exception as e:
            logger.error("Error processing incoming message payload: %s", e)