# -*- coding: utf-8 -*-
"""
Core 模块
"""

from .config import (
    load_config, save_config, 
    get_wifi_config, get_campus_net_config, get_personalize_config,
    is_first_run, set_first_run_done,
    get_network_check_config, get_common_config,
    WIFI_CONFIG, CAMPUS_NET_CONFIG, PERSONALIZE_CONFIG, COMMON_CONFIG
)