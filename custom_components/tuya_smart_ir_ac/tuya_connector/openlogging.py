#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
from typing import Any

logger = logging.getLogger("custom_components.tuya_connector")

# Use a set for O(1) lookup time instead of a list O(n)
SENSITIVE_KEYS = {
    "access_token", "client_id", "ip", "lat", "link_id",
    "local_key", "lon", "password", "refresh_token", "uid"
}

MASK_STRING = "***"


def get_module_logger(module_name: str):
    return logging.getLogger(f"custom_components.tuya_connector.{module_name}")

def filter_logger(data: Any) -> Any:
    """
    Recursively filter log data to hide sensitive information.
    Builds a new sanitized data structure on the fly, avoiding slow deepcopy operations
    and ensuring nested sensitive keys are caught at any depth level.
    """
    if isinstance(data, dict):
        return {
            key: MASK_STRING if key in SENSITIVE_KEYS else filter_logger(value)
            for key, value in data.items()
        }
    
    if isinstance(data, list):
        return [filter_logger(item) for item in data]
    
    # Return base types (str, int, float, bool, None) as is
    return data