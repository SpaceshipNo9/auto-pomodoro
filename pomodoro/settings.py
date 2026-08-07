from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths


@dataclass
class AppSettings:
    work_minutes: float = 25.0
    idle_minutes: float = 3.0
    rest_minutes: float = 5.0
    sound_path: str = ""
    background_path: str = ""
    sound_volume: int = 80
    always_on_top: bool = True
    start_on_login: bool = False
    font_family: str = ""
    text_color: str = "#25302b"
    accent_color: str = "#1f6d55"
    main_background_path: str = ""
    work_alert_title: str = "该休息了"
    work_alert_message: str = "本轮专注时间已结束。请点击确认，休息倒计时将从此刻开始。"
    work_alert_button: str = "确认并开始休息"
    ready_alert_title: str = "可以开始工作 / 学习了"
    ready_alert_message: str = "休息时间已经结束。确认后，番茄钟会重新等待鼠标移动，再自动开始下一轮。"
    ready_alert_button: str = "确认并等待下一轮"

    @classmethod
    def load(cls) -> "AppSettings":
        path = settings_path()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()

        if not isinstance(raw, dict):
            return cls()

        defaults = asdict(cls())
        clean = {}
        for key, default in defaults.items():
            value = raw.get(key, default)
            if isinstance(default, bool):
                clean[key] = value if isinstance(value, bool) else default
            elif isinstance(default, float):
                try:
                    number = float(value)
                    clean[key] = number if math.isfinite(number) else default
                except (TypeError, ValueError):
                    clean[key] = default
            elif isinstance(default, int):
                clean[key] = value if isinstance(value, int) and not isinstance(value, bool) else default
            elif isinstance(default, str):
                clean[key] = value if isinstance(value, str) else default
            else:
                clean[key] = default

        clean["work_minutes"] = min(600.0, max(0.1, clean["work_minutes"]))
        clean["idle_minutes"] = min(120.0, max(0.1, clean["idle_minutes"]))
        clean["rest_minutes"] = min(240.0, max(0.1, clean["rest_minutes"]))
        clean["sound_volume"] = min(100, max(0, clean["sound_volume"]))
        try:
            return cls(**clean)
        except (TypeError, ValueError):
            return cls()

    def save(self) -> None:
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def settings_path() -> Path:
    folder = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
    return Path(folder) / "settings.json"
