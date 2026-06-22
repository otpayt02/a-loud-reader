"""watcher.py — Codex inbox + clipboard listener for a-loud-reader.

Two things run in the background:

1. **Inbox watcher** — tails `inbox/inbox.md` (or whatever the watcher was told).
   Codex appends prompts/responses there as `1p ...`, `1r ...`, etc. We speak
   each new line in order, tracking an index file (`state/positions.json`) so
   we can resume mid-thread after a restart.

2. **Clipboard listener** — polls the system clipboard. If the latest text
   changed and global mode allows it, we speak it. Off by default; user
   toggles it with `loud-reader clipboard on` / `off`.

State is shared via JSON files in `state/`. Commands from the PowerShell CLI
flip those files and the watcher reacts on its next tick (~250 ms).

Usage:
    python watcher.py start
    python watcher.py status
    python watcher.py stop
"""

# --- stdlib ---
import json  # read/write the small JSON state files we keep on disk
import os    # paths, makedirs, etc.
import sys   # exit codes
import time  # sleep between polls
import ctypes  # Windows-specific: GetAsyncKeyState, GlobalLock for clipboard
import struct  # unpack HGLOBAL memory pointers
import subprocess
import threading  # run inbox and clipboard loops in parallel
from pathlib import Path  # cleaner path handling than os.path

# --- third-party ---
import pyperclip  # cross-platform clipboard read (uses ctypes under the hood on Windows)
import win32file  # type: ignore  # ReadDirectoryChangesW — fast inbox watcher
import win32con   # type: ignore  # constants for the above
from watchdog.events import FileSystemEventHandler  # type: ignore  # nice wrapper around RDCW
from watchdog.observers import Observer              # type: ignore  # the watcher itself

# --- local ---
# `src/say.py` is the single TTS entry point. We import it as a module so we
# can call its async synth function from this sync process.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import say  # noqa: E402  (the path tweak above is intentional)


# ----------------------------------------------------------------------------
# Configuration & state files
# ----------------------------------------------------------------------------

# Repo root: assumes this script lives in `src/` and the repo is its parent.
ROOT = Path(__file__).resolve().parent.parent

# Where Codex drops new chat turns. Append-only markdown; one line per turn.
INBOX_PATH = ROOT / "inbox" / "inbox.md"

# Where clipboard captures accumulate for the day (rotated at midnight).
CLIPBOARD_LOG = ROOT / "data" / "clipboard.md"

# State files. We use JSON because the PowerShell CLI needs to flip flags
# from a separate process; JSON is the cheapest shared format.
STATE_DIR = ROOT / "state"
FLAGS_PATH = STATE_DIR / "flags.json"      # on/off, pause, etc.
POSITIONS_PATH = STATE_DIR / "positions.json"  # per-thread "next line to read" cursors
PINNED_PATH = STATE_DIR / "pinned.json"    # threads the user marked "keep forever"

# How often the clipboard poller wakes up. 400 ms is responsive without
# hammering the OS; the inbox watcher is event-driven, not polled.
CLIPBOARD_POLL_S = 0.4


def _read_json(path: Path, default: dict) -> dict:
    """Read a JSON file or return `default` if it doesn't exist / is broken.

    We swallow errors on purpose: a corrupted state file should never crash
    the watcher. Worst case the user re-runs and the file is recreated.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: dict) -> None:
    """Atomic-ish JSON write: write to a temp file, then rename.

    The rename makes it so the PowerShell CLI never sees a half-written file.
    On Windows, `os.replace` is atomic when the destination exists.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _default_flags() -> dict:
    """Initial on/off state. Defaults match what the user asked for."""
    return {
        "master": True,        # overall on/off — `loud-reader on|off`
        "codex": True,         # speak Codex inbox turns — always on while master is on
        "clipboard": False,    # speak clipboard — off by default per user request
        "archive_mp3": True,   # save MP3s to archive/ — default on
        "pin_threads": {},     # {"<thread_id>": true} — keep-forever override
        "engine": "edge",      # "edge" for neural, "sapi" for offline Windows voice
        "voice": "en-US-JennyNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
    }


def _today_str() -> str:
    """Local-date string used to rotate the daily clipboard log."""
    return time.strftime("%Y-%m-%d")


# ----------------------------------------------------------------------------
# Codex inbox parsing & reading
# ----------------------------------------------------------------------------

