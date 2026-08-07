import plistlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pomodoro import autostart


class AutostartTests(unittest.TestCase):
    def test_macos_launch_agent_is_created_and_removed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            with patch.object(autostart.sys, "platform", "darwin"), \
                    patch.object(autostart.Path, "home", return_value=home), \
                    patch.object(autostart.sys, "frozen", True, create=True), \
                    patch.object(autostart.sys, "executable", sys.executable):
                autostart.set_start_on_login(True)
                plist_path = home / "Library" / "LaunchAgents" / f"{autostart.APP_ID}.plist"
                payload = plistlib.loads(plist_path.read_bytes())
                self.assertTrue(payload["RunAtLoad"])
                self.assertEqual(payload["ProgramArguments"], [str(Path(sys.executable).resolve())])
                autostart.set_start_on_login(False)
                self.assertFalse(plist_path.exists())

    def test_macos_rejects_temporary_dmg_path(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            temporary_app = "/Volumes/AutoPomodoro/AutoPomodoro.app/Contents/MacOS/AutoPomodoro"
            with patch.object(autostart.sys, "platform", "darwin"), \
                    patch.object(autostart.Path, "home", return_value=home), \
                    patch.object(autostart.sys, "frozen", True, create=True), \
                    patch.object(autostart.sys, "executable", temporary_app):
                with self.assertRaisesRegex(autostart.AutostartError, "应用程序"):
                    autostart.set_start_on_login(True)


if __name__ == "__main__":
    unittest.main()
