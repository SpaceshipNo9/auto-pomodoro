"""Botanical plate design system. Presentation only; no timer state is owned here."""
from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFontDatabase, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class Tokens:
    paper: str = "#faf9f5"
    cream: str = "#fffaf0"
    green: str = "#1f6d55"
    coral: str = "#db6554"
    coral_text: str = "#a54436"
    ink: str = "#25302b"
    muted: str = "#647168"
    rule: str = "#d4dbd0"
    quiet: str = "#edf1e9"
    radius: int = 10
    spacing: int = 16
    transition_ms: int = 220
    # Thin rules, not drop shadows, define the panels.
    border_px: int = 1
    shadow: str = "none"


TOKENS = Tokens()


def serif_family() -> str:
    available = set(QFontDatabase.families())
    return next((name for name in ("Baskerville", "Georgia", "Times New Roman") if name in available), "serif")


def stylesheet(text: str, accent: str, font: str, serif: str) -> str:
    t = TOKENS
    hover = QColor(accent).darker(112).name()
    return f'''
QWidget {{ color: {text}; font-family: "{font}"; font-size: 13px; }}
QMainWindow, QWidget#mainBackground {{ background: {t.paper}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QLabel {{ background: transparent; border: none; }}
QLabel#title {{ font-family: "{serif}"; font-size: 27px; color: {accent}; }}
QLabel#clock {{ font-family: "{serif}"; font-size: 64px; color: {accent}; }}
QLabel#clock[waiting="true"] {{ font-family: "{font}"; font-size: 36px; }}
QLabel#status {{ font-size: 15px; }}
QLabel#folio, QLabel#eyebrow {{ color: {t.muted}; font-size: 10px; letter-spacing: 2px; }}
QLabel#phaseNote {{ color: {t.muted}; font-size: 12px; }}
QLabel#phaseNote[imminent="true"] {{ color: {t.coral_text}; }}
QLabel#metrics {{ color: {text}; padding: 10px 0; border-top: 1px solid {t.rule}; }}
QLabel#hint {{ color: {t.muted}; font-size: 11px; background: rgba(250,249,245,235); padding: 5px; }}
QLabel#credit {{ color: {text}; background: rgba(250,249,245,235); font-size: 10px; padding: 5px; }}
QFrame#card {{ background: rgba(255,254,250,235); border: 1px solid {t.rule}; border-radius: {t.radius}px; }}
QLabel#sectionTitle {{ color: {accent}; font-size: 16px; font-weight: 600; }}
QPushButton {{ background: {accent}; color: {t.cream}; border: 1px solid {accent}; border-radius: 7px; padding: 9px 14px; min-height: 18px; font-weight: 500; }}
QPushButton:hover {{ background: {hover}; }}
QPushButton:pressed {{ background: {QColor(accent).darker(130).name()}; }}
QPushButton:focus {{ border: 2px solid {t.coral}; padding: 8px 13px; }}
QPushButton:disabled {{ background: {t.quiet}; color: {t.muted}; border-color: {t.rule}; }}
QPushButton#secondary {{ background: {t.paper}; color: {text}; border: 1px solid {t.rule}; }}
QPushButton#secondary:hover {{ background: {t.quiet}; border-color: {accent}; }}
QLineEdit, QPlainTextEdit, QDoubleSpinBox, QComboBox {{ background: {t.paper}; border: 1px solid {t.rule}; border-radius: 5px; padding: 7px; min-height: 18px; selection-background-color: {accent}; selection-color: {t.cream}; }}
QLineEdit:focus, QPlainTextEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {accent}; background: #ffffff; }}
QComboBox QAbstractItemView {{ background: {t.paper}; color: {text}; selection-background-color: {accent}; selection-color: {t.cream}; }}
QTabWidget::pane {{ border: none; border-top: 1px solid {t.rule}; background: transparent; }}
QTabBar::tab {{ background: transparent; color: {t.muted}; padding: 11px 14px; border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {accent}; border-bottom-color: {accent}; background: {t.quiet}; }}
QTabBar::tab:hover {{ color: {accent}; background: {t.quiet}; }}
QPushButton#optionToggle {{ background: {t.cream}; color: {text}; border: 1px solid {t.rule}; text-align: left; padding: 8px 14px; }}
QPushButton#optionToggle:checked {{ background: {accent}; color: {t.cream}; border-color: {accent}; }}
QPushButton#optionToggle:hover, QPushButton#optionToggle:focus {{ border-color: {t.coral}; }}
QSlider::groove:horizontal {{ height: 3px; background: {t.rule}; border-radius: 1px; }}
QSlider::sub-page:horizontal {{ background: {accent}; }}
QSlider::handle:horizontal {{ background: {t.cream}; border: 2px solid {accent}; width: 16px; height: 16px; margin: -8px 0; border-radius: 9px; }}
QSlider::handle:horizontal:hover {{ background: {t.quiet}; }}
QSlider:focus {{ background: {t.quiet}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #b7c3b8; border-radius: 4px; min-height: 28px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QStatusBar {{ background: {t.paper}; color: {t.muted}; font-size: 11px; }}
QMenu {{ background: {t.paper}; border: 1px solid {t.rule}; padding: 6px; }}
QMenu::item {{ padding: 7px 18px; }}
QMenu::item:selected {{ background: {t.quiet}; color: {accent}; }}
'''