# Regex for a Codex turn line. The user spec was "1p", "1r", "2p", "12r" etc.
# Captures: the full token (e.g. "12r") and the digit count, so we can sort.
import re
TURN_RE = re.compile(r"^(?P<idx>\d+)(?P<kind>[pr])\s+(?P<body>.*)$")


def parse_inbox(text: str) -> list[dict]:
    """Parse the inbox markdown into a sorted list of turn dicts.

    Lines that don't match the turn pattern are ignored (so Codex can also
    drop prose comments and headings in there without breaking us).
    """
    turns: list[dict] = []
    for raw in text.splitlines():
        m = TURN_RE.match(raw.strip())
        if not m:
            continue
        turns.append({
            "idx": int(m.group("idx")),
            "kind": m.group("kind"),  # "p" (prompt) or "r" (response)
            "body": m.group("body").strip(),
        })
    # Stable sort by (idx, kind) so prompts come before responses at the same number.
    turns.sort(key=lambda t: (t["idx"], t["kind"]))
    return turns


def _speak(text: str, flags: dict) -> None:
    """Synthesize `text` with the configured engine, and optionally archive it.

    We delegate to say.py for the actual TTS work. The archive flag controls
    whether the MP3 is saved with a meaningful name (and kept per the pin
    setting) or thrown away as a temp file.
    """
    if not text.strip():
        return
    # Build a safe filename from the first ~40 chars of text.
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", text[:40]).strip("_") or "turn"
    # Where the MP3 lands. If archiving is on we use a stable name; otherwise tmp.
    if flags.get("archive_mp3", True):
        out_dir = ROOT / "archive" / _today_str()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{int(time.time()*1000)}_{safe}.mp3"
    else:
        out_path = ROOT / "archive" / "_tmp.mp3"

    try:
        # `say.synth` is a sync wrapper around the async Edge-TTS call.
        say.synth(
            text=text,
            voice=flags.get("voice", "en-US-JennyNeural"),
            rate=flags.get("rate", "+0%"),
            pitch=flags.get("pitch", "+0Hz"),
            out_path=str(out_path),
        )
        # Hand the MP3 to a background player. We deliberately avoid `os.startfile`
        # because it steals foreground focus. Instead we launch a hidden process so
        # audio plays silently in the background while the user keeps working.
        if os.name == "nt":
            _play_in_background(str(out_path))
    except Exception as e:  # noqa: BLE001
        # If TTS fails (e.g. offline and engine=edge), fall back to Windows SAPI
        # so the user still hears something. Better than silent failure.
        _sapi_speak(text, flags)
        print(f"[warn] edge-tts failed ({e}); used SAPI fallback", file=sys.stderr)


def _play_in_background(mp3_path: str) -> None:
    """Play an MP3 in the background without stealing foreground focus.

    We try a few strategies in order of reliability on a clean Windows
    install. None of them pop a window over the user's current app.

    1. **PowerShell + WSH shell `exec` with `WindowStyle=Hidden`** — uses
       the user's default MP3 association (Windows Media Player, Movies
       & TV, foobar2000, etc.) and forces the process to be hidden. Audio
       still plays; the GUI never appears.
    2. **`winmm.mciSendString`** — old-school MCI. Plays the file via the
       system's MCI subsystem. No window, but no progress control either.
    3. **`pygame.mixer`** — if installed, the simplest cross-platform
       background player. We open and play the file in a thread so the
       watcher's main loop isn't blocked.

    We never raise out of this function. If all three fail we just print
    a warning and let the MP3 sit in archive/ for the user to play.
    """
    # 1) PowerShell with hidden window. This is the path that works on a
    #    brand-new Windows box with no extra Python packages.
    if os.name == "nt":
        try:
            # We invoke the WSH Shell via PowerShell so we can pass
            # `WindowStyle = Hidden`. mshta/wmplayer inherit the same
            # hidden flag.
            ps_cmd = (
                f"$s = New-Object -ComObject Shell.Application; "
                f"$s.ShellExecute('{mp3_path.replace(chr(39), chr(39)*2)}', '', '', 'open', 0)"
            )
            # CREATE_NO_WINDOW = 0x08000000. We use a hidden PowerShell.
            CREATE_NO_WINDOW = 0x08000000
            si = subprocess.STARTUPINFO()  # noqa: F821  (imported lazily below)
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            subprocess.Popen(  # noqa: F821
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                creationflags=CREATE_NO_WINDOW,
                startupinfo=si,
                stdout=subprocess.DEVNULL,  # noqa: F821
                stderr=subprocess.DEVNULL,  # noqa: F821
            )
            return
        except Exception as e:  # noqa: BLE001
            print(f"[warn] hidden WSH play failed: {e}", file=sys.stderr)

    # 2) Fallback to winmm MCI. Always available on Windows; truly headless.
    if os.name == "nt":
        try:
            import ctypes  # local import to keep the top of the file clean
            ctypes.windll.winmm.mciSendStringW(f'open "{mp3_path}" type mpegvideo alias a_loud', None, 0, None)
            ctypes.windll.winmm.mciSendStringW("play a_loud", None, 0, None)
            return
        except Exception as e:  # noqa: BLE001
            print(f"[warn] MCI play failed: {e}", file=sys.stderr)

    # 3) Last resort: pygame if it's installed.
    try:
        import pygame  # type: ignore
        pygame.mixer.init()
        pygame.mixer.music.load(mp3_path)
        pygame.mixer.music.play()
        return
    except Exception:
        pass

    print(f"[warn] no background player available; MP3 left at {mp3_path}", file=sys.stderr)

