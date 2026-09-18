from __future__ import annotations

import sys
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QCloseEvent, QCursor, QFont, QFontDatabase, QIcon, QPainter, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .autostart import AutostartError, set_start_on_login
from .engine import Durations, Event, Phase, PomodoroEngine
from .settings import AppSettings
from .design import TOKENS, SpecimenWidget, serif_family, stylesheet


def valid_color(value: str, fallback: str) -> str:
    color = QColor(value)
    return color.name() if color.isValid() else fallback


def build_style(settings: AppSettings) -> str:
    text = valid_color(settings.text_color, "#25302b")
    accent = valid_color(settings.accent_color, "#1f6d55")
    font = settings.font_family.replace('"', "") if settings.font_family else (QApplication.font().family() if QApplication.instance() else "sans-serif")
    # APP_STYLE is also imported before QApplication is created.
    serif = settings.font_family.replace('"', "") if settings.font_family else (serif_family() if QApplication.instance() else "Georgia")
    return stylesheet(text, accent, font, serif)


APP_STYLE = build_style(AppSettings())


def resource_path(relative_path: str) -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return bundle_root / relative_path


def load_app_icon() -> QIcon:
    candidates = [
        resource_path("assets/app-icon.svg"),
        Path(sys.executable).resolve().parent.parent / "Resources" / "AutoPomodoro.icns",
    ]
    for candidate in candidates:
        if candidate.is_file():
            icon = QIcon(str(candidate))
            if not icon.isNull():
                return icon
    return QIcon()


