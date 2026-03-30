; 该脚本使用 HM VNISEdit 脚本编辑器向导产生

; 安装程序初始定义常量
!define PRODUCT_NAME "Auto_Connect"
!define PRODUCT_VERSION "1.1.0"
!define PRODUCT_PUBLISHER "Aurorp1g"
!define PRODUCT_WEB_SITE "https://github.com/Aurorp1g/Auto_Connect"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\Auto_Connect.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

SetCompressor lzma

; ------ MUI 现代界面定义 (1.67 版本以上兼容) ------
!include "MUI.nsh"
!include "LogicLib.nsh"

; MUI 预定义常量
!define MUI_ABORTWARNING
!define MUI_ICON "favicon.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; 欢迎页面
!insertmacro MUI_PAGE_WELCOME
; 安装目录选择页面
!insertmacro MUI_PAGE_DIRECTORY
; 安装过程页面
!insertmacro MUI_PAGE_INSTFILES
; 安装完成页面
!define MUI_FINISHPAGE_RUN "$INSTDIR\Auto_Connect.exe"
!insertmacro MUI_PAGE_FINISH

; 安装卸载过程页面
!insertmacro MUI_UNPAGE_INSTFILES

; 安装界面包含的语言设置
!insertmacro MUI_LANGUAGE "SimpChinese"

; 安装预释放文件
!insertmacro MUI_RESERVEFILE_INSTALLOPTIONS
; ------ MUI 现代界面定义结束 ------

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "Auto_Connect_Installer.exe"
InstallDir "$PROGRAMFILES\Auto_Connect"
InstallDirRegKey HKLM "${PRODUCT_UNINST_KEY}" "UninstallString"
ShowInstDetails show
ShowUnInstDetails show
BrandingText " "

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  File /r "dist\Auto_Connect\*.*"
  CreateDirectory "$SMPROGRAMS\Auto_Connect"
  CreateShortCut "$SMPROGRAMS\Auto_Connect\Auto_Connect.lnk" "$INSTDIR\Auto_Connect.exe"
  CreateShortCut "$DESKTOP\Auto_Connect.lnk" "$INSTDIR\Auto_Connect.exe"
  ; [已删除重复] File "dist\Auto_Connect\Auto_Connect.exe"
SectionEnd

Section -AdditionalIcons
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\Auto_Connect\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
  CreateShortCut "$SMPROGRAMS\Auto_Connect\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\Auto_Connect.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\Auto_Connect.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd

/******************************
 *  以下是安装程序的卸载部分  *
 ******************************/

Section Uninstall
  ; 1) 先整体递归删除安装目录（包含所有子目录和文件）
  RMDir /r "$INSTDIR"

  ; 2) 再删快捷方式（如果目录已不存在也没问题）
  Delete "$DESKTOP\Auto_Connect.lnk"
  Delete "$SMPROGRAMS\Auto_Connect\Auto_Connect.lnk"
  Delete "$SMPROGRAMS\Auto_Connect\Website.lnk"
  Delete "$SMPROGRAMS\Auto_Connect\Uninstall.lnk"
  RMDir  "$SMPROGRAMS\Auto_Connect"

  ; 3) 清理软件本身的注册表信息
  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"

  ; 4) 【修正】清理开机自启动注册表项 - 同时尝试64位和32位视图
  DetailPrint "Removing AutoConnect startup entry..."

  ; 先尝试64位视图（原生注册表）
  SetRegView 64
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "AutoConnect"

  ; 再尝试32位视图（Wow6432Node，如果Python是32位写入的）
  SetRegView 32
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "AutoConnect"

  ; 恢复默认视图
  SetRegView lastused

  ; 可选：如果担心权限上下文问题，也尝试删除HKLM的（如果曾错误写入）
  DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "AutoConnect"

  SetAutoClose true
SectionEnd

#-- 根据 NSIS 脚本编辑规则，所有 Function 区段必须放置在 Section 区段之后编写，以避免安装程序出现未可预知的问题。--#

Function un.onInit
  ; 【修正】检测并终止 Auto_Connect.exe（主程序）
  nsExec::ExecToStack '"cmd" /c tasklist /FI "IMAGENAME eq Auto_Connect.exe" 2>nul | find /I "Auto_Connect.exe"'
  Pop $0

  ${If} $0 == 0
    MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Auto_Connect 正在运行（包含内置浏览器）。$\n$\n是否强制关闭程序及所有关联进程并继续卸载？$\n$\n（注意：强制关闭可能导致未保存的配置丢失）" IDYES terminate_app IDNO abort_uninstall

    terminate_app:
      DetailPrint "Terminating Auto_Connect.exe and process tree..."
      ; 【关键】使用 /T 参数终止整个进程树（包含子进程）
      nsExec::ExecToStack '"cmd" /c taskkill /IM Auto_Connect.exe /F /T 2>nul'
      Pop $0
      ; 等待主程序及其子进程退出
      Sleep 3000

      ; 【修正】强制终止可能残留的独立 Chromium 进程（通过端口 8888 识别）
      DetailPrint "Checking for residual Chromium processes..."
      nsExec::ExecToStack '"cmd" /c netstat -ano | findstr ":8888" | findstr "LISTENING" 2>nul'
      Pop $0

      ${If} $0 == 0
        DetailPrint "Terminating residual Chromium on port 8888..."
        ; 【关键修正】修复引号嵌套，使用 $\" 转义内部双引号
        nsExec::ExecToStack "cmd /c for /f \"tokens=5\" %p in ('netstat -ano ^| findstr \":8888\" ^| findstr \"LISTENING\"') do @taskkill /PID %p /F >nul 2>&1"
        Sleep 1500
      ${EndIf}

      Goto continue_uninstall
  ${EndIf}

  continue_uninstall:
  ; 确认卸载对话框
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "您确实要完全移除 $(^Name) ，及其所有的组件？" IDYES +2

  abort_uninstall:
  Abort
FunctionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) 已成功地从您的计算机移除。"
FunctionEnd
