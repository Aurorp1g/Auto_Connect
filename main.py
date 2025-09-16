import re    # 正则表达式，用于匹配字符
from urllib import request
import urllib.request
import requests
import time
import random
import os

def check_network_connection():
    """检查网络连接状态"""
    targets = [
        "http://connectivitycheck.gstatic.com/generate_204",
        "http://www.msftconnecttest.com/connecttest.txt",
        "http://connect.rom.miui.com/generate_204"
    ]
    timeout = 8

    for url in targets:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status == 204:
                    return True
        except:
            continue
    return False
def auto_login(post_URL, get_URL, log_file_path):
    print("自动联网脚本开始运行...")
    try:
        # 请求校园网url
        response = request.urlopen(get_URL)
        html = response.read()
        # 获取title元素内容
        res = re.findall('<title>(.*)</title>', html.decode(encoding="GBK", errors="strict"))
        title = ''
        if len(res) == 0:
            title = '未登录'
        else:
            title = res[0]
        # 根据title元素内容判断是否处于已登录状态
        if title == '登录成功':    
            print('当前状态为：已登陆成功！')
        else:
            print('当前状态为：未登录！')
            # 设置post的请求头，浏览器点击F12，在Netword中选中post请求，点击Headers、request header面板中查看
            header = {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "Connection": "keep-alive",
                "Content-Length": "781",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Cookie": "EPORTAL_COOKIE_DOMAIN=false; EPORTAL_COOKIE_SAVEPASSWORD=true; EPORTAL_COOKIE_OPERATORPWD=; EPORTAL_COOKIE_NEWV=true; EPORTAL_COOKIE_PASSWORD=0c8e03e937910c800890ec544b109fce824381097eba5b4e91011f2c3615a959563377abf814d21320f9f0c98a6615cf42b17d3920473acdb51447afc135c59e2e8a69b4136afde0b623a64e56fc0a82f330f70ce253235e999cc858bff65867a22053c8186fd148a20e0ba3d45ced58808990a864a4f39c72f368ddf0086582; EPORTAL_AUTO_LAND=; EPORTAL_COOKIE_SERVER=%E7%A7%BB%E5%8A%A8; EPORTAL_COOKIE_SERVER_NAME=%E7%A7%BB%E5%8A%A8; EPORTAL_USER_GROUP=Student; EPORTAL_COOKIE_USERNAME=; JSESSIONID=BD9937825302ECA25A22692E95D92CF1",
                "Host": "10.10.9.4",
                "Origin": "http://10.10.9.4",
                "Referer": "http://10.10.9.4/eportal/index.jsp?wlanuserip=10.201.220.90&wlanacname=FSN-XX-Business&ssid=&nasip=10.10.9.1&snmpagentip=&mac=44fa66c84741&t=wireless-v2-plain&url=http://www.msftconnecttest.com/redirect&apmac=&nasid=FSN-XX-Business&vid=3326&port=472&nasportid=AggregatePort%20175.33260000:3326-0",
                "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36 Edg/131.0.0.0",
            }
            # 设置post的请求数据，浏览器点击F12，在Netword中选中post请求，点击payload面板中查看
            data = {
                "userId": 'XXXX',  # 需要根据自己的情况修改
                "password": '0c937910c800890ec544b109fce824381097eba5b4e91011f2c3615a9595abf814d21320f9f0c98a642b17d3920473acdb51447afc135c59e2e9b413e0b623a64e56fc0a82f330f70ce253235e999cc85a22053c8186fd148a20e0ba3d45ced58808990a864a4f39c72f3f0086582',  # 需要根据自己的情况修改
                "queryString": 'wlanuserip%3D10.201.220.90%26wlanacname%3DFSN-XX-Business%26ssid%3D%26nasip%3D10.10.9.1%26snmpagentip%3D%26mac%3D44fa66c84741%26t%3Dwireless-v2-plain%26url%3Dhttp%3A%2F%2Fwww.msftconnecttest.com%2Fredirect%26apmac%3D%26nasid%3DFSN-XX-Business%26vid%3D3326%26port%3D472%26nasportid%3DAggregatePort%2520175.33260000%3A3326-0',
                "passwordEncrypt": 'true',
                "operatorPwd": '',
                "operatorUserId": '',
                "validcode": '',
                "service": '%E7%A7%BB%E5%8A%A8',
            }
            # 发送post请求（设置好header和data）
            post_response = requests.post(post_URL, data, headers=header)
            print(f"post请求状态码 {post_response.status_code}")  # 修正状态码获取方式
            uft_str = post_response.text.encode("iso-8859-1").decode('utf-8')
        
            # 发送get请求（修改响应变量名）
            schoolWebLoginURL = get_URL
            get_status = requests.get(schoolWebLoginURL).status_code
            print(f"get请求状态码 {get_status}")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        error_msg = str(e)
        
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(f"[{time.ctime()}] 自动联网脚本开始运行\n")
        log_file.write(f"当前状态: {'已登陆成功' if title == '登录成功' else '未登录'}\n")
        if 'post_response' in locals():
            log_file.write(f"POST状态码: {post_response.status_code}\n")
        if 'get_status' in locals():
            log_file.write(f"GET状态码: {get_status}\n")
        if 'error_msg' in locals():
            log_file.write(f"错误信息: {error_msg}\n")
        log_file.write("-"*50 + "\n")

    # 检查文件大小，如果大于1KB则清空文件
    if os.path.getsize(log_file_path) > 1024:
        open(log_file_path, 'w').close()


if __name__ == "__main__":
    log_file_path = 'auto_connect.log'
    # 确保日志文件存在
    if not os.path.exists(log_file_path):
        open(log_file_path, 'w').close()
    
    post_URL = 'http://10.10.9.4/eportal/InterFace.do?method=login' 
    get_URL = 'http://10.10.9.4/eportal/success.jsp?userIndex=30313761383634643038313231376666613631393530663863623836663665345f31302e3230312e3232302e39305f3230323430333930313432&keepaliveInterval=0'
    
    while True:
        while not check_network_connection():
            auto_login(post_URL, get_URL, log_file_path)
        print("网络已恢复，自动联网脚本结束运行")
        
        # 每1min左右检测一次是否成功连接
        rand = random.uniform(0, 20)
        print("休眠",int(60.0 + rand),"s")
        time.sleep(60.0 + rand)