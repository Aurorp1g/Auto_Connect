# -*- coding: utf-8 -*-
"""
GUI 应用主程序
使用 Eel 库实现图形界面
"""

import eel
import os
import socket
import sys
import threading
import time
import subprocess
import urllib.request
from datetime import datetime, timedelta
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


def get_node_path():
    """获取内置 Node.js 可执行文件路径"""
    base_path = get_project_root()
    if sys.platform == 'win32':
        node_path = os.path.join(base_path, 'node', 'node.exe')
    else:
        node_path = os.path.join(base_path, 'node', 'node')
    
    if os.path.exists(node_path):
        return node_path
    return None

service_thread = None
service_running = False
handling = False

chrome_process = None
browser_visible = False
browser_hiding = False  # True 表示正在隐藏浏览器（不退出程序）
tray_icon = None  # 托盘图标对象
app_initialized = False  # 应用是否已初始化
remote_service = False  # True 表示后台服务运行在无头进程（SYSTEM 会话），当前进程仅作托盘遥控
remote_running = False  # 后台服务的运行状态（远程模式下由 STATUS 命令同步）

# 网络状态缓存（由后台线程刷新，避免阻塞 eel 事件循环）
network_status_cache = {'network_ok': False, 'last_update': 0}

failed_count = 0
MAX_FAILED_COUNT = 5
SLEEP_DURATION = 1800  # 30分钟
REMOTE_CONTROL_PORT = 8890  # 无头后台服务本地控制端口（供用户会话托盘进程遥控）

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
    # 使用绝对路径作为子进程工作目录，避免开机自启时工作目录为 System32 导致相对路径失效
    post_dir = os.path.join(get_project_root(), get_common_config()["post_dir"])
    result = {'success': False, 'error': ''}
    
    try:
        startupinfo = None
        creationflags = 0
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW
        
        node_exe = get_node_path()
        if node_exe is None:
            node_exe = 'node'
        
        body_result = subprocess.run(
            [node_exe, body_js_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=post_dir,
            startupinfo=startupinfo,
            creationflags=creationflags
        )
        
        if body_result.returncode != 0:
            result = {'success': False, 'error': 'body.js 执行失败: ' + body_result.stderr}
            return result
        
        header_result = subprocess.run(
            [node_exe, header_js_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=post_dir,
            startupinfo=startupinfo,
            creationflags=creationflags
        )
        
        if header_result.returncode == 0:
            result = {'success': True, 'error': ''}
        else:
            result = {'success': False, 'error': 'header.js 执行失败: ' + header_result.stderr}
            
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


def handle_status_change_inner(wifi_connected: bool, network_ok: bool):
    """处理状态变化的内层函数（只有状态改变才推送）"""
    global last_wifi_status, last_network_status
    
    wifi_changed = wifi_connected != last_wifi_status
    network_changed = network_ok != last_network_status
    
    last_wifi_status = wifi_connected
    last_network_status = network_ok
    
    wifi_config = get_wifi_config()
    target_ssid = wifi_config.get('target_ssid', '')


    if network_ok:
        if network_changed:
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
        if wifi_connected:
            if network_ok:
                if network_changed:
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
                if network_changed:
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
                    last_network_status = True
                    
                    time.sleep(2)
                    network_still_ok = check_network()
                    
                    if not network_still_ok:
                        push_log_to_front('认证成功但网络仍不可用，可能是服务已终止', 'warning')
                        last_network_status = False
                else:
                    if error_msg and any(s in error_msg for s in ['10051', '套接字', 'socket']):
                        push_log_to_front('网络连接存在问题', 'warning')
                    push_log_to_front(f'校园网认证失败: {error_msg or "状态码不匹配"}', 'error')
        else:
            if wifi_changed:
                push_log_to_front(f'未连接到 [{target_ssid}]', 'info')
                try:
                    eel.update_status_py({'wifi_connected': False})
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
                    last_wifi_status = True
                    last_network_status = True
                else:
                    push_log_to_front('WiFi 已连接但需要校园网认证...', 'info')
                    login_success, error_msg = auto_login()
                    if login_success:
                        push_log_to_front('校园网认证成功', 'success')
                        try:
                            eel.update_status_py({'campus_logged': True, 'wifi_connected': True})
                        except:
                            pass
                        last_wifi_status = True
                        
                        time.sleep(2)
                        network_still_ok = check_network()
                        
                        if network_still_ok:
                            last_network_status = True
                            push_log_to_front('网络已连通', 'success')
                        else:
                            push_log_to_front('认证成功但网络仍不可用，可能是服务已终止', 'warning')
                    else:
                        push_log_to_front(f'校园网认证失败: {error_msg or "状态码不匹配"}', 'error')
            else:
                push_log_to_front('WiFi 连接失败', 'error')


def handle_status_change():
    """处理状态变化（兼容性保留）"""
    handle_status_change_inner(last_wifi_status, last_network_status)


def service_worker():
    """后台服务工作线程 - 自主轮询检测网络状态"""
    global service_running, failed_count, last_network_status
    
    wifi_config = get_wifi_config()
    target_ssid = wifi_config.get('target_ssid', '')
    
    push_log_to_front(f'自动连接程序启动，目标 WiFi: {target_ssid}', 'info')
    push_log_to_front('服务已启动，开始监控网络状态...', 'info')
    
    CHECK_INTERVAL = 2  # 每2秒检测一次
    
    while service_running:
        network_ok = check_network()
        
        if network_ok:
            if not last_network_status:
                push_log_to_front('网络已连接', 'success')
                try:
                    eel.update_status_py({'network_ok': True, 'campus_logged': True})
                except:
                    pass
            last_network_status = True
            failed_count = 0
        else:
            wifi_connected = is_connected(target_ssid)
            handle_status_change_inner(wifi_connected, network_ok)
            
            if last_wifi_status and last_network_status:
                failed_count = 0
            else:
                failed_count += 1
                if failed_count >= MAX_FAILED_COUNT:
                    sleep_duration = calculate_sleep_duration()
                    sleep_minutes = sleep_duration // 60
                    push_log_to_front(f'连续{MAX_FAILED_COUNT}次处理失败，休眠{sleep_minutes}分钟后重试...', 'warning')
                    try:
                        eel.on_backend_sleep(sleep_duration)
                    except:
                        pass
                    
                    for _ in range(sleep_duration):
                        if not service_running:
                            break
                        time.sleep(1)
                    
                    failed_count = 0
                    push_log_to_front('休眠结束，重新开始工作...', 'info')
        
        for _ in range(CHECK_INTERVAL):
            if not service_running:
                break
            time.sleep(1)
    
    try:
        eel.update_status_py({'running': False})
    except:
        pass


def calculate_sleep_duration():
    """计算休眠时长（考虑服务禁用时间段）"""
    personalize = get_personalize_config()
    disable_start = personalize.get('service_disable_start', '')
    disable_end = personalize.get('service_disable_end', '')
    
    if not disable_start or not disable_end:
        return SLEEP_DURATION
    
    try:
        now = datetime.now()
        current_time = now.time()
        
        start_time = datetime.strptime(disable_start, '%H:%M').time()
        end_time = datetime.strptime(disable_end, '%H:%M').time()
        
        if start_time <= end_time:
            in_range = start_time <= current_time <= end_time
        else:
            in_range = current_time >= start_time or current_time <= end_time
        
        if in_range:
            if current_time < end_time:
                end_datetime = datetime.combine(now.date(), end_time)
            else:
                end_datetime = datetime.combine(now.date() + timedelta(days=1), end_time)
            
            sleep_seconds = int((end_datetime - now).total_seconds())
            return max(sleep_seconds, 60)
        else:
            return SLEEP_DURATION
            
    except Exception:
        return SLEEP_DURATION


@eel.expose
def init_app():
    """初始化应用"""
    global app_initialized, remote_service, remote_running
    setup_log_file()
    
    if not app_initialized:
        app_initialized = True
        tray_only = '--tray-only' in sys.argv
        # 检测无头后台服务（SYSTEM 会话）是否在运行，若在则进入远程控制模式，避免重复启动服务
        # 无头服务可能仍在初始化控制服务器，短暂重试等待
        resp = None
        for _ in range(6):
            resp = send_remote_command('STATUS', timeout=1)
            if resp is not None:
                break
            time.sleep(0.5)
        if resp is not None:
            remote_service = True
            remote_running = (resp == 'RUNNING')
            log_message('检测到后台无头服务，进入远程控制模式', 'info')
        elif tray_only:
            # 纯托盘遥控进程：即使暂未连上后台服务，也保持远程模式，避免在本地重复启动服务
            remote_service = True
            remote_running = False
            log_message('进入托盘遥控模式（等待后台服务就绪）', 'warning')
        if is_first_run():
            try:
                eel.display_first_run()
            except:
                pass
        else:
            personalize = get_personalize_config()
            if personalize.get('auto_start') and not remote_service and not tray_only:
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
    global service_thread, service_running, remote_running
    
    if remote_service:
        resp = send_remote_command('START')
        if resp == 'OK':
            remote_running = True
            log_message('后台服务已启动', 'info')
        else:
            log_message('后台服务启动失败：无法连接后台服务', 'error')
        return
    
    if not service_running:
        service_running = True
        service_thread = threading.Thread(target=service_worker, daemon=True)
        service_thread.start()
        log_message('服务已启动', 'info')


@eel.expose
def stop_service():
    """停止服务"""
    global service_running, remote_running
    
    if remote_service:
        resp = send_remote_command('STOP')
        if resp == 'OK':
            remote_running = False
            log_message('后台服务已停止', 'info')
        else:
            log_message('后台服务停止失败：无法连接后台服务', 'error')
        return
    
    service_running = False
    log_message('服务已停止', 'info')


@eel.expose
def get_status():
    """获取当前状态（轻量级检测）"""
    wifi_config = get_wifi_config()
    target_ssid = wifi_config.get('target_ssid', '')
    
    wifi_ok = is_connected(target_ssid)
    
    # 直接读取缓存，不在 eel 请求处理线程中做阻塞的网络探测
    network_ok = network_status_cache.get('network_ok', False)
    
    running = remote_running if remote_service else service_running
    
    return {
        'running': running,
        'wifi_connected': wifi_ok,
        'network_ok': network_ok,
        'campus_logged': wifi_ok and network_ok
    }


def _network_status_monitor():
    """后台线程：定期刷新网络状态，避免阻塞 eel 事件循环"""
    while True:
        try:
            network_status_cache['network_ok'] = check_network()
            network_status_cache['last_update'] = time.time()
        except Exception:
            pass
        time.sleep(2)


last_wifi_status = False
last_network_status = False

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
        'minimize_to_tray': personalize.get('minimize_to_tray', False),
        'service_disable_start': personalize.get('service_disable_start', ''),
        'service_disable_end': personalize.get('service_disable_end', ''),
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
            'minimize_to_tray': config_data.get('minimize_to_tray', False),
            'service_disable_start': config_data.get('service_disable_start', ''),
            'service_disable_end': config_data.get('service_disable_end', '')
        }
        
        core_save_config(config)
        
        auto_start_result = setup_auto_start(config['personalize'].get('auto_start', False))
        
        if not auto_start_result:
            return {'success': False, 'error': '设置开机自启动失败'}
        
        # 如果开启了最小化到托盘但托盘还没创建，则创建托盘
        if config['personalize'].get('minimize_to_tray') and tray_icon is None:
            threading.Thread(target=setup_system_tray, daemon=True).start()
        
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def generate_post_data_py():
    """生成认证数据"""
    result = generate_post_data()
    if not result.get('success'):
        log_message(f"认证数据生成失败: {result.get('error')}", 'error')
    return result


def is_admin():
    """判断当前进程是否已提升为管理员权限"""
    if sys.platform != 'win32':
        return True
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_elevated(args):
    """以管理员权限重新启动当前程序，args 为附加命令行参数列表（返回 True 表示已成功触发 UAC 提升）"""
    import ctypes
    if getattr(sys, 'frozen', False):
        exe = sys.executable
        params = ' '.join(args)
    else:
        exe = sys.executable
        script = os.path.abspath(sys.argv[0])
        params = f'"{script}" ' + ' '.join(args)
    try:
        # runas 触发 UAC 提权；show=0 隐藏提权后进程的窗口
        result = ctypes.windll.shell32.ShellExecuteW(None, 'runas', exe, params, None, 0)
        return result > 32
    except Exception as e:
        log_message(f'请求管理员权限失败: {e}', 'error')
        return False


def apply_auto_start_task(enable):
    """注册/删除开机自启计划任务（需在已提权进程中调用）

    注册两个任务：
    1) AutoConnect       —— 启动时、SYSTEM 账户、无头后台服务（登录前运行）
    2) AutoConnectTray   —— 用户登录时、当前用户、仅托盘遥控进程（登录后显示最小化托盘）
    """
    import subprocess
    task_name = 'AutoConnect'
    tray_task_name = 'AutoConnectTray'
    if getattr(sys, 'frozen', False):
        app_path = sys.executable
    else:
        app_path = os.path.abspath(sys.argv[0])
    ps_exe = app_path.replace("'", "''")

    if enable:
        ps_script = (
            # 主任务：启动时 SYSTEM 无头服务
            "$a1 = New-ScheduledTaskAction -Execute '%s' -Argument '--headless'; "
            "$t1 = New-ScheduledTaskTrigger -AtStartup; "
            "$p1 = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest; "
            "$s1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero); "
            "Register-ScheduledTask -TaskName '%s' -Action $a1 -Trigger $t1 -Principal $p1 -Settings $s1 -Force | Out-Null; "
            # 托盘任务：用户登录时，当前用户，仅托盘遥控
            "$a2 = New-ScheduledTaskAction -Execute '%s' -Argument '--tray-only'; "
            "$t2 = New-ScheduledTaskTrigger -AtLogOn; "
            "$p2 = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest; "
            "$s2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero); "
            "Register-ScheduledTask -TaskName '%s' -Action $a2 -Trigger $t2 -Principal $p2 -Settings $s2 -Force | Out-Null; "
            "$c1 = Get-ScheduledTask -TaskName '%s' -ErrorAction SilentlyContinue; "
            "$c2 = Get-ScheduledTask -TaskName '%s' -ErrorAction SilentlyContinue; "
            "if ($c1 -and $c2) { Write-Output ('VERIFY_OK:' + $c1.State + ',' + $c2.State) } else { Write-Output 'VERIFY_FAIL'; exit 1 }"
        ) % (ps_exe, task_name, ps_exe, tray_task_name, task_name, tray_task_name)
    else:
        ps_script = (
            "$r1 = Get-ScheduledTask -TaskName '%s' -ErrorAction SilentlyContinue; "
            "$r2 = Get-ScheduledTask -TaskName '%s' -ErrorAction SilentlyContinue; "
            "if ($r1) { Unregister-ScheduledTask -TaskName '%s' -Confirm:$false | Out-Null; Write-Output 'DELETED_MAIN' } "
            "if ($r2) { Unregister-ScheduledTask -TaskName '%s' -Confirm:$false | Out-Null; Write-Output 'DELETED_TRAY' } "
            "if (-not $r1 -and -not $r2) { Write-Output 'NOT_FOUND' }"
        ) % (task_name, tray_task_name, task_name, tray_task_name)

    try:
        startupinfo = None
        creationflags = 0
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True, text=True, errors='replace',
            startupinfo=startupinfo, creationflags=creationflags
        )
        output = (result.stdout or '').strip()
        if result.returncode != 0:
            detail = output or (result.stderr or '').strip()
            log_message(f'{"注册" if enable else "删除"}开机自启计划任务失败: {detail}', 'error')
            return False

        if enable:
            log_message(f'已注册开机自启计划任务: {task_name} + {tray_task_name}（{output}）', 'info')
            # 清理旧的登录自启注册表项，避免与计划任务重复启动
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                try:
                    winreg.DeleteValue(key, 'AutoConnect')
                    log_message('已清理旧的登录自启注册表项', 'info')
                except FileNotFoundError:
                    pass
                winreg.CloseKey(key)
            except Exception:
                pass
        else:
            log_message(f'已删除开机自启计划任务: {task_name} + {tray_task_name}（{output}）', 'info')
        return True
    except Exception as e:
        log_message(f'计划任务操作异常: {e}', 'error')
        return False


