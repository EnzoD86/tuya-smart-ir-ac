#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""Tuya Open API."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional, Tuple

import requests

from .openlogging import filter_logger, logger
from .version import VERSION

TUYA_ERROR_CODE_TOKEN_INVALID = 1010

TO_B_REFRESH_TOKEN_API = "/v1.0/token/{}"

TO_B_TOKEN_API = "/v1.0/token"


class TuyaTokenInfo:
    """Tuya token info.

    Attributes:
        access_token: Access token.
        expire_time: Valid period in seconds.
        refresh_token: Refresh token.
        uid: Tuya user ID.
        is_token_refreshing: If a token refresh is in progress.
    """

    def __init__(self, token_response: Dict[str, Any] = None):
        """Init TuyaTokenInfo."""
        result = token_response.get("result", {})

        self.expire_time = (
            token_response.get("t", 0)
            + result.get("expire", result.get("expire_time", 0)) * 1000
        )
        self.access_token = result.get("access_token", "")
        self.refresh_token = result.get("refresh_token", "")
        self.uid = result.get("uid", "")
        self.is_token_refreshing = False


class TuyaOpenAPI:
    """Open Api.

    Typical usage example:

    openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
    """

    def __init__(
        self,
        endpoint: str,
        access_id: str,
        access_secret: str,
        lang: str = "en",
    ):
        """Init TuyaOpenAPI."""
        self.session = requests.session()

        self.endpoint = endpoint
        self.access_id = access_id
        self.access_secret = access_secret
        self.lang = lang

        self.token_info: TuyaTokenInfo = None

        self.dev_channel: str = ""

    # https://developer.tuya.com/docs/iot/open-api/api-reference/singnature?id=Ka43a5mtx1gsc
    def _calculate_sign(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, int]:

        # HTTPMethod
        str_to_sign = method
        str_to_sign += "\n"

        # Content-SHA256
        content_to_sha256 = (
            "" if body is None or len(body.keys()) == 0 else json.dumps(body)
        )

        str_to_sign += (
            hashlib.sha256(content_to_sha256.encode(
                "utf8")).hexdigest().lower()
        )
        str_to_sign += "\n"

        # Header
        str_to_sign += "\n"

        # URL
        str_to_sign += path

        if params is not None and len(params.keys()) > 0:
            str_to_sign += "?"

            query_builder = ""
            params_keys = sorted(params.keys())

            for key in params_keys:
                query_builder += f"{key}={params[key]}&"
            str_to_sign += query_builder[:-1]

        # Sign
        t = int(time.time() * 1000)

        message = self.access_id
        if self.token_info is not None:
            message += "" if path.startswith(TO_B_TOKEN_API) else self.token_info.access_token
        message += str(t) + str_to_sign
        sign = (
            hmac.new(
                self.access_secret.encode("utf8"),
                msg=message.encode("utf8"),
                digestmod=hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )
        return sign, t

    def __refresh_access_token_if_need(self, path: str):
        if self.is_connect() is False:
            return

        if path.startswith(TO_B_TOKEN_API):
            return

        # should use refresh token?
        now = int(time.time() * 1000)
        expired_time = self.token_info.expire_time

        if expired_time - 60 * 1000 > now:  # 1min
            return

        if self.token_info.is_token_refreshing:
            return

        self.token_info.is_token_refreshing = True

        response = self.get(
            TO_B_REFRESH_TOKEN_API.format(self.token_info.refresh_token)
        )

        self.token_info = TuyaTokenInfo(response)

    def set_dev_channel(self, dev_channel: str):
        """Set dev channel."""
        self.dev_channel = dev_channel

    def connect(
        self
    ) -> Dict[str, Any]:
        """Connect to Tuya Cloud.

        Returns:
            response: connect response
        """
        response = self.get(TO_B_TOKEN_API, {"grant_type": 1})

        if not response["success"]:
            return response

        # Cache token info.
        self.token_info = TuyaTokenInfo(response)

        return response

    def is_connect(self) -> bool:
        """Is connect to tuya cloud."""
        return self.token_info is not None and len(self.token_info.access_token) > 0

    def __request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        self.__refresh_access_token_if_need(path)

        access_token = ""
        if self.token_info:
            access_token = self.token_info.access_token

        sign, t = self._calculate_sign(method, path, params, body)
        headers = {
            "client_id": self.access_id,
            "sign": sign,
            "sign_method": "HMAC-SHA256",
            "access_token": access_token,
            "t": str(t),
            "lang": self.lang,
        }

        headers["dev_lang"] = "python"
        headers["dev_version"] = VERSION
        headers["dev_channel"] = f"cloud_{self.dev_channel}"

        logger.debug(
            f"Request: method = {method}, \
                url = {self.endpoint + path},\
                params = {params},\
                body = {filter_logger(body)},\
                t = {int(time.time()*1000)}"
        )

        response = self.session.request(
            method, self.endpoint + path, params=params, json=body, headers=headers
        )

        if response.ok is False:
            logger.error(
                f"Response error: code={response.status_code}, body={response.body}"
            )
            return None

        result = response.json()

        logger.debug(
            f"Response: {json.dumps(filter_logger(result), ensure_ascii=False, indent=2)}"
        )

        if result.get("code", -1) == TUYA_ERROR_CODE_TOKEN_INVALID:
            self.token_info = None
            self.connect()

        return result

    def get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Http Get.

        Requests the server to return specified resources.

        Args:
            path (str): api path
            params (map): request parameter

        Returns:
            response: response body
        """
        return self.__request("GET", path, params, None)

    def post(
        self, path: str, body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Http Post.

        Requests the server to update specified resources.

        Args:
            path (str): api path
            body (map): request body

        Returns:
            response: response body
        """
        return self.__request("POST", path, None, body)

    def put(
        self, path: str, body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Http Put.

        Requires the server to perform specified operations.

        Args:
            path (str): api path
            body (map): request body

        Returns:
            response: response body
        """
        return self.__request("PUT", path, None, body)

    def delete(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Http Delete.

        Requires the server to delete specified resources.

        Args:
            path (str): api path
            params (map): request param

        Returns:
            response: response body
        """
        return self.__request("DELETE", path, params, None)
