# AutoPomodoro · Botanical observation card

The desktop UI combines clean botanical plate illustrations with a restrained modern layout. Native Qt/PySide6 remains the UI framework.

## Design system

`pomodoro/design.py` owns the palette, typography, reusable stylesheet and vector specimen widget. Warm white `#faf9f5`, cream `#fffaf0`, botanical green `#1f6d55`, coral `#db6554` and ink `#25302b` define the default palette. Coral text uses a darker `#a54436` for contrast. Panels use a 1 px rule, 10 px radius and 16 px spacing, with no shadow.

The clock and English brand use the first installed font among Baskerville, Georgia and Times New Roman. Form controls use the system sans-serif font. A user-selected font overrides both. User-selected text and accent colors remain supported. Existing settings and defaults are not migrated or overwritten.

The specimen is drawn with QPainter rather than a poster bitmap: coral rounded-square body, botanical leaf crown, cream face, green ring and hands. Sparse hatching and measurement lines provide the plate reference without competing with the timer. The alert uses a small outline variant. Ring-color transitions last 220 ms with an ease-out curve; there is no continuous animation or separate timing source.

## Screens and behavior

- Main observation card: existing status, remaining time, configured work/rest/idle durations, manual reset and tray minimize.
- Settings: 01 time, 02 reminders, 03 appearance, 04 popup text, 05 system. The existing setting widgets and save action are reused. Only the selected form determines the tab panel height; the outer window scrolls on small displays.
- Last minute: a coral ring and a short informational label. This is presentation only, not a new engine phase.
- Rest: the specimen is visually subdued and the existing rest countdown remains visible.
- Alert: clean outline specimen, the user's title/message and existing mandatory confirmation action. Popup background images and optional always-on-top behavior are retained. User-provided text is rendered literally and wraps.

There is no new pause, skip, early-rest or notification behavior. `engine.py`, `settings.py`, `autostart.py`, audio playback and platform tray behavior retain their previous logic.

## Run and inspect

From the project directory:

```sh
.venv/bin/python3 main.py
QT_QPA_PLATFORM=offscreen .venv/bin/python3 -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen .venv/bin/python3 tools/preview_botanical.py
```

On Windows, use `.venv\Scripts\python.exe` instead of `.venv/bin/python3`.

The preview utility renders actual Qt widgets into `preview/`, including waiting, focus, the final minute, rest, all settings tabs, a small window and the confirmation alert. It mocks settings loading, stops cursor polling and never saves preferences or changes startup entries. Omit `QT_QPA_PLATFORM=offscreen` for native desktop captures.

Validated on macOS using both offscreen Qt and native Qt/Retina rendering. Windows-specific behavior is preserved in code; a native Windows visual pass remains necessary before distributing a new Windows release. Existing installed binaries are not replaced by editing this source tree.
