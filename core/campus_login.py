# -*- coding: utf-8 -*-
"""
校园网登录模块
"""

import re
import json
import os
import time
import urllib
from urllib import request
import requests
from typing import Optional, Tuple
from .config import CAMPUS_NET_CONFIG, NETWORK_CHECK_CONFIG, COMMON_CONFIG


def check_network_connection() -> bool:
    """检查网络连接状态"""
    timeout = NETWORK_CHECK_CONFIG["timeout"]

    for url in NETWORK_CHECK_CONFIG["check_targets"]:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status == 204:
                    return True
        except:
            continue
    return False


def auto_login(
    post_url: str = None, 
    get_url: str = None, 
    log_file_path: str = None,
    header_file_path: str = None,
    data_file_path: str = None
) -> Tuple[bool, Optional[str]]:
    """
    执行校园网自动登录
    
    Args:
        post_url: 登录 POST 请求地址
        get_url: 登录状态检测 GET 请求地址
        log_file_path: 日志文件路径
        header_file_path: 请求头文件路径
        data_file_path: 请求数据文件路径
        
    Returns:
        (success, error_msg) - success 表示是否登录成功，error_msg 是错误信息
    """
    if post_url is None:
        post_url = CAMPUS_NET_CONFIG["post_url"]
    if get_url is None:
        get_url = CAMPUS_NET_CONFIG["get_url"]
    if log_file_path is None:
        log_file_path = get_log_file_path()
    if header_file_path is None:
        header_file_path = get_post_header_path()
    if data_file_path is None:
        data_file_path = get_post_data_path()
    
    title = '未知状态'
    post_response = None
    get_status = None
    error_msg = None
    
    try:
        response = request.urlopen(get_url)
        html = response.read()
        res = re.findall('<title>(.*)</title>', html.decode(encoding="GBK", errors="strict"))
        
        if len(res) == 0:
            title = '未登录'
        else:
            title = res[0]
        
        if title == '登录成功':    
            print('当前状态为：已登陆成功！')
            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"[{time.ctime()}] 当前状态: 已登陆成功\n")
                log_file.write("-"*50 + "\n")
            return True, None
        else:
            print('当前状态为：未登录！')
            
            with open(header_file_path, 'r', encoding='utf-8') as f:
                header = json.load(f)
            with open(data_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            post_response = requests.post(post_url, data, headers=header)
            print(f"post请求状态码 {post_response.status_code}")
            
            school_web_login_url = get_url
            get_status = requests.get(school_web_login_url).status_code
            print(f"get请求状态码 {get_status}")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        error_msg = str(e)
        
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(f"[{time.ctime()}] 自动联网脚本开始运行\n")
        log_file.write(f"当前状态: {'已登陆成功' if title == '登录成功' else title}\n")
        if post_response is not None:
            log_file.write(f"POST状态码: {post_response.status_code}\n")
        if get_status is not None:
            log_file.write(f"GET状态码: {get_status}\n")
        if error_msg is not None:
            log_file.write(f"错误信息: {error_msg}\n")
        log_file.write("-"*50 + "\n")

    if os.path.getsize(log_file_path) > 1024:
        open(log_file_path, 'w').close()
        
    return title == '登录成功', error_msg


def ensure_internet_access() -> bool:
    """
    确保有网络访问能力，如果需要登录则自动登录
    
    Returns:
        bool: 是否有网络访问能力
    """
    if check_network_connection():
        return True
    
    success, error_msg = auto_login()
    return success


if __name__ == "__main__":
    import time
    
    if check_network_connection():
        print("网络已连接")
    else:
        print("网络未连接，尝试自动登录...")
        success, error = auto_login()
        if success:
            print("登录成功")
        else:
            print(f"登录失败: {error}")