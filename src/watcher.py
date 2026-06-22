"""watcher.py -- Codex inbox + clipboard listener for a-loud-reader.

Two background loops run in this process:

1. Inbox watcher -- tails ``inbox/inbox.md``. Codex (or any other source)
   appends turn lines like ``1p Hello`` or ``alpha:1r Hi``. We speak each new
   turn in order, persisting a cursor in ``state/positions.json`` so a restart
   resumes mid-thread.

2. Clipboard listener -- polls the system clipboard. When the latest text
   changes and the user has opted in (``clipboard`` flag), we speak it.
   Off by default; toggled with ``loud-reader clipboard on``.

State is shared with the PowerShell CLI via small JSON files under ``state/``.
The CLI flips flags there and the watcher reacts on its next tick.

Usage::

    python watcher.py start
    python watcher.py status
    python watcher.py stop
"""

# --- stdlib imports ---
import argparse
import ctypes
import ctypes.wintypes
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path

# --- third-party ---
import pyperclip
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# --- local (add src/ to sys.path so `import say` works when watcher.py is run as a script) ---
sys.path.insert(0, str(Path(__file__).resolve().parent))
import say  # noqa: E402


# ---------------------------------------------------------------------------
# Paths and configuration
# ---------------------------------------------------------------------------

# Repo root: assumes this script lives in `src/`.
ROOT = Path(__file__).resolve().parent.parent

# Where Codex drops new chat turns.
INBOX_PATH = ROOT / "inbox" / "inbox.md"

# Where clipboard captures accumulate for the day (rotates at midnight).
CLIPBOARD_LOG = ROOT / "data" / "clipboard.md"

# State files. JSON because the PowerShell CLI mutates them from another process.
STATE_DIR = ROOT / "state"
FLAGS_PATH = STATE_DIR / "flags.json"
POSITIONS_PATH = STATE_DIR / "positions.json"
PINNED_PATH = STATE_DIR / "pinned.json"

# How often the clipboard poller wakes up. 400 ms is responsive without thrash.
CLIPBOARD_POLL_S = 0.4

# Regex for a Codex turn line. Optional ``thread:`` prefix, then ``<N><p|r>``.
# Examples: ``1p Hello``, ``alpha:1r Hi``, ``work-thread:12p Notes``.
TURN_RE = re.compile(
    r"^(?:(?P<thread>[\w\-]+):)?(?P<idx>\d+)(?P<kind>[pr])\s+(?P<body>.*)$"
)


# ---------------------------------------------------------------------------
# JSON helpers (shared with the PowerShell CLI)
# ---------------------------------------------------------------------------