def format_time(seconds: int | None) -> str:
    if seconds is None:
        return "--:--"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class OptionToggle(QPushButton):
    """A full-width checkable setting; every visible pixel is clickable."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("optionToggle")
        self.setCheckable(True)
        self.setMinimumHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._sync_text)
        self._sync_text(False)

    def _sync_text(self, checked: bool) -> None:
        self.setText("● 已开启（点击可关闭）" if checked else "○ 已关闭（点击可开启）")


class BackgroundWidget(QWidget):
    def __init__(self, path: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mainBackground")
        self._background = QPixmap()
        self.set_background(path)

    def set_background(self, path: str) -> None:
        self._background = QPixmap(path) if path and Path(path).is_file() else QPixmap()
        self.update()

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        if not self._background.isNull():
            scaled = self._background.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
        else:
            painter.fillRect(self.rect(), QColor(TOKENS.paper))
        painter.end()
        super().paintEvent(event)


class SoundPlayer(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.output)
        self.player.mediaStatusChanged.connect(self._media_status_changed)
        self.beep_timer = QTimer(self)
        self.beep_timer.setInterval(1200)
        self.beep_timer.timeout.connect(QApplication.beep)
        self.custom_active = False

    def start(self, path: str, volume: int) -> None:
        self.stop()
        self.output.setVolume(max(0.0, min(1.0, volume / 100)))
        if path and Path(path).is_file():
            self.custom_active = True
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()
        else:
            QApplication.beep()
            self.beep_timer.start()

    def stop(self) -> None:
        self.custom_active = False
        self.beep_timer.stop()
        self.player.stop()

    def _media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if self.custom_active and status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPosition(0)
            self.player.play()
        elif self.custom_active and status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.custom_active = False
            QApplication.beep()
            self.beep_timer.start()


class AlertDialog(QDialog):
    confirmed = Signal()

    def __init__(
        self,
        title: str,
        message: str,
        button_text: str,
        background: str,
        always_on_top: bool,
        text_color: str,
        font_family: str,
        parent: QWidget | None = None,
    ) -> None:
        flags = Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        super().__init__(parent, flags)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(520, 380)
        self.resize(580, 440)
        self._background = QPixmap(background) if background and Path(background).is_file() else QPixmap()
        safe_text = valid_color(text_color, "#25302b")
        safe_font = font_family.replace('"', "") if font_family else QApplication.font().family()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.addStretch()
        panel = QFrame()
        panel.setObjectName("card")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(28, 22, 28, 26)
        panel_layout.setSpacing(16)
        folio = QLabel("AUTOPOMODORO  /  A MOMENT FOR YOU")
        folio.setObjectName("folio")
        folio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark = SpecimenWidget(compact=True)
        mark.setFixedSize(90, 90)
        panel_layout.addWidget(folio)
        panel_layout.addWidget(mark, 0, Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setTextFormat(Qt.TextFormat.PlainText)
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f'font-family: "{safe_font}"; font-size: 30px; font-weight: 700; color: {safe_text}; background: transparent;')
        message_label = QLabel(message)
        message_label.setTextFormat(Qt.TextFormat.PlainText)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet(f'font-family: "{safe_font}"; font-size: 18px; color: {safe_text}; background: transparent;')
        button = QPushButton(button_text)
        button.setMinimumHeight(46)
        button.clicked.connect(self._confirm)

        panel_layout.addWidget(title_label)
        panel_layout.addWidget(message_label)
        panel_layout.addWidget(button)
        outer.addWidget(panel)
        outer.addStretch()

    def _confirm(self) -> None:
        self.confirmed.emit()
        self.accept()

    def reject(self) -> None:
        return

    def closeEvent(self, event: QCloseEvent) -> None:
        event.ignore()

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        if not self._background.isNull():
            scaled = self._background.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
        else:
            painter.fillRect(self.rect(), QColor(TOKENS.paper))
        painter.end()
        super().paintEvent(event)


class MainWindow(QMainWindow):
    POLL_MS = 250
    MOVE_THRESHOLD = 2
    STATUS_TEXT = {
        Phase.WAITING: "等待鼠标移动，移动后自动开始",
        Phase.WORKING: "专注计时中",
        Phase.WORK_ALERT: "等待确认休息",
        Phase.RESTING: "休息计时中",
        Phase.READY_ALERT: "等待确认开始下一轮",
    }

    def __init__(self) -> None:
        super().__init__()
        self.settings = AppSettings.load()
        self.engine = self._new_engine()
        self.last_cursor_position: QPoint | None = None
        self.alert: AlertDialog | None = None
        self.sound = SoundPlayer(self)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_style(self.settings))

        self.setWindowTitle("自动番茄钟 · 正式版 1.0")
        self.setMinimumSize(680, 540)
        self.resize(900, 860)
        self._build_ui()
        self._load_settings_into_form()
        self._setup_tray()
        if self.settings.start_on_login:
            try:
                set_start_on_login(True)
            except AutostartError as exc:
                self.statusBar().showMessage(str(exc), 8000)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(self.POLL_MS)
        self.poll_timer.timeout.connect(self._poll)
        self.poll_timer.start()
        self._refresh()

    def _new_engine(self) -> PomodoroEngine:
        return PomodoroEngine(Durations(
            work_seconds=self.settings.work_minutes * 60,
            idle_seconds=self.settings.idle_minutes * 60,
            rest_seconds=self.settings.rest_minutes * 60,
        ))

    def _build_ui(self) -> None:
        self.central_background = BackgroundWidget(self.settings.main_background_path)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.central_background)
        self.setCentralWidget(self.scroll)
        outer = QVBoxLayout(self.central_background)
        outer.setContentsMargins(28, 20, 28, 16)
        outer.setSpacing(TOKENS.spacing)

        header = QHBoxLayout()
        title = QLabel("AutoPomodoro")
        title.setObjectName("title")
        signature = QLabel("自动番茄钟\nPLATE I · SPECIMEN 001")
        signature.setObjectName("folio")
        signature.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(signature)
        outer.addLayout(header)

        status_card = QFrame()
        status_card.setObjectName("card")
        status_outer = QVBoxLayout(status_card)
        status_outer.setContentsMargins(20, 18, 24, 18)
        status_layout = QHBoxLayout()
        status_layout.setSpacing(24)
        status_outer.addLayout(status_layout)
        specimen_column = QVBoxLayout()
        self.specimen = SpecimenWidget()
        self.specimen.setMaximumWidth(240)
        self.specimen.setMaximumHeight(210)
        specimen_column.addWidget(self.specimen, 1)
        specimen_caption = QLabel("FIG. 01  /  SOLANUM · TEMPUS")
        specimen_caption.setObjectName("folio")
        specimen_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        specimen_column.addWidget(specimen_caption)
        status_layout.addLayout(specimen_column, 2)
        readout = QVBoxLayout()
        readout.setSpacing(6)
        self.phase_tag = QLabel("OBSERVATION / 等待活动")
        self.phase_tag.setObjectName("eyebrow")
        readout.addWidget(self.phase_tag)
        self.status_label = QLabel()
        self.status_label.setObjectName("status")
        self.status_label.setWordWrap(True)
        self.clock_label = QLabel()
        self.clock_label.setObjectName("clock")
        self.phase_note = QLabel()
        self.phase_note.setObjectName("phaseNote")
        self.phase_note.setWordWrap(True)
        self.metrics = QLabel()
        self.metrics.setObjectName("metrics")
        self.metrics.setWordWrap(True)
        reset_button = QPushButton("重置并等待鼠标移动")
        reset_button.setObjectName("secondary")
        reset_button.clicked.connect(self._manual_reset)
        destination = "顶部菜单栏" if sys.platform == "darwin" else "系统托盘"
        self.minimize_button = QPushButton(f"一键最小化到{destination}")
        self.minimize_button.clicked.connect(self._hide_to_tray)
        status_buttons = QWidget()
        status_buttons_layout = QHBoxLayout(status_buttons)
        status_buttons_layout.setContentsMargins(0, 0, 0, 0)
        status_buttons_layout.setSpacing(10)
        status_buttons_layout.addWidget(reset_button)
        status_buttons_layout.addWidget(self.minimize_button)
        readout.addWidget(self.clock_label)
        readout.addWidget(self.status_label)
        readout.addWidget(self.phase_note)
        readout.addWidget(self.metrics)
        readout.addStretch()
        status_layout.addLayout(readout, 3)
        status_outer.addWidget(status_buttons)
        outer.addWidget(status_card)

        settings_card = QFrame()
        settings_card.setObjectName("card")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(20, 16, 20, 16)
        settings_title = QLabel("研究记录  /  PREFERENCES")
        settings_title.setObjectName("sectionTitle")
        settings_layout.addWidget(settings_title)
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        self.tabs.addTab(self._build_time_tab(), "01  时间")
        self.tabs.addTab(self._build_sound_tab(), "02  提醒")
        self.tabs.addTab(self._build_appearance_tab(), "03  界面")
        self.tabs.addTab(self._build_text_tab(), "04  文字")
        self.tabs.addTab(self._build_system_tab(), "05  系统")
        self.tabs.currentChanged.connect(self._fit_settings_page)
        self._fit_settings_page(0)
        settings_layout.addWidget(self.tabs)
        save_button = QPushButton("保存设置并重置当前周期")
        save_button.clicked.connect(self._save_settings)
        settings_layout.addWidget(save_button)
        outer.addWidget(settings_card, 1)

        hint = QLabel("应用保持运行即可监测整个桌面的鼠标位置；关闭主窗口会退出应用。")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(hint)

        credit = QLabel(
            "本软件由九号飞船 With ChatGPT Codex 开发，免费使用，如果您付费获得该软件，请立即退款。\n"
            "Developed by Spaceship No. 9 with ChatGPT Codex. Free to use. If you paid for this software, request an immediate refund."
        )
        credit.setObjectName("credit")
        credit.setWordWrap(True)
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(credit)

    def _fit_settings_page(self, index: int) -> None:
        # Hidden forms must not force the short time page to be as tall as the
        # text editor. The outer scroll area handles shorter laptop screens.
        for number in range(self.tabs.count()):
            page = self.tabs.widget(number)
            page.setSizePolicy(QSizePolicy.Policy.Preferred,
                               QSizePolicy.Policy.Preferred if number == index else QSizePolicy.Policy.Ignored)
        page = self.tabs.widget(index)
        self.tabs.setFixedHeight(page.sizeHint().height() + self.tabs.tabBar().sizeHint().height() + 8)
        self.tabs.updateGeometry()

    def _setup_tray(self) -> None:
        icon = QApplication.windowIcon()
        if icon.isNull():
            icon = load_app_icon()
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("自动番茄钟")
        tray_menu = QMenu()
        self.tray_status_action = QAction("状态：等待中", tray_menu)
        self.tray_status_action.setEnabled(False)
        show_action = QAction("显示主界面", tray_menu)
        reset_action = QAction("重置并等待鼠标移动", tray_menu)
        quit_action = QAction("退出自动番茄钟", tray_menu)
        show_action.triggered.connect(self._restore_window)
        reset_action.triggered.connect(self._manual_reset)
        quit_action.triggered.connect(self._quit_application)
        tray_menu.addAction(self.tray_status_action)
        tray_menu.addSeparator()
        tray_menu.addAction(show_action)
        tray_menu.addAction(reset_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_menu = tray_menu
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        if self._tray_available():
            self.tray_icon.show()
        else:
            self.minimize_button.setText("最小化窗口")
            self.minimize_button.setToolTip("当前系统未提供托盘区域，将使用普通窗口最小化。")

    @staticmethod
    def _tray_available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def _hide_to_tray(self) -> None:
        if self._tray_available():
            self.tray_icon.show()
            self.hide()
        else:
            self.showMinimized()

    def _restore_window(self) -> None:
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()
        if self.alert is not None and self.alert.isVisible():
            self.alert.raise_()
            self.alert.activateWindow()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._restore_window()

    def _quit_application(self) -> None:
        self._dismiss_alert()
        self.tray_icon.hide()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _build_time_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(14, 16, 14, 14)
        form.setVerticalSpacing(12)
        self.work_spin = self._minute_spin(0.1, 600)
        self.idle_spin = self._minute_spin(0.1, 120)
        self.rest_spin = self._minute_spin(0.1, 240)
        form.addRow("工作倒计时（分钟）", self.work_spin)
        form.addRow("静止后重置（分钟）", self.idle_spin)
        form.addRow("休息倒计时（分钟）", self.rest_spin)
        note = QLabel("鼠标移动后自动开始。专注期间静止达到阈值，本轮自动重置；休息阶段不受鼠标活动影响。")
        note.setWordWrap(True)
        form.addRow(note)
        return tab

    def _build_sound_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(14, 16, 14, 14)
        form.setVerticalSpacing(12)
        self.sound_edit = QLineEdit()
        self.sound_edit.setPlaceholderText("留空时使用系统提示音")
        form.addRow("自定义铃声", self._file_row(self.sound_edit, self._choose_sound))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setMinimumHeight(32)
        self.volume_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.volume_slider.setTickInterval(10)
        self.volume_slider.setAccessibleName("铃声音量")
        self.volume_value = QLabel()
        self.volume_slider.valueChanged.connect(lambda value: self.volume_value.setText(f"{value}%"))
        volume_row = QWidget()
        volume_layout = QHBoxLayout(volume_row)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_value)
        form.addRow("铃声音量", volume_row)
        self.top_checkbox = OptionToggle()
        self.top_checkbox.setToolTip("开启后，工作结束和休息结束提醒会保持在其他窗口前面。")
        form.addRow("提醒弹窗置顶", self.top_checkbox)
        note = QLabel("提醒需点击确认后关闭。确认工作结束提醒后，才开始休息计时。")
        note.setWordWrap(True)
        form.addRow(note)
        return tab

    def _build_system_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(14, 16, 14, 14)
        form.setVerticalSpacing(12)
        self.startup_checkbox = OptionToggle()
        self.startup_checkbox.setToolTip("开启后，登录 Windows 或 macOS 时自动运行番茄钟。")
        form.addRow("登录后自动启动", self.startup_checkbox)
        note = QLabel("此选项可自由开关，保存后生效。macOS 请先将应用移入“应用程序”并重新打开。\n\n点击一键最小化可在后台继续计时；关闭主窗口会退出应用。")
        note.setWordWrap(True)
        form.addRow(note)
        return tab

    def _build_appearance_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(14, 16, 14, 14)
        form.setVerticalSpacing(12)
        self.font_combo = QComboBox()
        self.font_combo.addItem("系统默认字体", "")
        for family in QFontDatabase.families():
            self.font_combo.addItem(family, family)
            self.font_combo.setItemData(self.font_combo.count() - 1, QFont(family), Qt.ItemDataRole.FontRole)
        form.addRow("界面字体", self.font_combo)
        self.text_color_edit = QLineEdit()
        self.text_color_button = QPushButton("选择颜色…")
        form.addRow("文字颜色", self._color_row(self.text_color_edit, self.text_color_button))
        self.accent_color_edit = QLineEdit()
        self.accent_color_button = QPushButton("选择颜色…")
        form.addRow("主题强调色", self._color_row(self.accent_color_edit, self.accent_color_button))
        self.main_background_edit = QLineEdit()
        self.main_background_edit.setPlaceholderText("留空时使用内置背景")
        form.addRow("主界面背景图", self._file_row(self.main_background_edit, self._choose_main_background))
        self.background_edit = QLineEdit()
        self.background_edit.setPlaceholderText("留空时使用内置背景")
        form.addRow("弹窗背景图", self._file_row(self.background_edit, self._choose_popup_background))
        note = QLabel("支持 PNG、JPG、BMP 和 WebP；图片会按窗口比例居中裁切。")
        note.setWordWrap(True)
        form.addRow("", note)
        return tab

    def _build_text_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(14, 12, 14, 12)
        form.setVerticalSpacing(8)
        self.work_title_edit = QLineEdit()
        self.work_message_edit = QPlainTextEdit()
        self.work_message_edit.setMaximumHeight(62)
        self.work_button_edit = QLineEdit()
        self.ready_title_edit = QLineEdit()
        self.ready_message_edit = QPlainTextEdit()
        self.ready_message_edit.setMaximumHeight(62)
        self.ready_button_edit = QLineEdit()
        form.addRow("工作结束标题", self.work_title_edit)
        form.addRow("工作结束正文", self.work_message_edit)
        form.addRow("工作结束按钮", self.work_button_edit)
        form.addRow("休息结束标题", self.ready_title_edit)
        form.addRow("休息结束正文", self.ready_message_edit)
        form.addRow("休息结束按钮", self.ready_button_edit)
        return tab

    @staticmethod
    def _minute_spin(minimum: float, maximum: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(1)
        spin.setSingleStep(0.5)
        spin.setSuffix(" 分钟")
        return spin

    @staticmethod
    def _file_row(edit: QLineEdit, callback: object) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        browse = QPushButton("选择…")
        browse.setObjectName("secondary")
        browse.clicked.connect(callback)  # type: ignore[arg-type]
        clear = QPushButton("清除")
        clear.setObjectName("secondary")
        clear.clicked.connect(edit.clear)
        layout.addWidget(edit, 1)
        layout.addWidget(browse)
        layout.addWidget(clear)
        return row

    def _color_row(self, edit: QLineEdit, button: QPushButton) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        button.setObjectName("secondary")
        button.clicked.connect(lambda: self._choose_color(edit, button))
        layout.addWidget(edit, 1)
        layout.addWidget(button)
        return row

    @staticmethod
    def _update_color_button(button: QPushButton, value: str) -> None:
        color = QColor(value)
        button.setStyleSheet(f"background: {color.name()}; color: {'black' if color.lightness() > 150 else 'white'};" if color.isValid() else "")

    def _choose_color(self, edit: QLineEdit, button: QPushButton) -> None:
        initial = QColor(edit.text()) if QColor(edit.text()).isValid() else QColor("#ffffff")
        color = QColorDialog.getColor(initial, self, "选择颜色")
        if color.isValid():
            edit.setText(color.name())
            self._update_color_button(button, color.name())

    def _load_settings_into_form(self) -> None:
        self.work_spin.setValue(self.settings.work_minutes)
        self.idle_spin.setValue(self.settings.idle_minutes)
        self.rest_spin.setValue(self.settings.rest_minutes)
        self.sound_edit.setText(self.settings.sound_path)
        self.background_edit.setText(self.settings.background_path)
        self.main_background_edit.setText(self.settings.main_background_path)
        self.volume_slider.setValue(self.settings.sound_volume)
        self.top_checkbox.setChecked(self.settings.always_on_top)
        self.startup_checkbox.setChecked(self.settings.start_on_login)
        font_index = self.font_combo.findData(self.settings.font_family)
        self.font_combo.setCurrentIndex(font_index if font_index >= 0 else 0)
        self.text_color_edit.setText(self.settings.text_color)
        self.accent_color_edit.setText(self.settings.accent_color)
        self._update_color_button(self.text_color_button, self.settings.text_color)
        self._update_color_button(self.accent_color_button, self.settings.accent_color)
        self.work_title_edit.setText(self.settings.work_alert_title)
        self.work_message_edit.setPlainText(self.settings.work_alert_message)
        self.work_button_edit.setText(self.settings.work_alert_button)
        self.ready_title_edit.setText(self.settings.ready_alert_title)
        self.ready_message_edit.setPlainText(self.settings.ready_alert_message)
        self.ready_button_edit.setText(self.settings.ready_alert_button)

    def _choose_sound(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择提醒铃声", self.sound_edit.text(), "音频文件 (*.mp3 *.wav *.m4a *.aac *.ogg *.flac);;所有文件 (*)")
        if path:
            self.sound_edit.setText(path)

    def _choose_image(self, title: str, current: str) -> str:
        path, _ = QFileDialog.getOpenFileName(self, title, current, "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*)")
        return path

    def _choose_main_background(self) -> None:
        path = self._choose_image("选择主界面背景图", self.main_background_edit.text())
        if path:
            self.main_background_edit.setText(path)

    def _choose_popup_background(self) -> None:
        path = self._choose_image("选择弹窗背景图", self.background_edit.text())
        if path:
            self.background_edit.setText(path)

    def _save_settings(self) -> None:
        file_fields = [
            (self.sound_edit.text().strip(), "铃声文件"),
            (self.main_background_edit.text().strip(), "主界面背景图片"),
            (self.background_edit.text().strip(), "弹窗背景图片"),
        ]
        for path, label in file_fields:
            if path and not Path(path).is_file():
                QMessageBox.warning(self, "文件不存在", f"选择的{label}不存在，请重新选择或清除。")
                return
        text_color = self.text_color_edit.text().strip()
        accent_color = self.accent_color_edit.text().strip()
        if not QColor(text_color).isValid() or not QColor(accent_color).isValid():
            QMessageBox.warning(self, "颜色无效", "请使用颜色选择器，或输入有效的颜色值，例如 #25302b。")
            return
        required = [
            self.work_title_edit.text().strip(), self.work_button_edit.text().strip(),
            self.ready_title_edit.text().strip(), self.ready_button_edit.text().strip(),
        ]
        if not all(required):
            QMessageBox.warning(self, "文字不能为空", "两个弹窗的标题和确认按钮文字不能为空。")
            return

        self.settings = AppSettings(
            work_minutes=self.work_spin.value(), idle_minutes=self.idle_spin.value(), rest_minutes=self.rest_spin.value(),
            sound_path=file_fields[0][0], background_path=file_fields[2][0], sound_volume=self.volume_slider.value(),
            always_on_top=self.top_checkbox.isChecked(), start_on_login=self.startup_checkbox.isChecked(),
            font_family=self.font_combo.currentData() or "", text_color=QColor(text_color).name(), accent_color=QColor(accent_color).name(),
            main_background_path=file_fields[1][0], work_alert_title=required[0],
            work_alert_message=self.work_message_edit.toPlainText().strip(), work_alert_button=required[1],
            ready_alert_title=required[2], ready_alert_message=self.ready_message_edit.toPlainText().strip(), ready_alert_button=required[3],
        )
        try:
            self.settings.save()
            set_start_on_login(self.settings.start_on_login)
        except OSError as exc:
            QMessageBox.critical(self, "保存失败", f"无法保存设置：{exc}")
            return
        except AutostartError as exc:
            self.settings.start_on_login = False
            self.startup_checkbox.setChecked(False)
            self.settings.save()
            QMessageBox.warning(self, "开机启动设置失败", str(exc))

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_style(self.settings))
        self.central_background.set_background(self.settings.main_background_path)
        self._fit_settings_page(self.tabs.currentIndex())
        self._dismiss_alert()
        self.engine = self._new_engine()
        self.last_cursor_position = QCursor.pos()
        self._refresh()
        self.statusBar().showMessage("设置已保存，正在等待鼠标移动", 4000)

    def _manual_reset(self) -> None:
        self._dismiss_alert()
        self.engine.reset()
        self.last_cursor_position = QCursor.pos()
        self._refresh()

    def _dismiss_alert(self) -> None:
        self.sound.stop()
        if self.alert is not None:
            self.alert.confirmed.disconnect()
            self.alert.done(QDialog.DialogCode.Rejected)
            self.alert.deleteLater()
            self.alert = None

    def _poll(self) -> None:
        now = time.monotonic()
        current = QCursor.pos()
        moved = False
        if self.last_cursor_position is not None:
            delta = current - self.last_cursor_position
            moved = abs(delta.x()) + abs(delta.y()) >= self.MOVE_THRESHOLD
        self.last_cursor_position = current
        event = self.engine.mouse_moved(now) if moved else Event.NONE
        if event is Event.WORK_STARTED:
            self.statusBar().showMessage("检测到鼠标移动，已自动开始专注计时", 3000)
        event = self.engine.tick(now)
        if event is Event.IDLE_RESET:
            self.last_cursor_position = current
            self.statusBar().showMessage("鼠标静止时间达到阈值，本轮已自动重置", 5000)
        elif event is Event.WORK_FINISHED:
            self._show_work_alert()
        elif event is Event.REST_FINISHED:
            self._show_ready_alert()
        self._refresh(now)

    def _show_alert(self, title: str, message: str, button: str, callback: object) -> None:
        self.sound.start(self.settings.sound_path, self.settings.sound_volume)
        self.alert = AlertDialog(
            title, message, button, self.settings.background_path, self.settings.always_on_top,
            self.settings.text_color, self.settings.font_family, self,
        )
        self.alert.confirmed.connect(callback)  # type: ignore[arg-type]
        self.alert.show()
        self.alert.raise_()
        self.alert.activateWindow()

    def _show_work_alert(self) -> None:
        self._show_alert(self.settings.work_alert_title, self.settings.work_alert_message, self.settings.work_alert_button, self._confirm_work_alert)

    def _confirm_work_alert(self) -> None:
        self.sound.stop()
        self.engine.confirm_work_alert(time.monotonic())
        self.alert = None
        self._refresh()

    def _show_ready_alert(self) -> None:
        self._show_alert(self.settings.ready_alert_title, self.settings.ready_alert_message, self.settings.ready_alert_button, self._confirm_ready_alert)

    def _confirm_ready_alert(self) -> None:
        self.sound.stop()
        self.engine.confirm_ready_alert()
        self.alert = None
        self.last_cursor_position = QCursor.pos()
        self._refresh()

    def _refresh(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.status_label.setText(self.STATUS_TEXT[self.engine.phase])
        remaining = self.engine.remaining_seconds(now)
        if self.engine.phase is Phase.WAITING:
            self.clock_label.setText("等待中")
        elif self.engine.phase in (Phase.WORK_ALERT, Phase.READY_ALERT):
            self.clock_label.setText("请确认")
        else:
            self.clock_label.setText(format_time(remaining))
        self._refresh_presentation(remaining)
        if hasattr(self, "tray_status_action"):
            status = self.STATUS_TEXT[self.engine.phase]
            clock = self.clock_label.text()
            self.tray_status_action.setText(f"状态：{status} · {clock}")
            self.tray_icon.setToolTip(f"自动番茄钟\n{status} · {clock}")

    def _refresh_presentation(self, remaining: int | None) -> None:
        """Project existing engine state onto the botanical observation card."""
        phase = self.engine.phase
        waiting = phase in (Phase.WAITING, Phase.WORK_ALERT, Phase.READY_ALERT)
        if self.clock_label.property("waiting") != waiting:
            self.clock_label.setProperty("waiting", waiting)
            self.clock_label.style().unpolish(self.clock_label)
            self.clock_label.style().polish(self.clock_label)
        imminent = phase is Phase.WORKING and remaining is not None and remaining <= 60
        if self.phase_note.property("imminent") != imminent:
            self.phase_note.setProperty("imminent", imminent)
            self.phase_note.style().unpolish(self.phase_note)
            self.phase_note.style().polish(self.phase_note)
        tags = {
            Phase.WAITING: ("OBSERVATION / 等待活动", "让专注自然开始"),
            Phase.WORKING: ("FOCUS CYCLE / 专注周期", "即将休息 · 本轮剩余不超过一分钟" if imminent else "心无旁骛，循序而行"),
            Phase.WORK_ALERT: ("INTERVAL / 休息提醒", "确认提醒后，开始休息"),
            Phase.RESTING: ("REST INTERVAL / 休息时间", "休息一下，放松身心"),
            Phase.READY_ALERT: ("NEW CYCLE / 下一轮", "确认提醒后，等待新的鼠标活动"),
        }
        tag, note = tags[phase]
        self.phase_tag.setText(tag)
        self.phase_note.setText(note)
        self.metrics.setText(f"专注  {self.settings.work_minutes:g} 分钟     /     休息  {self.settings.rest_minutes:g} 分钟\n静止 {self.settings.idle_minutes:g} 分钟后重置")
        duration = self.engine.durations.rest_seconds if phase is Phase.RESTING else self.engine.durations.work_seconds
        progress = 1 - remaining / duration if remaining is not None and duration > 0 else 0
        if phase in (Phase.WORK_ALERT, Phase.READY_ALERT):
            progress = 1
        self.specimen.set_visual(progress, phase is Phase.RESTING, imminent,
                                 valid_color(self.settings.accent_color, TOKENS.green))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.sound.stop()
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            app.quit()
