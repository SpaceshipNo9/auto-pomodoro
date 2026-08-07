# 自动番茄钟 · 正式版 1.0

这是一个 Windows / macOS 跨平台桌面番茄钟。它轮询系统鼠标位置，检测到移动后自动开始工作倒计时；工作期间鼠标静止达到设定时间后，本轮自动重置。

> 本软件由九号飞船 With ChatGPT Codex 开发，免费使用。如果您为官方安装包付费，请立即退款。
>
> Developed by Spaceship No. 9 with ChatGPT Codex. The official builds are free to use. If you paid for an official build, request an immediate refund.

## 功能

- 鼠标开始移动时自动计时
- 工作计时、鼠标静止重置时间、休息时间均可调节（支持 0.1 分钟，便于测试）
- 工作结束后弹窗并循环响铃，必须点击确认才能进入休息
- 休息结束后再次弹窗并响铃，确认后等待下一轮鼠标移动
- 可选择本地 MP3、WAV、M4A、AAC、OGG 或 FLAC 铃声
- 可选择 PNG、JPG、BMP 或 WebP 作为提示弹窗背景
- 可分别选择主界面背景图和提示弹窗背景图
- 可自定义整个界面的字体、文字颜色和主题强调色
- 可自定义工作结束与休息结束弹窗的标题、正文和按钮文字
- 可选择登录 Windows/macOS 后自动启动
- 一键隐藏到 Windows 系统托盘或 macOS 顶部菜单栏，后台继续计时
- 托盘菜单支持查看状态、显示主界面、重置周期和退出
- 设置自动保存

## 直接运行

需要 Python 3.9 或更高版本。

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

Windows 也可将上面的 `python3` 换成 `py`。

## 打包为 Windows 软件

必须在 Windows 电脑上完成 Windows 打包。在 PowerShell 中执行：

```powershell
.\build-windows.ps1
```

如果已安装 Inno Setup 6，会生成 `dist\AutoPomodoro-Official-1.0-Windows-Setup.exe` 安装包；同时也会保留 `dist\AutoPomodoro\AutoPomodoro.exe` 便携版。macOS 无法直接生成 Windows 二进制，详细方法见 `BUILD-WINDOWS.md`。

## 打包为 macOS 软件

必须在 Mac 上完成 macOS 打包。在“终端”中执行：

```bash
chmod +x build-macos.command
./build-macos.command
```

生成结果包括 `dist/AutoPomodoro.app` 和 `dist/AutoPomodoro-macOS-Universal.dmg`。Universal 2 安装包同时支持 Intel 与 Apple Silicon（M1/M2/M3/M4/M5 等）芯片，无需分别下载。首次打开未经 Apple 公证的 App 时，可能需要在 Finder 中按住 Control 点击应用，再选择“打开”。若公开分发，则应使用 Apple Developer 证书签名并公证。

## 使用说明

1. 启动应用并设置三个时间参数。
2. 按需选择铃声和背景图，点击“保存设置并重置当前周期”。
3. 保持程序运行。鼠标下一次发生明显移动时会自动开始工作计时。
4. 若工作期间鼠标静止达到阈值，本轮会被取消，并重新等待移动。
5. 工作结束弹窗不能通过关闭按钮或 Esc 跳过；点击“确认并开始休息”后才开始休息计时。
6. 休息结束后确认提示，程序回到等待状态。
7. 点击“一键最小化”后，Windows 可从右下角托盘恢复，macOS 可从顶部菜单栏图标恢复；关闭主窗口仍会退出应用。

建议先把 App 拖入“应用程序”文件夹，再开启“登录系统后自动启动”，这样开机启动项会记录稳定的应用路径。

应用通过读取鼠标坐标变化工作，不记录点击、按键或鼠标轨迹，也不会联网。macOS 通常无需授予“辅助功能”权限。

## 运行测试

```bash
python3 -m unittest discover -s tests -v
```

## 开源许可证

源代码以 [MIT License](LICENSE) 发布。MIT 许可证允许使用、修改与再分发；本项目作者提供的官方安装包永久免费。
