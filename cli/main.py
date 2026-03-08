# -*- coding: utf-8 -*-
"""
自动连接主程序
整合 WiFi 自动连接和校园网登录功能
"""

import signal
import time
import random
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.wifi_manager import ensure_wifi_connected, is_connected
from core.campus_login import check_network_connection as check_network
from core.campus_login import auto_login as campus_auto_login
from core.config import (
    get_wifi_config, get_campus_net_config, 
    get_personalize_config, get_common_config
)


interrupted = False
service_running = False


def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    global interrupted, service_running
    print("\n自动联网脚本将重新启动...")
    interrupted = True
    service_running = False


def sleep_with_interrupt(seconds: int) -> bool:
    """可中断的休眠函数
    
    Returns:
        True 表示被中断，False 表示正常完成
    """
    global interrupted
    for i in range(int(seconds)):
        if interrupted:
            return True
        time.sleep(1)
    return False


def auto_login():
    """执行校园网登录"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    common_config = get_common_config()
    campus_config = get_campus_net_config()
    header_file = os.path.join(project_root, 'data', 'post_header.json')
    data_file = os.path.join(project_root, 'data', 'post_data.json')
    log_file = common_config.get("log_file", "auto_connect.log")
    
    return campus_auto_login(
        post_url=campus_config.get('post_url', ''),
        get_url=campus_config.get('get_url', ''),
        log_file_path=log_file,
        header_file_path=header_file,
        data_file_path=data_file
    )


def ensure_log_file():
    """确保日志文件存在"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    common_config = get_common_config()
    log_file = common_config.get("log_file", "auto_connect.log")
    if not os.path.isabs(log_file):
        log_file = os.path.join(project_root, log_file)
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    if not os.path.exists(log_file):
        open(log_file, 'w').close()


def main():
    """主函数"""
    global interrupted, service_running
    
    signal.signal(signal.SIGINT, signal_handler)
    ensure_log_file()
    
    wifi_config = get_wifi_config()
    personalize_config = get_personalize_config()
    common_config = get_common_config()
    
    target_ssid = wifi_config.get('target_ssid', '')
    interval_min = personalize_config.get('check_interval_min', common_config.get('check_interval_min', 60))
    interval_max = personalize_config.get('check_interval_max', common_config.get('check_interval_max', 80))
    
    print(f"自动连接程序启动，目标 WiFi: {target_ssid}")
    service_running = True
    
    while service_running:
        interrupted = False
        
        if is_connected(target_ssid):
            print(f"已连接到 [{target_ssid}]")
            
            if check_network():
                print("网络已连接")
            else:
                print("WiFi 已连接但网络不可用，尝试校园网认证...")
                success, error = auto_login()
                
                if success:
                    print("校园网认证成功")
                elif error and any(s in error for s in ['10051', '套接字', 'socket']):
                    print("网络连接存在问题，休眠1小时后重试...")
                    if sleep_with_interrupt(3600):
                        continue
                else:
                    if sleep_with_interrupt(2):
                        continue
        else:
            print(f"未连接到 [{target_ssid}]")
            
            if check_network():
                print("网络正常，保持当前状态")
            else:
                print("网络不可用，尝试连接 WiFi...")
                if ensure_wifi_connected():
                    print(f"WiFi [{target_ssid}] 连接命令已发送")
                    time.sleep(3)
                    
                    if check_network():
                        print("WiFi 已连接，网络正常")
                    else:
                        print("WiFi 已连接但需要校园网认证...")
                        success, error = auto_login()
                        
                        if success:
                            print("校园网认证成功")
                        elif error and any(s in error for s in ['10051', '套接字', 'socket']):
                            print("网络连接存在问题，休眠1小时后重试...")
                            if sleep_with_interrupt(3600):
                                continue
                        else:
                            if sleep_with_interrupt(2):
                                continue
                else:
                    print("WiFi 连接失败")
            
            if sleep_with_interrupt(2):
                continue
        
        rand = random.uniform(0, interval_max - interval_min)
        sleep_time = interval_min + rand
        print(f"休眠 {int(sleep_time)} 秒")
        
        if sleep_with_interrupt(sleep_time):
            continue


if __name__ == "__main__":
    main()