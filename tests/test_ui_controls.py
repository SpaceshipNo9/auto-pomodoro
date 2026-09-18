import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

from pomodoro.settings import AppSettings  # noqa: E402
from pomodoro.engine import Phase  # noqa: E402
from pomodoro.ui import AlertDialog, MainWindow, OptionToggle  # noqa: E402


class OptionToggleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_entire_center_area_toggles_setting(self) -> None:
        toggle = OptionToggle()
        toggle.resize(600, 40)
        toggle.show()
        self.app.processEvents()
        self.assertFalse(toggle.isChecked())
        QTest.mouseClick(toggle, Qt.MouseButton.LeftButton, pos=toggle.rect().center())
        self.assertTrue(toggle.isChecked())
        self.assertIn("已开启", toggle.text())
        QTest.mouseClick(toggle, Qt.MouseButton.LeftButton, pos=toggle.rect().center())
        self.assertFalse(toggle.isChecked())
        self.assertIn("已关闭", toggle.text())
        toggle.close()

    def test_both_options_toggle_and_are_saved(self) -> None:
        with patch("pomodoro.ui.AppSettings.load", return_value=AppSettings()):
            window = MainWindow()
        window.show()
        self.app.processEvents()
        self.assertTrue(window.top_checkbox.isChecked())
        self.assertFalse(window.startup_checkbox.isChecked())
        self.assertEqual(window.font_combo.currentData(), "")
        window.tabs.setCurrentIndex(1)
        self.app.processEvents()
        self.assertTrue(window.top_checkbox.isVisible())
        QTest.mouseClick(window.top_checkbox, Qt.MouseButton.LeftButton, pos=window.top_checkbox.rect().center())
        window.tabs.setCurrentIndex(4)
        self.app.processEvents()
        self.assertTrue(window.startup_checkbox.isVisible())
        QTest.mouseClick(window.startup_checkbox, Qt.MouseButton.LeftButton, pos=window.startup_checkbox.rect().center())
        with patch.object(AppSettings, "save"), patch("pomodoro.ui.set_start_on_login") as startup:
            window._save_settings()
        self.assertFalse(window.settings.always_on_top)
        self.assertTrue(window.settings.start_on_login)
        self.assertEqual(window.settings.font_family, "")
        startup.assert_called_once_with(True)
        window.close()

    def test_visual_refresh_preserves_engine_and_settings(self) -> None:
        with patch("pomodoro.ui.AppSettings.load", return_value=AppSettings()):
            window = MainWindow()
        window.poll_timer.stop()
        window.engine.mouse_moved(0)
        before = (window.engine.deadline, window.engine.last_mouse_move, vars(window.settings).copy())
        window._refresh(1470)
        self.assertEqual(window.clock_label.text(), "00:30")
        self.assertTrue(window.phase_note.property("imminent"))
        self.assertEqual(window.engine.phase, Phase.WORKING)
        self.assertEqual(before, (window.engine.deadline, window.engine.last_mouse_move, vars(window.settings)))
        window.engine.tick(1500)
        window.engine.phase = Phase.WORK_ALERT
        window.engine.confirm_work_alert(1500)
        window._refresh(1510)
        self.assertTrue(window.specimen.resting)
        self.assertFalse(window.phase_note.property("imminent"))
        window.close()

    def test_small_window_all_settings_remain_accessible(self) -> None:
        with patch("pomodoro.ui.AppSettings.load", return_value=AppSettings()):
            window = MainWindow()
        window.resize(680, 540)
        window.show()
        for index in range(window.tabs.count()):
            window.tabs.setCurrentIndex(index)
            self.app.processEvents()
            self.assertEqual(window.scroll.horizontalScrollBar().maximum(), 0)
            self.assertGreaterEqual(window.tabs.currentWidget().height(), window.tabs.currentWidget().minimumSizeHint().height())
        window.scroll.ensureWidgetVisible(window.findChild(QLabel, "credit"))
        self.app.processEvents()
        credit = window.findChild(QLabel, "credit")
        position = credit.mapTo(window.scroll.viewport(), credit.rect().center())
        self.assertTrue(window.scroll.viewport().rect().contains(position))
        window.close()

    def test_custom_popup_text_is_literal_and_wrapped(self) -> None:
        title = "<b>休息 & 放松</b> " * 4
        dialog = AlertDialog(title, "<i>自定义文字</i>", "确认", "", False, "#25302b", "")
        label = next(label for label in dialog.findChildren(QLabel) if label.text() == title)
        self.assertEqual(label.textFormat(), Qt.TextFormat.PlainText)
        self.assertTrue(label.wordWrap())
        dialog.accept()

    def test_alert_cannot_be_rejected_but_confirmation_closes_it(self) -> None:
        dialog = AlertDialog(
            "测试标题", "测试正文", "必须确认", "", False,
            "#25302b", QApplication.font().family(),
        )
        confirmations = []
        dialog.confirmed.connect(lambda: confirmations.append(True))
        dialog.show()
        self.app.processEvents()
        dialog.reject()
        self.assertTrue(dialog.isVisible())
        button = next(item for item in dialog.findChildren(QPushButton) if item.text() == "必须确认")
        QTest.mouseClick(button, Qt.MouseButton.LeftButton, pos=button.rect().center())
        self.assertEqual(confirmations, [True])
        self.assertFalse(dialog.isVisible())

    def test_one_click_tray_minimize_and_restore(self) -> None:
        with patch("pomodoro.ui.AppSettings.load", return_value=AppSettings()):
            window = MainWindow()
        window.show()
        self.app.processEvents()
        self.assertTrue(window.isVisible())
        with patch.object(window, "_tray_available", return_value=True):
            QTest.mouseClick(window.minimize_button, Qt.MouseButton.LeftButton, pos=window.minimize_button.rect().center())
        self.assertFalse(window.isVisible())
        self.assertTrue(window.poll_timer.isActive())
        window._restore_window()
        self.assertTrue(window.isVisible())
        menu_items = [action.text() for action in window.tray_menu.actions()]
        self.assertIn("显示主界面", menu_items)
        self.assertIn("重置并等待鼠标移动", menu_items)
        self.assertIn("退出自动番茄钟", menu_items)
        window.close()

    def test_official_free_use_notice_is_visible_and_bilingual(self) -> None:
        with patch("pomodoro.ui.AppSettings.load", return_value=AppSettings()):
            window = MainWindow()
        window.show()
        self.app.processEvents()
        credit = window.findChild(QLabel, "credit")
        self.assertIsNotNone(credit)
        self.assertTrue(credit.isVisible())
        self.assertIn("九号飞船 With ChatGPT Codex", credit.text())
        self.assertIn("请立即退款", credit.text())
        self.assertIn("Free to use", credit.text())
        self.assertIn("immediate refund", credit.text())
        window.close()


if __name__ == "__main__":
    unittest.main()
