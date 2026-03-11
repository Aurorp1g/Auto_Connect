# -*- coding: utf-8 -*-
"""
WiFi 连接模块
"""

import subprocess
import re
from typing import Optional, Tuple
from .config import get_wifi_config, COMMON_CONFIG


def run_netsh_command(args: list, timeout: int = None) -> Tuple[str, str, bool]:
    """
    执行 netsh 命令（隐藏窗口，防止弹出控制台）
    
    Returns:
        (stdout, stderr, success) - success 为 True 表示命令执行成功
    """
    if timeout is None:
        timeout = COMMON_CONFIG["command_timeout"]
    
    cmd = ["netsh"] + args
    
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        stdout = result.stdout
        stderr = result.stderr
        
        if '\x00' in stdout or '�' in stdout:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=timeout,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                stdout = result.stdout.decode('gbk', errors='ignore')
                stderr = result.stderr.decode('gbk', errors='ignore')
            except Exception:
                pass
        
        return stdout, stderr, result.returncode == 0
        
    except subprocess.TimeoutExpired:
        return "", f"命令执行超时 ({timeout}秒)", False
    except Exception as e:
        return "", str(e), False


def get_first_wlan_interface() -> Optional[str]:
    """自动检测第一个无线网卡接口名称（支持中英文系统）"""
    stdout, stderr, success = run_netsh_command(["wlan", "show", "interfaces"])
    
    if not success:
        print(f"获取网卡信息失败: {stderr}")
        return None
    
    pattern = r'(?:名称|Name)\s*:\s*(.+)'
    match = re.search(pattern, stdout, re.IGNORECASE)
    
    if match:
        interface_name = match.group(1).strip()
        if interface_name:
            return interface_name
    
    return None


def is_connected(target_ssid: str = None) -> bool:
    """
    检查当前是否已连接到目标 SSID
    
    Args:
        target_ssid: 目标 WiFi 名称，None 则使用配置中的默认 SSID
    """
    if target_ssid is None:
        target_ssid = get_wifi_config()["target_ssid"]
    
    stdout, _, success = run_netsh_command(["wlan", "show", "interfaces"])
    
    if not success:
        return False
    
    ssid_pattern = rf'SSID\s*:\s*{re.escape(target_ssid)}'
    ssid_found = re.search(ssid_pattern, stdout, re.IGNORECASE)
    
    if not ssid_found:
        return False
    
    state_pattern = r'(?:状态|State)\s*:\s*(?:已连接|connected)'
    state_connected = bool(re.search(state_pattern, stdout, re.IGNORECASE))

    return ssid_found is not None and state_connected


def connect_to_wifi(ssid: str = None, interface_name: str = None) -> bool:
    """
    连接到指定的 WiFi（无密码）
    
    Args:
        ssid: 目标 WiFi 名称，None 则使用配置中的默认 SSID
        interface_name: 网卡接口名，None 则自动检测
        
    Returns:
        bool: 命令是否发送成功（不代表连接成功建立）
    """
    if ssid is None:
        ssid = get_wifi_config()["target_ssid"]
    
    if not interface_name:
        wifi_config = get_wifi_config()
        if wifi_config["interface_name"]:
            interface_name = wifi_config["interface_name"]
        else:
            interface_name = get_first_wlan_interface()
            if not interface_name:
                print("错误: 无法自动检测无线网卡，请手动指定")
                return False
            print(f"检测到无线网卡: {interface_name}")
    
    args = ["wlan", "connect", f'name="{ssid}"']
    if interface_name:
        args.append(f'interface="{interface_name}"')
    
    print(f"正在连接 [{ssid}]...")
    stdout, stderr, success = run_netsh_command(
        args, 
        timeout=COMMON_CONFIG["connect_timeout"]
    )
    
    if not success:
        error_msg = stderr.lower()
        if "没有可用的配置文件" in error_msg or "profile" in error_msg and "not found" in error_msg:
            print(f"错误: WiFi [{ssid}] 没有配置文件。")
            print("提示: 对于无密码网络，需先手动连接一次让 Windows 保存配置，或提供 XML 配置文件。")
        else:
            print(f"连接失败: {stderr}")
        return False
    
    return True


def ensure_wifi_connected() -> bool:
    """
    确保已连接到目标 WiFi，如果未连接则尝试连接
    
    Returns:
        bool: 是否已连接或连接成功
    """
    target_ssid = get_wifi_config()["target_ssid"]
    
    if is_connected(target_ssid):
        print(f"已经连接到 [{target_ssid}]，无需重复连接")
        return True
    
    return connect_to_wifi(target_ssid)


if __name__ == "__main__":
    if ensure_wifi_connected():
        print("WiFi 连接成功")
    else:
        print("WiFi 连接失败")