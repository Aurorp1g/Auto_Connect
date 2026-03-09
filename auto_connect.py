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
from urllib.parse import urlparse

import browser.custom_chrome

from core.wifi_manager import ensure_wifi_connected, is_connected
from core.campus_login import check_network_connection as check_network
from core.campus_login import auto_login as campus_auto_login
from core.config import (
    load_config as core_load_config,
    save_config as core_save_config,
    get_wifi_config, get_campus_net_config,
    get_personalize_config, is_first_run, set_first_run_done, get_common_config,
    get_post_header_path, get_post_data_path, get_post_header_js_path, get_post_data_js_path, get_log_file_path,
    get_default_rsa_config, get_default_post_url
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


def build_post_url(index_url: str) -> str:
    """根据index_url自动拼接post_url"""
    if not index_url:
        return get_default_post_url()
    
    try:
        parsed = urlparse(index_url)
        host = parsed.netloc
        post_url = f"{parsed.scheme}://{host}/eportal/InterFace.do?method=login"
        return post_url
    except Exception:
        return get_default_post_url()


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
    
    push_log_to_front(f'自动连接程序启动，目标 WiFi: {target_ssid}', 'info')
    
    while service_running:
        interrupted = False
        
        if is_connected(target_ssid):
            push_log_to_front(f'已连接到 [{target_ssid}]', 'success')
            try:
                eel.update_status_py({
                    'wifi_connected': True,
                    'running': True
                })
            except:
                pass
            
            if check_network():
                push_log_to_front('网络已连接', 'success')
                try:
                    eel.update_status_py({
                        'network_ok': True,
                        'campus_logged': True,
                        'running': True
                    })
                except:
                    pass
            else:
                push_log_to_front('WiFi 已连接但网络不可用，尝试校园网认证...', 'info')
                try:
                    eel.update_status_py({'network_ok': False})
                except:
                    pass
                login_success, error_msg = auto_login()
                
                if login_success:
                    push_log_to_front('校园网认证成功', 'success')
                    try:
                        eel.update_status_py({'campus_logged': True, 'network_ok': True})
                    except:
                        pass
                else:
                    if error_msg and any(s in error_msg for s in ['10051', '套接字', 'socket']):
                        push_log_to_front('网络连接存在问题，休眠1小时后重试...', 'warning')
                        log_message('网络连接存在问题，休眠1小时后重试...', 'warning')
                        for _ in range(3600):
                            if not service_running:
                                break
                            time.sleep(1)
                        continue
        else:
            push_log_to_front(f'未连接到 [{target_ssid}]，正在检测网络...', 'info')
            try:
                eel.update_status_py({'wifi_connected': False})
            except:
                pass
            
            if check_network():
                push_log_to_front('网络正常，保持当前状态', 'success')
                try:
                    eel.update_status_py({'network_ok': True})
                except:
                    pass
            else:
                push_log_to_front('网络不可用，尝试连接 WiFi...', 'info')
                try:
                    eel.update_status_py({'network_ok': False})
                except:
                    pass
                
                if ensure_wifi_connected():
                    push_log_to_front(f'WiFi [{target_ssid}] 连接命令已发送', 'info')
                    time.sleep(3)
                    
                    if check_network():
                        push_log_to_front('WiFi 已连接，网络正常', 'success')
                        try:
                            eel.update_status_py({'network_ok': True, 'wifi_connected': True, 'campus_logged': True})
                        except:
                            pass
                    else:
                        push_log_to_front('WiFi 已连接但需要校园网认证...', 'info')
                        login_success, error_msg = auto_login()
                        if login_success:
                            push_log_to_front('校园网认证成功', 'success')
                            try:
                                eel.update_status_py({'campus_logged': True, 'wifi_connected': True})
                            except:
                                pass
                        else:
                            if error_msg and any(s in error_msg for s in ['10051', '套接字', 'socket']):
                                push_log_to_front('网络连接存在问题，休眠1小时后重试...', 'warning')
                                for _ in range(3600):
                                    if not service_running:
                                        break
                                    time.sleep(1)
                                continue
                            push_log_to_front(f'校园网认证失败: {error_msg or "状态码不匹配"}', 'error')
                else:
                    push_log_to_front('WiFi 连接失败', 'error')
        
        rand = time.time() % (interval_max - interval_min)
        sleep_time = interval_min + rand
        
        push_log_to_front(f'休眠 {int(sleep_time)} 秒后再次检测', 'info')
        
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
    
    if is_first_run():
        try:
            eel.display_first_run()
        except:
            pass
    else:
        personalize = get_personalize_config()
        if personalize.get('auto_start') and personalize.get('run_hidden'):
            start_service()


def push_log_to_front(message: str, msg_type: str = 'info'):
    """推送日志到前端显示"""
    try:
        eel.push_log_message(message, msg_type)
    except:
        pass


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
        'index_url': config.get('index_url', ''),
        'auto_start': personalize.get('auto_start', False),
        'run_hidden': personalize.get('run_hidden', False),
        'minimize_to_tray': personalize.get('minimize_to_tray', True),
        'interval_min': personalize.get('check_interval_min', 60),
        'interval_max': personalize.get('check_interval_max', 80),
        'first_run': config.get('first_run', True)
    }