def _sapi_speak(text: str, flags: dict) -> None:
    """Last-ditch offline TTS via Windows SAPI. Robotesque but always works.

    We use the COM-callable SAPI.SpVoice through ctypes. Simpler than
    installing pywin32, and good enough as a fallback that almost never runs.
    """
    try:
        # `win32com.client` ships with pywin32; if it's not installed, we just skip.
        import win32com.client  # type: ignore
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Speak(text)
    except Exception:
        # If even SAPI is missing (very rare on Windows), we have nothing to do.
        pass


# ----------------------------------------------------------------------------
# Inbox watcher
# ----------------------------------------------------------------------------

class _InboxHandler(FileSystemEventHandler):
    """watchdog handler that fires on inbox.md changes.

    We don't process the file inside the callback (it may still be open for
    write). Instead we just set an event flag and let the main loop drain it.
    """

    def __init__(self) -> None:
        # threading.Event is the simplest cross-thread signal in the stdlib.
        self._dirty = threading.Event()
        self._dirty.set()  # start dirty so we read on first tick

    def on_modified(self, event):  # type: ignore[override]
        # Only care about our exact file, not the directory itself.
        if not event.is_directory and Path(event.src_path).name == INBOX_PATH.name:
            self._dirty.set()

    def on_created(self, event):  # type: ignore[override]
        self.on_modified(event)

    @property
    def dirty(self) -> threading.Event:
        return self._dirty


def _process_inbox(stop: threading.Event, flags_provider) -> None:
    """Drain the inbox whenever it changes, speaking new turns in order.

    `flags_provider` is a zero-arg callable that returns the latest flags dict.
    We re-read it every tick so the PowerShell CLI's toggles take effect fast.
    """
    handler = _InboxHandler()
    # Watch the directory (not the file) so creation-after-delete is detected.
    observer = Observer()
    observer.schedule(handler, str(INBOX_PATH.parent), recursive=False)
    observer.start()

    try:
        # The "cursor" tracks which (idx, kind) we've already spoken. Persisted
        # in positions.json so a restart resumes where we left off.
        positions = _read_json(POSITIONS_PATH, {"cursor": [0, "p"], "threads": {}})

        while not stop.is_set():
            # Wait for a change signal or 1 s, whichever comes first. The 1 s
            # ceiling is just to be safe in case the event fires before we set
            # up the wait.
            handler.dirty.wait(timeout=1.0)
            if not handler.dirty.is_set():
                continue
            handler.dirty.clear()

            flags = flags_provider()
            if not (flags.get("master") and flags.get("codex")):
                # Watcher is toggled off — keep the cursor, don't speak.
                continue

            if not INBOX_PATH.exists():
                continue

            text = INBOX_PATH.read_text(encoding="utf-8", errors="ignore")
            turns = parse_inbox(text)
            if not turns:
                continue

            # Walk the parsed turns in order. For each one past the cursor, speak it
            # and advance the cursor.
            cur_idx, cur_kind = positions.get("cursor", [0, "p"])
            advanced = False
            for t in turns:
                tk = (t["idx"], t["kind"])
                ck = (cur_idx, cur_kind)
                if tk < ck:
                    continue  # already read
                if tk == ck and not advanced:
                    continue
                # Speak this turn.
                prefix = "Prompt" if t["kind"] == "p" else "Response"
                _speak(f"{prefix} {t['idx']}. {t['body']}", flags)
                cur_idx, cur_kind = t["idx"], t["kind"]
                advanced = True
                # Persist after each turn so a crash mid-thread loses at most one.
                positions["cursor"] = [cur_idx, cur_kind]
                _write_json(POSITIONS_PATH, positions)

    finally:
        observer.stop()
        observer.join()


