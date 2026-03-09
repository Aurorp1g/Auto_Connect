# -*- coding: utf-8 -*-
"""
配置模块
从 data/config.json 加载配置
"""

import os
import json
from urllib.parse import urlparse


def get_config_path() -> str:
    """获取配置文件路径"""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "config.json"
    )


def load_config() -> dict:
    """加载配置文件"""
    config_path = get_config_path()
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    """保存配置文件"""
    config_path = get_config_path()
    config_dir = os.path.dirname(config_path)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def get_wifi_config() -> dict:
    """获取 WiFi 配置"""
    config = load_config()
    wifi_config = config.get("wifi", {})
    return {
        "target_ssid": wifi_config.get("target_ssid", ""),
        "interface_name": wifi_config.get("interface_name", ""),
    }


def get_campus_net_config() -> dict:
    """获取校园网配置"""
    config = load_config()
    post_url = config.get("post_url", "")
    index_url = config.get("index_url", "")
    
    get_url = extract_get_url(index_url)
    
    return {
        "post_url": post_url,
        "get_url": get_url,
    }


def get_personalize_config() -> dict:
    """获取个性化配置"""
    config = load_config()
    personalize = config.get("personalize", {})
    return {
        "auto_start": personalize.get("auto_start", False),
        "run_hidden": personalize.get("run_hidden", False),
        "minimize_to_tray": personalize.get("minimize_to_tray", True),
        "check_interval_min": personalize.get("check_interval_min", 60),
        "check_interval_max": personalize.get("check_interval_max", 80),
    }


def is_first_run() -> bool:
    """检查是否首次运行"""
    config = load_config()
    return config.get("first_run", True)


def set_first_run_done() -> None:
    """设置首次运行完成"""
    config = load_config()
    config["first_run"] = False
    save_config(config)


def extract_get_url(index_url: str) -> str:
    """从 index_url 中提取 get_url（基础 URL + 路径，不包含查询参数）"""
    if not index_url:
        return ""
    
    parsed = urlparse(index_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    return base_url


def get_network_check_config() -> dict:
    """获取网络检测配置"""
    return {
        "check_targets": [
            "http://connectivitycheck.gstatic.com/generate_204",
            "http://www.msftconnecttest.com/connecttest.txt",
            "http://connect.rom.miui.com/generate_204"
        ],
        "timeout": 8,
    }


def get_common_config() -> dict:
    """获取通用配置"""
    personalize = get_personalize_config()
    return {
        "command_timeout": 10,
        "connect_timeout": 20,
        "check_interval_min": personalize.get("check_interval_min", 60),
        "check_interval_max": personalize.get("check_interval_max", 80),
        "log_file": "./logs/auto_connect.log",
        "data_dir": "data",
        "post_dir": "post"
    }


DEFAULT_RSA_EXPONENT = "10001"
DEFAULT_RSA_MODULUS = "94dd2a8675fb779e6b9f7103698634cd400f27a154afa67af6166a43fc26417222a79506d34cacc7641946abda1785b7acf9910ad6a0978c91ec84d40b71d2891379af19ffb333e7517e390bd26ac312fe940c340466b4a5d4af1d65c3b5944078f96a1a51a5a53e4bc302818b7c9f63c4a1b07bd7d874cef1c3d4b2f5eb7871"


def get_default_rsa_config() -> dict:
    """获取默认RSA加密配置（锐捷校园网）"""
    return {
        "RSA_exponent": DEFAULT_RSA_EXPONENT,
        "RSA_modulus": DEFAULT_RSA_MODULUS
    }


def get_default_post_url() -> str:
    """获取默认的认证POST URL（锐捷校园网通用格式）"""
    return "http://10.10.9.4/eportal/InterFace.do?method=login"


def get_post_header_path() -> str:
    """获取请求头文件路径"""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        COMMON_CONFIG["data_dir"], 
        "post_header.json"
    )


def get_post_data_path() -> str:
    """获取请求数据文件路径"""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        COMMON_CONFIG["data_dir"], 
        "post_data.json"
    )


def get_log_file_path() -> str:
    """获取日志文件路径"""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        COMMON_CONFIG["log_file"]
    )

def get_post_header_js_path() -> str:
    """获取请求头 JavaScript 文件路径"""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        COMMON_CONFIG["post_dir"], 
        "header.js"
    )


def get_post_data_js_path() -> str:
    """获取请求数据 JavaScript 文件路径"""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        COMMON_CONFIG["post_dir"], 
        "body.js"
    )


WIFI_CONFIG = get_wifi_config()
CAMPUS_NET_CONFIG = get_campus_net_config()
NETWORK_CHECK_CONFIG = get_network_check_config()
PERSONALIZE_CONFIG = get_personalize_config()
COMMON_CONFIG = get_common_config()
POST_HEADER_PATH = get_post_header_path()
POST_DATA_PATH = get_post_data_path()
POST_HEADER_JS_PATH = get_post_header_js_path()
POST_DATA_JS_PATH = get_post_data_js_path()