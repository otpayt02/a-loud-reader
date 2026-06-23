"""tray.py -- system-tray UI for a-loud-reader.

This is a small `pystray` app that mirrors ``state/flags.json`` and lets the
user toggle the watcher without opening a terminal. The CLI remains the source
of truth; the tray only reads and writes the same JSON files.

Run with::

    python src/tray.py

The tray icon is drawn procedurally with PIL so we don't need to ship an
asset file. Right-click for the menu.
"""

# stdlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

# third-party
import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as Item

# Local: add src/ to sys.path so we can reuse state helpers from watcher.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import watcher as _watcher  # noqa: E402


# ---------------------------------------------------------------------------
# State read/write (delegates to watcher helpers, but flipped to be thread-safe)
# ---------------------------------------------------------------------------

def _read_flags():
    """Return the current flags dict, seeded with defaults if the file is missing."""
    return _watcher._flags_provider()


def _write_flags(flags):
    _watcher._write_json(_watcher.FLAGS_PATH, flags)


def _toggle(key, value=None):
    """Flip a boolean flag. If ``value`` is given, set to that; else invert."""
    flags = _read_flags()
    flags[key] = (value if value is not None else not bool(flags.get(key)))
    _write_flags(flags)


# ---------------------------------------------------------------------------
# Icon: 32x32 PNG, drawn with PIL so the repo ships no binary assets.
# ---------------------------------------------------------------------------

def _make_icon():
    """Return a 32x32 RGBA image used as the tray icon."""
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Outer ring (speaker body)
    draw.ellipse((4, 4, 28, 28), fill=(33, 150, 243, 255))
    # Sound waves (three arcs)
    for r in (8, 12, 16):
        draw.arc((16 - r, 16 - r, 16 + r, 16 + r), start=300, end=60, fill=(255, 255, 255, 255), width=2)
    return img


# ---------------------------------------------------------------------------
# Menu actions
# ---------------------------------------------------------------------------

def _action_on_off(icon, item):
    _toggle("master")


def _action_codex(icon, item):
    _toggle("codex")


def _action_clipboard(icon, item):
    _toggle("clipboard")


def _action_pause(icon, item):
    # Pause == set master=False but keep watcher running; resume flips back.
    _toggle("master", False)


def _action_resume(icon, item):
    _toggle("master", True)


def _action_voice(icon, item):
    """Cycle to the next voice in a curated short list."""
    voices = ["en-US-JennyNeural", "en-US-AriaNeural", "en-US-GuyNeural", "en-US-DavisNeural"]
    flags = _read_flags()
    cur = flags.get("voice", voices[0])
    idx = voices.index(cur) if cur in voices else -1
    flags["voice"] = voices[(idx + 1) % len(voices)]
    _write_flags(flags)


def _action_rate_up(icon, item):
    flags = _read_flags()
    flags["rate"] = "+" + str(min(50, int(str(flags.get("rate", "+0%")).strip("+%").replace("%", "")) + 5)) + "%"
    _write_flags(flags)


def _action_rate_down(icon, item):
    flags = _read_flags()
    cur = int(str(flags.get("rate", "+0%")).strip("+%").replace("%", "")) - 5
    flags["rate"] = "+" + str(max(-50, cur)) + "%"
    _write_flags(flags)


def _action_engine(icon, item):
    flags = _read_flags()
    flags["engine"] = "piper" if flags.get("engine", "edge") == "edge" else "edge"
    _write_flags(flags)


def _action_archive(icon, item):
    """Open the archive folder in Explorer."""
    archive = _watcher.ROOT / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(archive))  # type: ignore[attr-defined]


def _action_status(icon, item):
    flags = _read_flags()
    msg = (
        "a-loud-reader\n"
        "master:        " + str(flags.get("master")) + "\n"
        "codex:         " + str(flags.get("codex")) + "\n"
        "clipboard:     " + str(flags.get("clipboard")) + "\n"
        "engine/voice:  " + str(flags.get("engine")) + " / " + str(flags.get("voice")) + "\n"
        "rate:          " + str(flags.get("rate"))
    )
    # A tiny balloon notification in the system tray is the friendliest way to
    # surface status from a tray app. pystray exposes `notify` for that.
    try:
        icon.notify(msg, title="a-loud-reader")
    except Exception:
        pass


def _action_start(icon, item):
    """Boot the Python watcher as a detached process."""
    pid_file = _watcher.ROOT / "state" / "watcher.pid"
    if pid_file.exists():
        return
    py = sys.executable
    args = [py, "-u", str(_watcher.ROOT / "src" / "watcher.py"), "start"]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_watcher.ROOT / "src")
    subprocess.Popen(
        args,
        cwd=str(_watcher.ROOT),
        env=env,
        stdout=open(_watcher.ROOT / "state" / "watcher.log", "ab"),
        stderr=subprocess.STDOUT,
        creationflags=0x08000000 if os.name == "nt" else 0,
    )


def _action_stop(icon, item):
    """Kill the watcher by PID."""
    pid_file = _watcher.ROOT / "state" / "watcher.pid"
    if not pid_file.exists():
        return
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        else:
            os.kill(pid, 15)
    except Exception:
        pass
    pid_file.unlink(missing_ok=True)


def _action_quit(icon, item):
    icon.stop()


# ---------------------------------------------------------------------------
# Menu builder
# ---------------------------------------------------------------------------

def _checked(value):
    """Return a pystray checkmark lambda that reflects the live flag value."""
    return lambda item: bool(value)


def _build_menu(icon):
    """Rebuild the menu every tick so checkmarks stay in sync with flags.json."""
    flags = _read_flags()
    return pystray.Menu(
        Item("a-loud-reader", None, enabled=False),
        Item("On / Off", _action_on_off, checked=_checked(flags.get("master"))),
        Item(
            "Pause",
            _action_pause,
            visible=lambda item: bool(flags.get("master")),
        ),
        Item(
            "Resume",
            _action_resume,
            visible=lambda item: not bool(flags.get("master")),
        ),
        pystray.Menu.SEPARATOR,
        Item("Codex speaking", _action_codex, checked=_checked(flags.get("codex"))),
        Item("Clipboard speaking", _action_clipboard, checked=_checked(flags.get("clipboard"))),
        Item("Engine: " + str(flags.get("engine", "edge")), _action_engine),
        Item("Voice: " + str(flags.get("voice", "?")), _action_voice),
        Item(
            "Rate: " + str(flags.get("rate", "+0%")),
            pystray.Menu(
                Item("Faster", _action_rate_up),
                Item("Slower", _action_rate_down),
            ),
        ),
        pystray.Menu.SEPARATOR,
        Item("Start watcher", _action_start, visible=lambda item: not (_watcher.ROOT / "state" / "watcher.pid").exists()),
        Item("Stop watcher", _action_stop, visible=lambda item: (_watcher.ROOT / "state" / "watcher.pid").exists()),
        Item("Show status", _action_status),
        Item("Open archive folder", _action_archive),
        pystray.Menu.SEPARATOR,
        Item("Quit", _action_quit),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    icon = pystray.Icon("a-loud-reader", _make_icon(), "a-loud-reader")
    # pystray rebuilds the menu only when refreshed; we call update_menu() on a
    # 1-second timer so the checkmarks always reflect the live flags.json.
    def _refresh():
        while True:
            try:
                icon.update_menu()
            except Exception:
                pass
            time.sleep(1.0)

    threading.Thread(target=_refresh, daemon=True).start()
    icon.run(_build_menu)


if __name__ == "__main__":
    main()