def _read_json(path: Path, default):
    """Read a JSON file or return ``default`` if missing/corrupt.

    We use ``utf-8-sig`` so a stray BOM doesn't crash the watcher (PowerShell
    writes BOM by default and that previously broke the pin_threads check).
    """
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data) -> None:
    """Atomic JSON write: write to ``.tmp`` then rename. No half-written files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _default_flags():
    """Initial on/off state. Matches what the user asked for."""
    return {
        "master": True,
        "codex": True,
        "clipboard": False,
        "archive_mp3": True,
        "pin_threads": {},
        "engine": "edge",
        "piper_model": "",
        "voice": "en-US-JennyNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
    }


def _today_str():
    """Local-date string used to rotate the daily clipboard log and MP3 archive."""
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# Inbox parsing
# ---------------------------------------------------------------------------

def parse_inbox(text):
    """Parse inbox markdown into a sorted list of turn dicts."""
    turns = []
    for raw in text.splitlines():
        m = TURN_RE.match(raw.strip())
        if not m:
            continue
        turns.append({
            "thread": m.group("thread") or "default",
            "idx": int(m.group("idx")),
            "kind": m.group("kind"),
            "body": m.group("body").strip(),
        })
    turns.sort(key=lambda t: (t["idx"], t["kind"]))
    return turns


# ---------------------------------------------------------------------------
# TTS + playback
# ---------------------------------------------------------------------------

def _speak(text, flags, thread="default"):
    """Synthesize ``text`` and play it in the background.

    The MP3 path depends on whether the thread is pinned:
      - pinned thread -> ``archive/pinned/<thread>/...``
      - default thread -> ``archive/YYYY-MM-DD/...``

    Playback always uses the headless ``winmm`` MCI path so no GUI ever pops up.
    """
    if not text.strip():
        return
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", text[:40]).strip("_") or "turn"
    pinned = bool(flags.get("pin_threads", {}).get(thread, False))
    if flags.get("archive_mp3", True):
        if pinned:
            out_dir = ROOT / "archive" / "pinned" / thread
        else:
            out_dir = ROOT / "archive" / _today_str()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{int(time.time() * 1000)}_{safe}.mp3"
    else:
        out_path = ROOT / "archive" / "_tmp.mp3"

    try:
        # Engine dispatch. We mutate say._ENGINE / say._PIPER_MODEL so the
        # existing synth() call picks the right backend.
        engine = flags.get("engine", "edge")
        if engine == "piper":
            say._ENGINE = "piper"
            say._PIPER_MODEL = flags.get("piper_model") or say.DEFAULT_PIPER_MODEL
        else:
            say._ENGINE = "edge"
        say.synth(
            text=text,
            voice=flags.get("voice", "en-US-JennyNeural"),
            rate=flags.get("rate", "+0%"),
            pitch=flags.get("pitch", "+0Hz"),
            out_path=str(out_path),
        )
        _play_in_background(str(out_path))
    except Exception as e:  # noqa: BLE001
        print("[warn] edge-tts failed:", e, file=sys.stderr)
        _sapi_speak(text)


def _play_in_background(mp3_path):
    """Play an MP3 in the background without ever showing a window.

    Strategy (in order):
      1. winmm.mciSendStringW -- built into every Windows install, truly headless.
      2. pygame.mixer if installed -- simple, headless, cross-platform.
      3. playsound if installed -- pure-Python fallback.

    We never raise out of this function; worst case the MP3 sits in archive/.
    """
    if os.name == "nt":
        try:
            winmm = ctypes.WinDLL("winmm")
            alias = f"alr_{int(time.time() * 1000) % 100000}"
            quoted = mp3_path.replace(chr(34), chr(92) + chr(34))
            send = winmm.mciSendStringW
            send.argtypes = [
                ctypes.wintypes.LPCWSTR,
                ctypes.wintypes.LPWSTR,
                ctypes.c_uint,
                ctypes.c_void_p,
            ]
            send.restype = ctypes.c_uint
            buf = ctypes.create_unicode_buffer(256)
            cmd_open = 'open "' + quoted + '" type mpegvideo alias ' + alias
            cmd_play = "play " + alias
            send(cmd_open, buf, 255, None)
            send(cmd_play, buf, 255, None)
            return
        except Exception as e:
            print("[warn] winmm MCI play failed:", e, file=sys.stderr)

    try:
        import pygame  # type: ignore
        pygame.mixer.init()
        pygame.mixer.music.load(mp3_path)
        pygame.mixer.music.play()
        return
    except Exception:
        pass

    try:
        from playsound import playsound  # type: ignore
        threading.Thread(target=playsound, args=(mp3_path,), daemon=True).start()
        return
    except Exception:
        pass

    print("[warn] no background player available; MP3 left at", mp3_path, file=sys.stderr)


def _sapi_speak(text):
    """Offline TTS via Windows SAPI (robotic but always works)."""
    try:
        import win32com.client  # type: ignore
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Speak(text)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Inbox watcher
# ---------------------------------------------------------------------------

class _InboxHandler(FileSystemEventHandler):
    """watchdog handler that sets a dirty flag when inbox.md changes."""

    def __init__(self):
        self._dirty = threading.Event()
        self._dirty.set()  # dirty on first tick

    def on_modified(self, event):
        if not event.is_directory and Path(event.src_path).name == INBOX_PATH.name:
            self._dirty.set()

    def on_created(self, event):
        self.on_modified(event)

    @property
    def dirty(self):
        return self._dirty


def _process_inbox(stop, flags_provider):
    """Drain the inbox whenever it changes, speaking new turns in order."""
    handler = _InboxHandler()
    observer = Observer()
    observer.schedule(handler, str(INBOX_PATH.parent), recursive=False)
    observer.start()
    try:
        positions = _read_json(POSITIONS_PATH, {"cursor": [0, "p"], "threads": {}})
        while not stop.is_set():
            handler.dirty.wait(timeout=1.0)
            if not handler.dirty.is_set():
                continue
            handler.dirty.clear()
            flags = flags_provider()
            if not (flags.get("master") and flags.get("codex")):
                continue
            if not INBOX_PATH.exists():
                continue
            text = INBOX_PATH.read_text(encoding="utf-8", errors="ignore")
            turns = parse_inbox(text)
            if not turns:
                continue
            cur_idx, cur_kind = positions.get("cursor", [0, "p"])
            advanced = False
            for t in turns:
                tk = (t["idx"], t["kind"])
                ck = (cur_idx, cur_kind)
                if tk < ck:
                    continue
                if tk == ck and not advanced:
                    continue
                prefix = "Prompt" if t["kind"] == "p" else "Response"
                _speak(prefix + " " + str(t["idx"]) + ". " + t["body"], flags, thread=t["thread"])
                cur_idx, cur_kind = t["idx"], t["kind"]
                advanced = True
                positions["cursor"] = [cur_idx, cur_kind]
                _write_json(POSITIONS_PATH, positions)
    finally:
        observer.stop()
        observer.join()


# ---------------------------------------------------------------------------
# Clipboard listener
# ---------------------------------------------------------------------------

def _process_clipboard(stop, flags_provider):
    """Poll the clipboard and speak any new text the user copies."""
    last_text = ""
    current_day = _today_str()
    try:
        last_text = pyperclip.paste() or ""
    except Exception:
        last_text = ""
    while not stop.is_set():
        time.sleep(CLIPBOARD_POLL_S)
        flags = flags_provider()
        if not (flags.get("master") and flags.get("clipboard")):
            try:
                last_text = pyperclip.paste() or ""
            except Exception:
                last_text = ""
            continue
        day = _today_str()
        if day != current_day:
            current_day = day
        try:
            text = pyperclip.paste() or ""
        except Exception:
            text = ""
        if not text or text == last_text:
            continue
        last_text = text
        CLIPBOARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CLIPBOARD_LOG.open("a", encoding="utf-8") as f:
            f.write("\n--- " + time.strftime("%H:%M:%S") + " ---\n" + text + "\n")
        _speak(text, flags)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def _flags_provider():
    """Re-read flags.json from disk every call. Cheap; one tiny file."""
    flags = _read_json(FLAGS_PATH, _default_flags())
    for k, v in _default_flags().items():
        flags.setdefault(k, v)
    return flags


def start():
    """Boot the inbox watcher + clipboard listener as background threads."""
    if not FLAGS_PATH.exists():
        _write_json(FLAGS_PATH, _default_flags())
    stop = threading.Event()
    t_inbox = threading.Thread(
        target=_process_inbox, args=(stop, _flags_provider), daemon=True, name="inbox"
    )
    t_clip = threading.Thread(
        target=_process_clipboard, args=(stop, _flags_provider), daemon=True, name="clipboard"
    )
    t_inbox.start()
    t_clip.start()
    (ROOT / "state" / "watcher.pid").write_text(str(os.getpid()), encoding="utf-8")
    print(
        "watcher started (pid",
        os.getpid(),
        "). inbox=",
        INBOX_PATH,
        "clipboard=",
        _flags_provider()["clipboard"],
    )
    try:
        while not stop.is_set():
            stop.wait(timeout=1.0)
    except KeyboardInterrupt:
        stop.set()
    t_inbox.join(timeout=2)
    t_clip.join(timeout=2)
    return 0


def status():
    """Print the current flags + position + a one-line health summary."""
    flags = _flags_provider()
    pos = _read_json(POSITIONS_PATH, {"cursor": [0, "p"]})
    pid_file = ROOT / "state" / "watcher.pid"
    running = pid_file.exists()
    print("watcher running :", running, "(pid file:", pid_file if running else "n/a", ")")
    print("master          :", flags.get("master"))
    print("codex speaking  :", flags.get("codex"))
    print("clipboard speak :", flags.get("clipboard"))
    print("archive mp3     :", flags.get("archive_mp3"))
    print("engine/voice    :", flags.get("engine"), "/", flags.get("voice"))
    print("cursor          :", pos.get("cursor"))
    return 0


def stop():
    """Stop the running watcher by killing its PID."""
    pid_file = ROOT / "state" / "watcher.pid"
    if not pid_file.exists():
        print("watcher not running")
        return 0
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except ValueError:
        pid_file.unlink(missing_ok=True)
        return 0
    if os.name == "nt":
        os.system("taskkill /PID " + str(pid) + " /F >NUL 2>&1")
    else:
        os.kill(pid, 15)
    pid_file.unlink(missing_ok=True)
    print("watcher stopped (pid", pid, ")")
    return 0


def main():
    parser = argparse.ArgumentParser(prog="watcher.py")
    parser.add_argument("command", choices=["start", "stop", "status"])
    args = parser.parse_args()
    return {"start": start, "stop": stop, "status": status}[args.command]()


if __name__ == "__main__":
    sys.exit(main())


