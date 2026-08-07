# 生成 Windows 安装包

PyInstaller 不支持从 macOS 交叉编译 Windows 程序，必须让构建命令在 Windows 环境中运行一次。

## 在 Windows 电脑上构建

1. 安装 Python 3.9 或更高版本。
2. 安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)。
3. 解压 Windows 构建包。
4. 双击 `build-windows.bat`。

也可以在解压目录打开 PowerShell 后执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build-windows.ps1
```

完成后，安装包位于：

```text
dist\AutoPomodoro-Official-1.0-Windows-Setup.exe
```

## 使用 GitHub 免费的 Windows 构建机

项目内包含 `.github/workflows/build-windows.yml`。将项目上传到 GitHub 后：

1. 打开仓库的 Actions 页面。
2. 选择“Build Windows installer”。
3. 点击“Run workflow”。
4. 构建结束后，在任务页面底部下载 `AutoPomodoro-Official-1.0-Windows-Setup` artifact。
