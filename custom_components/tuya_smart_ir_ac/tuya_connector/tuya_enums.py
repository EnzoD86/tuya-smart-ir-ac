#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""Tuya iot enums."""

from enum import Enum


# class TuyaCloudOpenAPIEndpoint:
#     """Tuya Cloud Open API Endpoint."""

#     CHINA = "https://openapi.tuyacn.com"
#     AMERICA = "https://openapi.tuyaus.com"
#     AMERICA_AZURE = "https://openapi-ueaz.tuyaus.com"
#     EUROPE = "https://openapi.tuyaeu.com"
#     EUROPE_MS = "https://openapi-weaz.tuyaeu.com"
#     INDIA = "https://openapi.tuyain.com"


# class TuyaCloudPulsarWSEndpoint:
#     """Tuya Cloud Pulsar websocket Endpoint."""

#     CHINA = "wss://mqe.tuyacn.com:8285/"
#     AMERICA = "wss://mqe.tuyaus.com:8285/"
#     EUROPE = "wss://mqe.tuyaeu.com:8285/"
#     INDIA = "wss://mqe.tuyain.com:8285/"


class TuyaCloudPulsarTopic:
    """Tuya Cloud Pulsar Topic."""

    PROD = "event"
    TEST = "event-test"