def setup_auto_start(enable):
    """设置开机自启动：优先走计划任务（登录前启动），需要管理员权限时自动请求 UAC 提升"""
    if sys.platform != 'win32':
        return True

    log_message(f"设置开机自启动: enable={enable}")

    if is_admin():
        return apply_auto_start_task(enable)

    flag = '--apply-autostart' if enable else '--remove-autostart'
    log_message(f'需要管理员权限，正在请求 UAC 提权以{"开启" if enable else "关闭"}开机自启...', 'info')
    return run_elevated([flag])


def activate_browser_window():
    """激活（显示并置顶）浏览器窗口"""
    try:
        import ctypes
        from ctypes import wintypes
        
        user32 = ctypes.windll.user32
        
        def enum_windows_callback(hwnd, lParam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if 'Chrome' in title or 'Auto_Connect' in title or 'eel' in title:
                        user32.ShowWindow(hwnd, 9)
                        user32.SetForegroundWindow(hwnd)
            return True
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
        return True
    except Exception:
        return False


def launch_browser():
    """启动浏览器窗口"""
    global chrome_process, browser_visible
    
    if chrome_process is None or chrome_process.poll() is not None:
        chrome_process = browser.custom_chrome.start_chrome_for_eel(port=8888, hidden=False)
        browser_visible = True
        log_message('浏览器窗口已启动', 'info')
        return True
    else:
        if activate_browser_window():
            browser_visible = True
            return True
    return False


def refresh_tray_menu():
    """刷新托盘菜单"""
    global tray_icon, browser_visible
    
    if tray_icon is None:
        return
    
    try:
        import pystray
        
        def do_show(icon, item):
            global browser_visible
            if launch_browser():
                browser_visible = True
                icon.menu = get_tray_menu()
        
        def do_hide(icon, item):
            global browser_visible
            hide_browser()
            browser_visible = False
            icon.menu = get_tray_menu()
        
        def do_exit(icon, item):
            global service_running, chrome_process
            service_running = False
            if chrome_process is not None:
                chrome_process.terminate()
                chrome_process = None
            try:
                eel.stop()
            except:
                pass
            icon.stop()
            import os
            os._exit(0)
        
        tray_icon.menu = get_tray_menu()
    except Exception as e:
        log_message(f'刷新托盘菜单失败: {e}', 'error')


def get_tray_menu():
    """获取托盘菜单"""
    import pystray
    
    def do_show(icon, item):
        global browser_visible
        if launch_browser():
            browser_visible = True
            icon.menu = get_tray_menu()

    def do_hide(icon, item):
        global browser_visible
        hide_browser()
        browser_visible = False
        icon.menu = get_tray_menu()

    def do_exit(icon, item):
        global service_running, chrome_process
        if remote_service:
            send_remote_command('EXIT')
        else:
            service_running = False
        if chrome_process is not None:
            chrome_process.terminate()
            chrome_process = None
        try:
            eel.stop()
        except:
            pass
        icon.stop()
        import os
        os._exit(0)

    def do_stop(icon, item):
        global service_running, remote_running
        if remote_service:
            resp = send_remote_command('STOP')
            if resp == 'OK':
                remote_running = False
                log_message('后台服务已停止', 'info')
            else:
                log_message('后台服务停止失败：无法连接后台服务', 'error')
                try:
                    icon.notify('无法连接后台服务，可能已被关闭', '停止失败')
                except Exception:
                    pass
        else:
            if service_running:
                service_running = False
                log_message('服务已停止', 'info')
                push_log_to_front('自动连接服务已停止', 'warning')
        icon.menu = get_tray_menu()

    def do_start(icon, item):
        global remote_running
        if remote_service:
            resp = send_remote_command('START')
            if resp == 'OK':
                remote_running = True
                log_message('后台服务已启动', 'info')
            else:
                log_message('后台服务启动失败：无法连接后台服务', 'error')
                try:
                    icon.notify('无法连接后台服务，可能已被关闭', '启动失败')
                except Exception:
                    pass
        else:
            start_service()
            log_message('服务已启动', 'info')
        icon.menu = get_tray_menu()

    def do_restart(icon, item):
        global service_running, remote_running
        if remote_service:
            resp = send_remote_command('RESTART')
            if resp == 'OK':
                remote_running = True
                log_message('后台服务已重启', 'info')
            else:
                log_message('后台服务重启失败：无法连接后台服务', 'error')
                try:
                    icon.notify('无法连接后台服务，可能已被关闭', '重启失败')
                except Exception:
                    pass
        else:
            if service_running:
                service_running = False
                log_message('服务已停止', 'info')
            # 等待旧服务线程退出，避免与重启后的新线程重叠
            time.sleep(1)
            start_service()
            log_message('服务已重启', 'info')
            push_log_to_front('自动连接服务已重启', 'info')
        icon.menu = get_tray_menu()

    running = remote_running if remote_service else service_running
    
    return pystray.Menu(
        pystray.MenuItem('显示窗口', do_show, visible=not browser_visible),
        pystray.MenuItem('隐藏窗口', do_hide, visible=browser_visible),
        pystray.MenuItem('停止服务', do_stop, visible=running),
        pystray.MenuItem('启动服务', do_start, visible=not running),
        pystray.MenuItem('重启服务', do_restart, visible=running),
        pystray.MenuItem('退出', do_exit)
    )


def hide_browser():
    """隐藏浏览器窗口"""
    global chrome_process, browser_visible, browser_hiding
    
    browser_hiding = True
    
    if chrome_process is not None:
        chrome_process.terminate()
        chrome_process = None
        time.sleep(0.5)
    
    browser_visible = False
    browser_hiding = False
    log_message('浏览器窗口已隐藏', 'info')


def send_remote_command(cmd, timeout=3):
    """向无头后台服务发送控制命令，返回响应字符串；连接失败返回 None"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(('127.0.0.1', REMOTE_CONTROL_PORT))
        s.sendall(cmd.encode('utf-8'))
        data = s.recv(1024).decode('utf-8').strip()
        s.close()
        return data
    except Exception:
        return None


def start_headless_control_server():
    """无头模式下的本地控制服务器，供用户会话的托盘进程远程查询/控制后台服务"""
    try:
        ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ctrl_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ctrl_sock.bind(('127.0.0.1', REMOTE_CONTROL_PORT))
        ctrl_sock.listen(5)
        ctrl_sock.settimeout(2)
        while True:
            try:
                conn, addr = ctrl_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                data = conn.recv(1024).decode('utf-8').strip()
                cmd = data.upper()
                if cmd == 'STATUS':
                    conn.sendall(('RUNNING' if service_running else 'STOPPED').encode('utf-8'))
                elif cmd == 'STOP':
                    stop_service()
                    conn.sendall(b'OK')
                elif cmd == 'START':
                    start_service()
                    conn.sendall(b'OK')
                elif cmd == 'RESTART':
                    stop_service()
                    time.sleep(1)
                    start_service()
                    conn.sendall(b'OK')
                elif cmd == 'EXIT':
                    conn.sendall(b'OK')
                    try:
                        conn.close()
                    except Exception:
                        pass
                    import os
                    os._exit(0)
                else:
                    conn.sendall(b'UNKNOWN')
            except Exception:
                pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        try:
            ctrl_sock.close()
        except Exception:
            pass
    except Exception as e:
        log_message(f'无头控制服务器启动失败: {e}', 'error')


def _acquire_single_instance_mutex():
    """获取跨会话单实例互斥体，防止计划任务重复启动无头服务"""
    if sys.platform != 'win32':
        return True, None
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.CreateMutexW(None, False, "Global\\AutoConnect_Headless")
        if not handle:
            return True, None
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(handle)
            return False, None
        return True, handle
    except Exception:
        return True, None


def run_headless():
    """无头模式：不加载 GUI/托盘/浏览器，直接运行后台连接服务（供系统启动时计划任务调用）"""
    setup_log_file()
    log_message('无头模式启动（无 GUI，登录前运行）', 'info')

    held, handle = _acquire_single_instance_mutex()
    if not held:
        log_message('已有无头实例在运行，本实例退出', 'warning')
        return

    try:
        start_service()
        # 启动本地控制服务器，供用户会话的托盘进程远程查询/控制
        threading.Thread(target=start_headless_control_server, daemon=True).start()
        # 阻塞主线程，保持进程常驻（服务停止/重启由控制服务器命令驱动）
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if handle is not None:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(handle)
            except Exception:
                pass


def run_gui():
    """运行 GUI 应用"""
    gui_path = os.path.join(get_project_root(), 'gui')
    
    eel.init(gui_path, ['.html', '.js', '.css'])
    
    hidden_mode = '--hidden' in sys.argv or '--tray-only' in sys.argv
    
    init_app()
    
    # 启动后台网络状态监控线程
    threading.Thread(target=_network_status_monitor, daemon=True).start()
    
    def start_command_server():
        """启动命令服务器，用于接收来自其他实例的命令"""
        try:
            cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cmd_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            cmd_sock.bind(('localhost', 8889))
            cmd_sock.listen(1)
            
            while True:
                try:
                    conn, addr = cmd_sock.accept()
                    data = conn.recv(1024).decode('utf-8')
                    conn.close()
                    
                    if data == "SHOW_WINDOW":
                        launch_browser()
                except Exception:
                    pass
        except Exception:
            pass
    
    threading.Thread(target=start_command_server, daemon=True).start()
    
    def browser_close_callback(page, sockets):
        """浏览器关闭时的回调"""
        global browser_hiding, chrome_process, browser_visible, tray_icon
        
        if browser_hiding:
            return
        
        personalize = get_personalize_config()
        minimize_to_tray = personalize.get('minimize_to_tray', False)
        
        if minimize_to_tray:
            browser_hiding = True
            if chrome_process is not None:
                chrome_process.terminate()
                chrome_process = None
            browser_visible = False
            refresh_tray_menu()
            time.sleep(0.5)
            browser_hiding = False
            return
        
        import os
        os._exit(0)
    
    icon_path = os.path.join(get_project_root(), 'gui', 'favicon.ico')
    cmdline_args = ['--disable-http-cache']
    if os.path.exists(icon_path):
        cmdline_args.append('--icon=' + icon_path)
    
    eel.start('index.html', 
               block=False,
               mode=False,
               size=(1200, 750),
               port=8888,
               close_callback=browser_close_callback,
               cmdline_args=cmdline_args)
    
    personalize = get_personalize_config()
    minimize_to_tray = personalize.get('minimize_to_tray', False)
    
    # hidden 模式始终创建托盘，非 hidden 模式根据设置决定
    if hidden_mode or minimize_to_tray:
        threading.Thread(target=setup_system_tray, daemon=True).start()
    
    if not hidden_mode:
        launch_browser()
    
    while True:
        try:
            eel.sleep(1)
        except KeyboardInterrupt:
            break
        except SystemExit:
            continue
        except Exception:
            pass
        
        try:
            global chrome_process
            if chrome_process is not None:
                if chrome_process.poll() is not None:
                    chrome_process = None
                    global browser_visible
                    browser_visible = False
        except Exception:
            pass


def setup_system_tray():
    """设置系统托盘"""
    try:
        import pystray
        from PIL import Image, ImageDraw
        
        def create_image():
            favicon_path = os.path.join(get_project_root(), 'gui', 'favicon.ico')
            if os.path.exists(favicon_path):
                return Image.open(favicon_path).resize((64, 64))
            image = Image.new('RGB', (64, 64), color='#667eea')
            dc = ImageDraw.Draw(image)
            dc.rectangle([16, 16, 48, 48], fill='white')
            dc.ellipse([24, 24, 40, 40], fill='#667eea')
            return image
        
        global tray_icon
        tray_icon = pystray.Icon(
            'AutoConnect',
            create_image(),
            '自动连接 - WiFi 校园网助手',
            get_tray_menu()
        )
        
        tray_icon.run()
    except Exception as e:
        log_message(f'托盘功能启动失败: {e}', 'error')


if __name__ == "__main__":
    if '--headless' in sys.argv:
        run_headless()
    elif '--apply-autostart' in sys.argv:
        # 提权后的进程：注册开机自启计划任务后退出
        apply_auto_start_task(True)
    elif '--remove-autostart' in sys.argv:
        # 提权后的进程：删除开机自启计划任务后退出
        apply_auto_start_task(False)
    elif '--tray-only' in sys.argv:
        # 用户登录后由计划任务拉起，显示托盘并遥控无头后台服务
        run_gui()
    else:
        # 检查是否已有实例在运行
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8888))
        sock.close()
        
        if result == 0:
            print("程序已在运行，正在跳转...")
            try:
                cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cmd_sock.connect(('localhost', 8889))
                cmd_sock.send(b'SHOW_WINDOW')
                cmd_sock.close()
            except Exception:
                pass
        else:
            run_gui()