ALLOWED_RAW_FIELDS = ['RSA_exponent', 'RSA_modulus', 'post_url', 'index_url']


@eel.expose
def load_raw_config():
    """加载原始配置供开发选项使用"""
    return core_load_config()


@eel.expose
def save_raw_config(config_data):
    """保存原始配置（仅允许修改特定字段）"""
    try:
        config = core_load_config()
        
        for key in ALLOWED_RAW_FIELDS:
            if key in config_data:
                config[key] = config_data[key]
        
        core_save_config(config)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


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
        
        index_url = config_data.get('index_url', '').strip()
        config['index_url'] = index_url
        
        config['post_url'] = build_post_url(index_url)
        
        rsa_config = get_default_rsa_config()
        config['RSA_exponent'] = rsa_config['RSA_exponent']
        config['RSA_modulus'] = rsa_config['RSA_modulus']
        
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
        
        auto_start_result = setup_auto_start(config['personalize'].get('auto_start', False))
        
        if not auto_start_result:
            return {'success': False, 'error': '设置开机自启动失败'}
        
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
    import logging
    
    if getattr(sys, 'frozen', False):
        app_path = sys.executable
    elif sys.argv and sys.argv[0]:
        app_path = os.path.abspath(sys.argv[0])
    else:
        app_path = sys.executable
    app_name = "AutoConnect"
    
    log_message(f"设置开机自启动: enable={enable}, app_path={app_path}")
    
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    key = None
    success = False
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
        
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
            log_message(f"已添加注册表项: {app_name} -> {app_path}")
            
            try:
                verify_value, _ = winreg.QueryValueEx(key, app_name)
                log_message(f"验证读取: {verify_value}")
                if verify_value != app_path:
                    log_message(f"警告: 写入值与读取值不一致!", 'warning')
            except FileNotFoundError:
                log_message(f"错误: 写入后无法读取到注册表项!", 'error')
        else:
            try:
                winreg.DeleteValue(key, app_name)
                log_message(f"已删除注册表项: {app_name}")
            except FileNotFoundError:
                log_message(f"注册表项不存在: {app_name}", 'warning')
        success = True
    except Exception as e:
        log_message(f"设置开机自启动失败: {e}", 'error')
        logging.error(f"设置开机自启动失败: {e}")
    finally:
        if key:
            try:
                winreg.CloseKey(key)
            except Exception:
                pass
    
    return success


def run_gui():
    """运行 GUI 应用"""
    gui_path = os.path.join(get_project_root(), 'gui')
    
    eel.init(gui_path, ['.html', '.js', '.css'])
    
    personalize = get_personalize_config()
    run_hidden = personalize.get('run_hidden', False)
    minimize_to_tray = personalize.get('minimize_to_tray', True)
    
    if run_hidden:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    
    eel.start('index.html', 
               block=False,
               mode=False,
               size=(1200, 750),
               port=8888)
    
    time.sleep(1)
    browser.custom_chrome.start_chrome_for_eel(port=8888)
    
    if minimize_to_tray:
        threading.Thread(target=setup_system_tray, daemon=True).start()
    
    while True:
        eel.sleep(1)


def setup_system_tray():
    """设置系统托盘"""
    try:
        import pystray
        from PIL import Image, ImageDraw
        
        def create_image():
            width = 64
            height = 64
            image = Image.new('RGB', (width, height), color='#667eea')
            dc = ImageDraw.Draw(image)
            dc.rectangle([16, 16, 48, 48], fill='white')
            dc.ellipse([24, 24, 40, 40], fill='#667eea')
            return image
        
        def show_window(icon, item):
            try:
                eel.show_window()
            except:
                pass
        
        def exit_app(icon, item):
            global service_running
            service_running = False
            try:
                eel.stop_gui()
            except:
                pass
            icon.stop()
        
        menu = pystray.Menu(
            pystray.MenuItem('显示窗口', show_window),
            pystray.MenuItem('退出', exit_app)
        )
        
        icon = pystray.Icon(
            'AutoConnect',
            create_image(),
            '自动连接 - WiFi 校园网助手',
            menu
        )
        
        icon.run()
    except Exception as e:
        log_message(f'托盘功能启动失败: {e}', 'error')


if __name__ == "__main__":
    run_gui()