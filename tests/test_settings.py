import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pomodoro.settings import AppSettings


class AppSettingsTests(unittest.TestCase):
    def test_old_settings_are_migrated_with_new_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps({"work_minutes": 40, "background_path": "/tmp/popup.png"}), encoding="utf-8")
            with patch("pomodoro.settings.settings_path", return_value=path):
                settings = AppSettings.load()
        self.assertEqual(settings.work_minutes, 40)
        self.assertEqual(settings.background_path, "/tmp/popup.png")
        self.assertEqual(settings.main_background_path, "")
        self.assertFalse(settings.start_on_login)
        self.assertEqual(settings.work_alert_title, "该休息了")

    def test_custom_fields_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            settings = AppSettings(
                font_family="PingFang SC",
                text_color="#123456",
                accent_color="#654321",
                main_background_path="/tmp/main.png",
                ready_alert_title="回来吧",
            )
            with patch("pomodoro.settings.settings_path", return_value=path):
                settings.save()
                loaded = AppSettings.load()
        self.assertEqual(loaded.font_family, "PingFang SC")
        self.assertEqual(loaded.text_color, "#123456")
        self.assertEqual(loaded.main_background_path, "/tmp/main.png")
        self.assertEqual(loaded.ready_alert_title, "回来吧")

    def test_corrupted_types_and_out_of_range_values_are_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps({
                "work_minutes": "not-a-number",
                "idle_minutes": -30,
                "rest_minutes": 99999,
                "sound_volume": 800,
                "start_on_login": "yes",
            }), encoding="utf-8")
            with patch("pomodoro.settings.settings_path", return_value=path):
                loaded = AppSettings.load()
        self.assertEqual(loaded.work_minutes, 25.0)
        self.assertEqual(loaded.idle_minutes, 0.1)
        self.assertEqual(loaded.rest_minutes, 240.0)
        self.assertEqual(loaded.sound_volume, 100)
        self.assertFalse(loaded.start_on_login)

    def test_non_object_json_falls_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text("[]", encoding="utf-8")
            with patch("pomodoro.settings.settings_path", return_value=path):
                loaded = AppSettings.load()
        self.assertEqual(loaded, AppSettings())


if __name__ == "__main__":
    unittest.main()
