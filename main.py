from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from pomodoro.ui import APP_STYLE, MainWindow, load_app_icon


def main() -> int:
    QCoreApplication.setOrganizationName("PersonalTools")
    QCoreApplication.setApplicationName("AutoPomodoro")
    QCoreApplication.setApplicationVersion("1.0.0")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    app.setQuitOnLastWindowClosed(False)
    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
