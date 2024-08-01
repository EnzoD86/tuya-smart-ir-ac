#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""Tuya iot logging."""

import logging
from typing import Any, Dict
import copy

logger = logging.getLogger('tuya iot')

default_handler = logging.StreamHandler()
default_handler.setFormatter(logging.Formatter(
    "[%(asctime)s] [tuya-%(module)s] %(message)s"
))

logger.addHandler(default_handler)
TUYA_LOGGER = logger

FILTER_LIST = ["access_token", "client_id", "ip", "lat", "link_id",
               "local_key", "lon", "password", "refresh_token", "uid"]

STAR = "***"


def filter_logger(result_info: Dict[str, Any]):
    """Filter log, hide sensitive info."""
    if result_info is None:
        return result_info
    filter_info_original = copy.deepcopy(result_info)
    if "result" in filter_info_original:
        filter_info = filter_info_original["result"]
    else:
        filter_info = filter_info_original
    if isinstance(filter_info, list):
        for item in filter_info:
            for filter_key in FILTER_LIST:
                if filter_key in item:
                    item[filter_key] = STAR

    elif isinstance(filter_info, dict):
        for filter_key in FILTER_LIST:
            if filter_key in filter_info:
                filter_info[filter_key] = STAR

    return filter_info_original
