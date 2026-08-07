from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path


APP_ID = "com.personaltools.autopomodoro"
WINDOWS_VALUE_NAME = "AutoPomodoro"


class AutostartError(RuntimeError):
    pass


def launch_arguments() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve())]
    main_file = Path(__file__).resolve().parents[1] / "main.py"
    return [str(Path(sys.executable).resolve()), str(main_file)]


def set_start_on_login(enabled: bool) -> None:
    if sys.platform == "darwin":
        _set_macos(enabled)
    elif sys.platform == "win32":
        _set_windows(enabled)
    else:
        raise AutostartError("开机自动启动目前仅支持 macOS 和 Windows。")


def _set_macos(enabled: bool) -> None:
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    plist_path = launch_agents / f"{APP_ID}.plist"
    try:
        if not enabled:
            plist_path.unlink(missing_ok=True)
            return
        executable = launch_arguments()[0]
        if executable.startswith("/Volumes/") or "/AppTranslocation/" in executable:
            raise AutostartError("请先把应用拖入“应用程序”文件夹并重新打开，再开启自动启动。")
        launch_agents.mkdir(parents=True, exist_ok=True)
        payload = {
            "Label": APP_ID,
            "ProgramArguments": launch_arguments(),
            "RunAtLoad": True,
            "KeepAlive": False,
            "ProcessType": "Interactive",
        }
        temporary_path = plist_path.with_suffix(".plist.tmp")
        temporary_path.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML))
        temporary_path.replace(plist_path)
    except OSError as exc:
        raise AutostartError(f"无法更新 macOS 登录启动项：{exc}") from exc


def _set_windows(enabled: bool) -> None:
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                command = subprocess.list2cmdline(launch_arguments())
                winreg.SetValueEx(key, WINDOWS_VALUE_NAME, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, WINDOWS_VALUE_NAME)
                except FileNotFoundError:
                    pass
    except OSError as exc:
        raise AutostartError(f"无法更新 Windows 开机启动项：{exc}") from exc