class SpecimenWidget(QWidget):
    """Scalable engraved tomato mark and a read-only progress ring."""

    def __init__(self, parent=None, compact=False):
        super().__init__(parent)
        self.compact = compact
        self.setMinimumSize(72, 72) if compact else self.setMinimumSize(160, 170)
        self.progress = 0.0
        self.resting = False
        self.ink_only = compact
        self.accent = QColor(TOKENS.green)
        self._ring_color = QColor(TOKENS.green)
        self._target_color = self._ring_color
        self._transition = QVariantAnimation(self)
        self._transition.setDuration(TOKENS.transition_ms)
        self._transition.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._transition.valueChanged.connect(self._animate_color)
        self.setAccessibleName("番茄钟植物标本插画")

    def _animate_color(self, color):
        self._ring_color = color
        self.update()

    def set_visual(self, progress, resting=False, imminent=False, accent=TOKENS.green):
        self.progress = max(0.0, min(1.0, progress))
        self.resting = resting
        self.accent = QColor(accent)
        color = QColor(TOKENS.coral if imminent else accent)
        if color != self._target_color:
            self._target_color = color
            self._transition.stop()
            self._transition.setStartValue(self._ring_color)
            self._transition.setEndValue(color)
            self._transition.start()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        p.translate((self.width() - side) / 2, (self.height() - side) / 2)
        p.scale(side / 240, side / 240)
        green = self.accent
        ink = QColor(TOKENS.ink)
        if not self.compact:
            p.setPen(QPen(QColor(TOKENS.rule), 0.8, Qt.PenStyle.DashLine))
            p.drawLine(8, 120, 232, 120)
            p.drawLine(120, 8, 120, 232)
            p.setPen(QPen(QColor(TOKENS.rule), 1))
            p.drawEllipse(QRectF(9, 9, 222, 222))
            p.setPen(QPen(self._ring_color, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(9, 9, 222, 222), 90 * 16, -int(self.progress * 360 * 16))
        p.setOpacity(0.66 if self.resting else 1.0)
        body = QPainterPath()
        body.addRoundedRect(QRectF(40, 40, 160, 166), 37, 37)
        p.setPen(QPen(ink, 1.1))
        p.setBrush(QColor(TOKENS.cream if self.ink_only else TOKENS.coral))
        p.drawPath(body)
        # Sparse engraved strokes are clipped inside the tomato silhouette.
        p.save()
        p.setClipPath(body)
        hatch = QColor(TOKENS.ink)
        hatch.setAlpha(23)
        p.setPen(QPen(hatch, 0.65))
        for x in range(-120, 290, 7):
            p.drawLine(x, 206, x + 75, 160)
        p.restore()
        for mirror in (False, True):
            p.save()
            if mirror:
                p.translate(240, 0)
                p.scale(-1, 1)
            leaf = QPainterPath()
            leaf.moveTo(123, 95)
            leaf.cubicTo(103, 49, 79, 56, 60, 63)
            leaf.cubicTo(81, 66, 78, 92, 123, 95)
            p.setBrush(QColor(TOKENS.cream) if self.ink_only else green)
            p.setPen(QPen(ink, 0.9))
            p.drawPath(leaf)
            p.setPen(QPen(QColor(TOKENS.cream) if not self.ink_only else green, 0.65))
            p.drawLine(69, 64, 120, 92)
            for i in range(4):
                x = 83 + i * 7
                y = 72 + i * 4
                p.drawLine(x, y, x - 3, y - 10)
                p.drawLine(x, y, x - 9, y + 2)
            p.restore()
        p.setPen(QPen(ink, 1))
        p.setBrush(QColor(TOKENS.cream))
        p.drawEllipse(QRectF(61, 79, 118, 118))
        p.setPen(QPen(green, 6))
        p.drawEllipse(QRectF(72, 90, 96, 96))
        p.setPen(QPen(green, 0.8))
        for n in range(12):
            angle = n * math.pi / 6
            p.drawLine(int(120 + 40 * math.sin(angle)), int(138 - 40 * math.cos(angle)),
                       int(120 + 43 * math.sin(angle)), int(138 - 43 * math.cos(angle)))
        p.setPen(QPen(green, 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawLine(120, 107, 120, 138)
        p.drawLine(120, 138, 144, 155)
        p.setBrush(green)
        p.setPen(QPen(ink, 0.8))
        p.drawEllipse(QRectF(115, 133, 10, 10))
        p.end()
