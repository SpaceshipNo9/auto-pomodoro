#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
BUILD_PYTHON="$(pwd)/.venv/bin/python3"
if [[ ! -x "$BUILD_PYTHON" ]]; then
  BUILD_PYTHON="python3"
fi
export PYINSTALLER_CONFIG_DIR="$(pwd)/build/pyinstaller-cache"
"$BUILD_PYTHON" -m pip install -r requirements-dev.txt
ICON_ARGS=()
if [[ -f "assets/AutoPomodoro.icns" ]]; then
  ICON_ARGS=(--icon "assets/AutoPomodoro.icns")
fi
"$BUILD_PYTHON" -m PyInstaller --noconfirm --clean --windowed --name "AutoPomodoro" --target-architecture universal2 --osx-bundle-identifier "com.personaltools.autopomodoro" --add-data "assets/app-icon.svg:assets" "${ICON_ARGS[@]}" main.py
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName 自动番茄钟" "dist/AutoPomodoro.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString 1.0.0" "dist/AutoPomodoro.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleVersion string 1" "dist/AutoPomodoro.app/Contents/Info.plist" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :CFBundleVersion 1" "dist/AutoPomodoro.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :NSHumanReadableCopyright string 本软件由九号飞船 With ChatGPT Codex 开发，免费使用。" "dist/AutoPomodoro.app/Contents/Info.plist" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :NSHumanReadableCopyright 本软件由九号飞船 With ChatGPT Codex 开发，免费使用。" "dist/AutoPomodoro.app/Contents/Info.plist"
codesign --force --deep --sign - "dist/AutoPomodoro.app"

DMG_ROOT="build/dmg-root"
rm -rf "$DMG_ROOT"
mkdir -p "$DMG_ROOT"
cp -R "dist/AutoPomodoro.app" "$DMG_ROOT/"
ln -s /Applications "$DMG_ROOT/Applications"
rm -f "dist/AutoPomodoro-macOS-Universal.dmg"
hdiutil create -volname "AutoPomodoro" -srcfolder "$DMG_ROOT" -ov -format UDZO "dist/AutoPomodoro-macOS-Universal.dmg"
echo "Build complete: dist/AutoPomodoro.app"
echo "Installer complete: dist/AutoPomodoro-macOS-Universal.dmg"
