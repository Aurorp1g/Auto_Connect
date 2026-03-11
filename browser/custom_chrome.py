import sys
import os
import subprocess as sps
import time

def get_chrome_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(base_path)
    
    chrome_path = os.path.join(base_path, 'chromium', 'chrome.exe')
    return chrome_path

def start_chrome_for_eel(port=8888, hidden=False):
    chrome_path = get_chrome_path()
    
    if not os.path.exists(chrome_path):
        print("便携版Chromium未找到")
        return None
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(base_path)
    user_data_dir = os.path.join(base_path, 'chromium', 'user_data')
    
    cmd = [
        chrome_path,
        '--app=http://localhost:%d/index.html' % port,
        '--user-data-dir=' + user_data_dir,
        '--disable-http-cache',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-features=TranslateUI',
        '--disable-extensions',
        '--remote-debugging-port=9222',
        '--window-size=1200,750',
        '--force-dark-mode',
        '--disable-features=ChromeDarkMode'
    ]
    
    if hidden:
        cmd.append('--hidden')
    
    proc = sps.Popen(cmd, stdout=sps.DEVNULL, stderr=sps.DEVNULL, stdin=sps.DEVNULL, creationflags=sps.CREATE_NEW_PROCESS_GROUP)
    return proc