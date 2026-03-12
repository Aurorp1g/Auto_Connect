# Auto Connect

校园网自动连接工具 - 解决校园网频繁掉线和重复登录问题

## 功能特性

- **WiFi 自动连接** - 自动连接到指定校园WiFi热点
- **校园网自动认证** - 支持 DRCOM、JLGC 等多种校园网认证方式
- **智能重连机制** - 网络断开后自动检测并重新连接
- **内置浏览器界面** - 采用便携版 Chromium 提供图形界面（可选）
- **系统托盘运行** - 最小化到系统托盘，后台稳定运行
- **日志记录** - 完整的运行日志记录功能

## 技术栈

- **Python** - 核心开发语言
- **Eel** - Python Web GUI 框架
- **PyInstaller** - 程序打包
- **pystray** - 系统托盘支持
- **Chromium** - 便携版浏览器（可选，内置）

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
├── chromium/               # 便携版 Chromium（可选）
│   └── chrome.exe
├── gui/                    # 前端资源
├── post/                   # 登录认证脚本
├── build/                  # 构建输出
│   └── Auto_Connect/       # 打包后的可执行文件
├── requirements.txt        # Python 依赖
└── Auto_Connect.spec       # PyInstaller 配置文件
```

## 环境要求

- Windows 10/11 系统
- Python 3.8+
- Node.js（用于RSA加密认证）
- **Chromium 125.0.6422.113**（可选，用于内置浏览器界面）

## Chromium 安装（可选）

本项目的 `chromium` 目录默认已被 `.gitignore` 忽略，如需使用内置浏览器界面，请手动下载并放置：

### 必需文件

下载 Chromium 便携版（版本：**125.0.6422.113**），将以下文件放入 `chromium/` 目录：

```
chromium/
├── chrome.exe              # 主程序
├── chrome.dll
├── chrome_elf.dll
├── d3dcompiler_47.dll
├── dxcompiler.dll
├── dxil.dll
├── icudtl.dat
├── libEGL.dll
├── libGLESv2.dll
├── resources.pak
└── ...（其他依赖文件）
```

### 下载地址

- [Chromium Browser Downloads](https://chromium.cypress.io/)
- 或自行搜索 `Chromium 125.0.6422.113 portable`

### 注意事项

- 若未放置 Chromium，程序启动时会自动使用系统默认浏览器
- 终端会显示提示信息引导下载安装
- 使用内置 Chromium 可获得更好的界面体验和离线运行能力

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