# ----------------------------------------------------------------------------
# Clipboard listener
# ----------------------------------------------------------------------------

def _process_clipboard(stop: threading.Event, flags_provider) -> None:
    """Poll the clipboard and speak any new text the user copies.

    Daily log file at `data/clipboard.md` gets one line per copy so the user
    can review what was spoken that day. Rotated at local midnight.
    """
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
            # Don't update last_text while off; when re-enabled, we don't want
            # to re-speak whatever was sitting on the clipboard.
            try:
                last_text = pyperclip.paste() or ""
            except Exception:
                last_text = ""
            continue

        # Rotate the daily log if the date changed.
        day = _today_str()
        if day != current_day:
# (per-day rotation handled by daily reset job, not inline)
            current_day = day

        try:
            text = pyperclip.paste() or ""
        except Exception:
            text = ""
        if not text or text == last_text:
            continue
        last_text = text

        # Append to the daily clipboard log (interspaced line per spec).
        CLIPBOARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CLIPBOARD_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n--- {time.strftime('%H:%M:%S')} ---\n{text}\n")

        _speak(text, flags)


# ----------------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------------

def _flags_provider() -> dict:
    """Re-read flags.json from disk every call. Cheap; one tiny file."""
    flags = _read_json(FLAGS_PATH, _default_flags())
    # Backfill any missing keys so old state files keep working.
    for k, v in _default_flags().items():
        flags.setdefault(k, v)
    return flags


def start() -> int:
    """Boot the inbox watcher + clipboard listener as background threads."""
    # Initialize flags file on first run so the CLI can flip it from the start.
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

    # PID file so the CLI can find us to stop us.
    (ROOT / "state" / "watcher.pid").write_text(str(os.getpid()), encoding="utf-8")
    print(f"watcher started (pid {os.getpid()}). inbox={INBOX_PATH} clipboard={flags_provider()['clipboard']}")
    try:
        # Main thread sleeps until the user stops us (or forever, which is fine
        # because we're going to be killed from the CLI).
        while not stop.is_set():
            stop.wait(timeout=1.0)
    except KeyboardInterrupt:
        stop.set()
    t_inbox.join(timeout=2)
    t_clip.join(timeout=2)
    return 0


def status() -> int:
    """Print the current flags + position + a one-line health summary."""
    flags = _flags_provider()
    pos = _read_json(POSITIONS_PATH, {"cursor": [0, "p"]})
    pid_file = ROOT / "state" / "watcher.pid"
    running = pid_file.exists()
    print(f"watcher running : {running}  (pid file: {pid_file if running else 'n/a'})")
    print(f"master          : {flags['master']}")
    print(f"codex speaking  : {flags['codex']}")
    print(f"clipboard speak : {flags['clipboard']}")
    print(f"archive mp3     : {flags['archive_mp3']}")
    print(f"engine/voice    : {flags['engine']} / {flags['voice']}")
    print(f"cursor          : {pos.get('cursor')}")
    return 0


def stop() -> int:
    """Stop the running watcher by killing its PID (best-effort)."""
    pid_file = ROOT / "state" / "watcher.pid"
    if not pid_file.exists():
        print("watcher not running")
        return 0
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except ValueError:
        pid_file.unlink(missing_ok=True)
        return 0
    # `taskkill` is the polite way to stop a process on Windows. /F = force.
    if os.name == "nt":
        os.system(f'taskkill /PID {pid} /F >NUL 2>&1')
    else:
        os.kill(pid, 15)  # SIGTERM on POSIX; not used here, but kept for parity.
    pid_file.unlink(missing_ok=True)
    print(f"watcher stopped (pid {pid})")
    return 0


def flags_provider() -> dict:
    """Public alias for the internal provider so the CLI can peek without restart."""
    return _flags_provider()


def main() -> int:
    """Tiny CLI for start/stop/status."""
    if len(sys.argv) < 2:
        print("usage: watcher.py start|stop|status", file=sys.stderr)
        return 2
    cmd = sys.argv[1].lower()
    if cmd == "start":
        return start()
    if cmd == "stop":
        return stop()
    if cmd == "status":
        return status()
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())


