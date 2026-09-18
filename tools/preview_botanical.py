"""Capture real Qt widgets without touching user preferences or startup entries.

Run from the project root: QT_QPA_PLATFORM=offscreen .venv/bin/python tools/preview_botanical.py
"""
from pathlib import Path
import sys
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pomodoro.engine import Phase
from pomodoro.settings import AppSettings
from pomodoro.ui import AlertDialog, MainWindow


def main():
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    output = Path(__file__).resolve().parents[1] / "preview"
    output.mkdir(exist_ok=True)
    with patch("pomodoro.ui.AppSettings.load", return_value=AppSettings()):
        window = MainWindow()
    window.poll_timer.stop()
    window.show()
    app.processEvents()

    def capture(name):
        window.specimen._transition.setCurrentTime(220)
        app.processEvents()
        window.grab().save(str(output / f"{name}.png"))

    capture("01-waiting")
    window.engine.mouse_moved(0)
    window._refresh(300)
    capture("02-focus")
    window._refresh(1470)
    window.specimen._transition.setCurrentTime(220)
    capture("03-imminent")
    window.engine.phase = Phase.WORK_ALERT
    window.engine.confirm_work_alert(0)
    window._refresh(120)
    capture("04-rest")
    for index in range(1, 5):
        window.tabs.setCurrentIndex(index)
        capture(f"settings-{index}")
    window.resize(680, 540)
    window.tabs.setCurrentIndex(2)
    capture("05-small-window")
    window.scroll.verticalScrollBar().setValue(window.scroll.verticalScrollBar().maximum())
    capture("06-small-settings")
    dialog = AlertDialog("该休息了", "本轮专注时间已结束。请点击确认，休息倒计时将从此刻开始。", "确认并开始休息", "", False, "#25302b", "", window)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(output / "07-alert.png"))
    dialog.accept()
    window.close()
    print(output)


if __name__ == "__main__":
    main()
