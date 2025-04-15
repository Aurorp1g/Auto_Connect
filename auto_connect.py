import subprocess
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import os

def setup_logger():
    """配置日志记录器"""
    log_file = "connect_log.txt"
    
    current_dir = os.path.abspath(os.path.dirname(__file__))
    full_path = os.path.join(current_dir, log_file)
    
    try:
        if os.path.exists(full_path):
            os.remove(full_path)
    except Exception as e:
        print(f"删除旧日志失败: {str(e)}")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(full_path, encoding='utf-8', mode='w')  # 移除StreamHandler
        ],  # 仅保留文件处理器
        force=True
    )

def check_network_connection():
    """检查网络连接状态"""
    import urllib.request
    targets = [
        "http://connectivitycheck.gstatic.com/generate_204",
        "http://www.msftconnecttest.com/connecttest.txt", 
        "http://connect.rom.miui.com/generate_204"
    ]
    timeout = 8

    logging.info("正在进行单次HTTP检测:")
    for url in targets:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status == 204:
                    logging.info(f"[成功] {url} 返回204")
                    return True
                logging.warning(f"[跳过] {url} 状态码: {response.status}")  # 改为使用warning级别
        except Exception as e:
            logging.error(f"[失败] {url} 错误: {str(e)}")  # 将print改为logging.error
    
    logging.error("所有HTTP检测目标均无响应")
    return False

def connect_to_wifi(ssid):
    """连接到指定的WiFi网络"""
    print(f"尝试连接到WiFi: {ssid}")
    try:
        # 使用netsh命令连接WiFi
        subprocess.check_output(
            ["netsh", "wlan", "connect", f"name={ssid}"],
            stderr=subprocess.STDOUT,
            shell=True
        )
        print(f"已连接到WiFi: {ssid}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"连接WiFi失败: {e.output.decode('utf-8', errors='ignore')}")
        return False

def auto_login():
    """自动完成认证"""
    print("打开浏览器进行认证...")
    try:
        # 配置Edge浏览器选项
        edge_options = Options()
        edge_options.add_argument("--headless=new")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--log-level=3")  # 新增：设置日志级别为FATAL
        edge_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])  # 新增第二个参数
        
        # 启动Edge浏览器
        service = Service()
        # 移除 service.service_args = ['--verbose']
        driver = webdriver.Edge(service=service, options=edge_options)

        # 访问认证页面（根据实际情况修改URL）
        driver.get("http://10.10.9.4/")  # 替换为实际的认证页面URL

        # 等待页面加载完成
        time.sleep(5)

        # 尝试找到"连接Login"按钮并点击
        try:
            # 等待按钮出现，超时时间为10秒
            login_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), '连接 Login')]"))
            )
            login_button.click()
            print("已点击'连接 Login'按钮。")
        except (NoSuchElementException, TimeoutException):
            print("未找到'连接 Login'按钮。")
            driver.quit()
            return False

        # 关闭浏览器
        driver.quit()
        print("认证完成，已关闭浏览器。")
        return True
    except Exception as e:
        print(f"认证过程中发生错误: {e}")
        return False

def main(): 
    if not check_network_connection():
        print("开始网络重连流程...")
        if connect_to_wifi("fosu"):
            time.sleep(10)
            # 修改检查逻辑为否定判断
            if not check_network_connection():  # 网络仍然不可用时执行认证
                print("开始自动认证流程...")
                if auto_login():
                    print("等待认证生效...")
                    time.sleep(15)  # 增加认证后等待时间
                    # 认证后再次检查网络
                    if check_network_connection():
                        print("认证成功，网络已连接")
                    else:
                        print("认证后网络仍然不可用")
                else:
                    print("自动认证失败")
            else:
                print("连接WiFi后网络已自动恢复")  # 新增提示
        else:
            print("未找到WiFi: fosu，脚本停止。")
    else:
        print("网络已连接，无需进一步操作。")

if __name__ == "__main__":
    setup_logger()
    main()  