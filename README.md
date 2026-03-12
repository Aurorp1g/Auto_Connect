# Auto Connect

校园网自动连接工具 - 解决校园网频繁掉线和重复登录问题

## 功能特性

- **WiFi 自动连接** - 自动连接到指定校园WiFi热点
- **校园网自动认证** - 支持 DRCOM、JLGC 等多种校园网认证方式
- **智能重连机制** - 网络断开后自动检测并重新连接
- **内置浏览器界面** - 采用便携版 Chromium 提供图形界面
- **系统托盘运行** - 最小化到系统托盘，后台稳定运行
- **日志记录** - 完整的运行日志记录功能

## 技术栈

- **Python** - 核心开发语言
- **Eel** - Python Web GUI 框架
- **PyInstaller** - 程序打包
- **pystray** - 系统托盘支持
- **Chromium** - 便携版浏览器（内置）

## 项目结构

```
Auto_Connect/
├── auto_connect.py          # 主程序入口
├── core/                   # 核心模块
│   ├── campus_login.py     # 校园网登录
│   ├── config.py           # 配置管理
│   └── wifi_manager.py     # WiFi 连接管理
├── browser/                # 浏览器模块
│   └── custom_chrome.py    # 内置 Chrome 启动器
├── chromium/               # 便携版 Chromium
│   ├── chrome.exe
│   └── user_data/          # 用户数据目录
├── build/                  # 构建输出
│   └── Auto_Connect/       # 打包后的可执行文件
├── requirements.txt        # Python 依赖
└── Auto_Connect.spec       # PyInstaller 配置文件
```

## 环境要求

- Windows 10/11 系统
- Python 3.8+
- Node.js（用于RSA加密认证）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行项目

### 开发模式

```bash
python auto_connect.py
```

### 打包为可执行文件

```bash
pyinstaller --onedir --contents-directory . --name Auto_Connect --add-data "gui;gui" --add-data "chromium;chromium" --add-data "post;post" --noconsole -i favicon.ico auto_connect.py
```

## 配置说明

首次运行后，会在用户目录下生成配置文件 `auto_connect_config.json`，主要配置项包括：

- **WiFi 配置** - 目标 SSID、密码等
- **校园网配置** - 登录URL、认证参数等
- **通用配置** - 检查间隔、重试次数等

## 使用说明

1. 首次运行自动打开配置界面
2. 输入校园网 WiFi 名称和账号密码
3. 点击启动服务
4. 程序会在系统托盘运行，自动处理网络连接

## 注意事项

- 确保已安装 Node.js（用于生成RSA加密的登录数据）
- 内置 Chromium 会占用一定磁盘空间
- 配置文件和日志文件存储在用户目录下

## 许可证

MIT License