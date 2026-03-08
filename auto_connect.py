# -*- coding: utf-8 -*-
"""
GUI 应用主程序
使用 Eel 库实现图形界面
"""

import eel
import os
import sys
import threading
import time
import subprocess

from core.wifi_manager import ensure_wifi_connected, is_connected
from core.campus_login import check_network_connection as check_network
from core.campus_login import auto_login as campus_auto_login
from core.config import (
    load_config as core_load_config,
    save_config as core_save_config,
    get_wifi_config, get_campus_net_config,
    get_personalize_config, is_first_run, set_first_run_done, get_common_config,
    get_post_header_path, get_post_data_path, get_post_header_js_path, get_post_data_js_path, get_log_file_path
)

def get_project_root():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

service_thread = None
service_running = False
interrupted = False

def setup_log_file():
    """确保日志文件存在"""
    log_file = get_log_file_path()
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    if not os.path.exists(log_file):
        open(log_file, 'w').close()


def log_message(message, msg_type='info'):
    """记录日志消息"""
    log_file = get_log_file_path()
    setup_log_file()
    with open(log_file, 'a', encoding='utf-8') as f:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] [{msg_type.upper()}] {message}\n")


def generate_post_data():
    """执行 JS 文件生成认证数据 (body.js 和 header.js)"""
    body_js_path = get_post_data_js_path()
    header_js_path = get_post_header_js_path()
    result = {'success': False, 'error': ''}
    
    try:
        node_available = subprocess.run(
            ['node', '--version'],
            capture_output=True,
            timeout=5
        )
        
        if node_available.returncode == 0:
            body_result = subprocess.run(
                ['node', body_js_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=get_common_config()["post_dir"]
            )
            
            if body_result.returncode != 0:
                result = {'success': False, 'error': 'body.js 执行失败: ' + body_result.stderr}
                return result
            
            header_result = subprocess.run(
                ['node', header_js_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=get_common_config()["post_dir"]
            )
            
            if header_result.returncode == 0:
                result = {'success': True, 'error': ''}
            else:
                result = {'success': False, 'error': 'header.js 执行失败: ' + header_result.stderr}
        else:
            result = {'success': False, 'error': 'Node.js 不可用'}
            
    except FileNotFoundError:
        result = {'success': False, 'error': '未找到 Node.js，请安装 Node.js'}
    except subprocess.TimeoutExpired:
        result = {'success': False, 'error': '执行超时'}
    except Exception as e:
        result = {'success': False, 'error': str(e)}
    
    return result


def auto_login():
    """执行校园网登录"""
    campus_config = get_campus_net_config()
    return campus_auto_login(
        post_url=campus_config.get('post_url', ''),
        get_url=campus_config.get('get_url', ''),
        log_file_path=get_log_file_path(),
        header_file_path=get_post_header_path(),
        data_file_path=get_post_data_path()
    )


def service_worker():
    """后台服务工作线程"""
    global service_running, interrupted
    
    wifi_config = get_wifi_config()
    target_ssid = wifi_config.get('target_ssid', '')
    personalize = get_personalize_config()
    interval_min = personalize.get('check_interval_min', 60)
    interval_max = personalize.get('check_interval_max', 80)
    
    while service_running:
        interrupted = False
        
        if is_connected(target_ssid):
            try:
                eel.update_status_py({
                    'wifi_connected': True,
                    'running': True
                })
            except:
                pass
            
            if check_network():
                try:
                    eel.update_status_py({
                        'network_ok': True,
                        'campus_logged': True,
                        'running': True
                    })
                except:
                    pass
            else:
                try:
                    eel.update_status_py({'network_ok': False})
                except:
                    pass
                success, error = auto_login()
                
                if success:
                    try:
                        eel.update_status_py({'campus_logged': True, 'network_ok': True})
                    except:
                        pass
                else:
                    if error and any(s in error for s in ['10051', '套接字', 'socket']):
                        log_message('网络连接存在问题，休眠1小时后重试...', 'warning')
                        for _ in range(3600):
                            if not service_running:
                                break
                            time.sleep(1)
                        continue
        else:
            try:
                eel.update_status_py({'wifi_connected': False})
            except:
                pass
            
            if check_network():
                try:
                    eel.update_status_py({'network_ok': True})
                except:
                    pass
            else:
                try:
                    eel.update_status_py({'network_ok': False})
                except:
                    pass
                
                if ensure_wifi_connected():
                    time.sleep(3)
                    
                    if check_network():
                        try:
                            eel.update_status_py({'network_ok': True, 'wifi_connected': True, 'campus_logged': True})
                        except:
                            pass
                    else:
                        success, error = auto_login()
                        if success:
                            try:
                                eel.update_status_py({'campus_logged': True, 'wifi_connected': True})
                            except:
                                pass
                else:
                    log_message('WiFi 连接失败', 'error')
        
        rand = time.time() % (interval_max - interval_min)
        sleep_time = interval_min + rand
        
        for _ in range(int(sleep_time)):
            if not service_running:
                break
            time.sleep(1)
    
    try:
        eel.update_status_py({'running': False})
    except:
        pass


@eel.expose
def init_app():
    """初始化应用"""
    setup_log_file()
    config = core_load_config()
    
    if config.get('first_run', True):
        try:
            eel.display_first_run()
        except:
            pass
    else:
        personalize = get_personalize_config()
        if personalize.get('auto_start') and personalize.get('run_hidden'):
            start_service()


@eel.expose
def start_service():
    """启动服务"""
    global service_thread, service_running
    
    if not service_running:
        service_running = True
        service_thread = threading.Thread(target=service_worker, daemon=True)
        service_thread.start()
        log_message('服务已启动', 'info')


@eel.expose
def stop_service():
    """停止服务"""
    global service_running
    service_running = False
    log_message('服务已停止', 'info')
    log_message('服务已停止', 'info')


@eel.expose
def get_status():
    """获取当前状态"""
    wifi_config = get_wifi_config()
    target_ssid = wifi_config.get('target_ssid', '')
    
    wifi_ok = is_connected(target_ssid)
    network_ok = check_network()
    
    return {
        'running': service_running,
        'wifi_connected': wifi_ok,
        'network_ok': network_ok,
        'campus_logged': wifi_ok and network_ok
    }


@eel.expose
def load_config_for_gui():
    """加载配置供前端使用"""
    config = core_load_config()
    wifi = config.get('wifi', {})
    personalize = config.get('personalize', {})
    
    return {
        'username': config.get('username', ''),
        'password': config.get('password', ''),
        'service': config.get('service', '联通'),
        'wifi_ssid': wifi.get('target_ssid', ''),
        'wifi_interface': wifi.get('interface_name', ''),
        'auto_start': personalize.get('auto_start', False),
        'run_hidden': personalize.get('run_hidden', False),
        'minimize_to_tray': personalize.get('minimize_to_tray', True),
        'interval_min': personalize.get('check_interval_min', 60),
        'interval_max': personalize.get('check_interval_max', 80),
        'first_run': config.get('first_run', True)
    }


@eel.expose
def save_config(config_data):
    """保存配置"""
    try:
        config = core_load_config()
        
        config['username'] = config_data.get('username', '')
        config['password'] = config_data.get('password', '')
        config['service'] = config_data.get('service', '联通')
        config['wifi'] = {
            'target_ssid': config_data.get('wifi_ssid', ''),
            'interface_name': config_data.get('wifi_interface', '')
        }
        
        if 'first_run' in config_data:
            config['first_run'] = config_data['first_run']
        
        core_save_config(config)
        
        if not config.get('first_run', True):
            set_first_run_done()
        
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def save_personalize(config_data):
    """保存个性化设置"""
    try:
        config = core_load_config()
        
        config['personalize'] = {
            'auto_start': config_data.get('auto_start', False),
            'run_hidden': config_data.get('run_hidden', False),
            'minimize_to_tray': config_data.get('minimize_to_tray', True),
            'check_interval_min': config_data.get('interval_min', 60),
            'check_interval_max': config_data.get('interval_max', 80)
        }
        
        core_save_config(config)
        
        setup_auto_start(config['personalize'].get('auto_start', False))
        
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def generate_post_data_py():
    """生成认证数据"""
    return generate_post_data()


def setup_auto_start(enable):
    """设置开机自启动"""
    import winreg
    
    app_path = sys.executable
    app_name = "AutoConnect"
    
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        
        winreg.CloseKey(key)
    except Exception:
        pass


def run_gui():
    """运行 GUI 应用"""
    gui_path = os.path.join(get_project_root(), 'gui')
    
    eel.init(gui_path, ['.html', '.js', '.css'])
    
    personalize = get_personalize_config()
    run_hidden = personalize.get('run_hidden', False)
    
    eel.start('index.html', 
               block=False,
               size=(900, 650))
    
    while True:
        eel.sleep(1)


if __name__ == "__main__":
    run_gui()