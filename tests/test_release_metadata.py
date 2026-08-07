import unittest
from pathlib import Path

from pomodoro import __version__


ROOT = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def test_official_version_is_consistent(self) -> None:
        self.assertEqual(__version__, "1.0.0")
        self.assertIn('setApplicationVersion("1.0.0")', (ROOT / "main.py").read_text(encoding="utf-8"))
        self.assertIn('#define MyAppVersion "1.0.0"', (ROOT / "windows-installer.iss").read_text(encoding="utf-8"))
        self.assertIn("CFBundleShortVersionString 1.0.0", (ROOT / "build-macos.command").read_text(encoding="utf-8"))

    def test_release_notice_and_icons_are_present(self) -> None:
        notice = (ROOT / "NOTICE.txt").read_text(encoding="utf-8")
        self.assertIn("九号飞船 With ChatGPT Codex", notice)
        self.assertIn("请立即退款", notice)
        self.assertIn("Free to use", notice)
        self.assertTrue((ROOT / "assets" / "AutoPomodoro.icns").is_file())
        self.assertTrue((ROOT / "assets" / "AutoPomodoro.ico").is_file())


if __name__ == "__main__":
    unittest.main()
