"""say.py â€” single-shot TTS for a-loud-reader.

Wraps the Edge TTS neural voices (no API key, online) behind a tiny CLI.
The watcher (`loud-reader.ps1`) shells out to this so we get one engine to
maintain, and it works on a fresh Windows install with just `pip install edge-tts`.

Usage:
    python say.py "Hello world"
    python say.py "Hello" --voice en-US-AriaNeural --rate +10% --pitch -5Hz
    python say.py "Hello" --out archive/hello.mp3
    python say.py --list-voices
    python say.py --list-voices en
"""

# Standard library imports we always need.
import argparse  # Parse the CLI flags below (--voice, --rate, ...).
import asyncio   # Edge-TTS is async; we run it in a tiny event loop.
import os        # Filesystem path joining and directory creation.
import sys       # Exit codes and writing to stderr.

# Third-party import: edge-tts is the open-source Python wrapper around
# Microsoft Edge's free "Read Aloud" neural voices. No key, no quota, no signup.
import edge_tts  # type: ignore


# Default voice. Edge's "Jenny" is a clean US English female voice that sounds
# good for technical content. Users can override with --voice.
DEFAULT_VOICE = "en-US-JennyNeural"

# Default rate (% relative to the voice's natural pace). 0% = normal,
# +10% = a touch faster, -10% = slower / more deliberate.
DEFAULT_RATE = "+0%"

# Default pitch shift. Voices already sound natural, so we leave it neutral.
DEFAULT_PITCH = "+0Hz"


async def _synthesize_to_mp3(text: str, voice: str, rate: str, pitch: str, out_path: str) -> None:
    """Synthesize `text` and write the resulting MP3 to `out_path`.

    edge_tts.Communicate is an async context manager that streams audio bytes
    in chunks; we collect them and dump to disk. This is the only async path
    in the file; everything else is sync on purpose.
    """
    # Build the communicator with the requested voice/rate/pitch.
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)

    # Make sure the destination directory exists (e.g. archive/ may be missing
    # the very first time you run this).
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Stream the audio into a file. We open in write-binary because MP3 is bytes.
    with open(out_path, "wb") as f:
        async for chunk in communicate.stream():
            # Edge-TTS emits two kinds of chunks: "audio" (the MP3 bytes) and
            # "error" (rare; e.g. rate string malformed). We only want audio.
            if chunk["type"] == "audio":
                f.write(chunk["data"])


async def _list_voices(locale_prefix: str | None) -> list[dict]:
    """Return the list of available Edge voices, optionally filtered by locale.

    If `locale_prefix` is "en" we return only English voices, which is what
    the user almost always wants. If it's None we return everything (200+).
    """
    voices = await edge_tts.list_voices()
    if locale_prefix:
        # Locale looks like "en-US". The user passes just "en" usually, so we
        # match by the leading two characters of the locale.
        prefix = locale_prefix.lower()
        voices = [v for v in voices if v["Locale"].lower().startswith(prefix)]
    return voices


def main() -> int:
    """CLI entry point. Returns 0 on success, non-zero on failure."""
    # argparse gives us --help for free, which matters because the user will
    # discover features by typing `python say.py --help`.
    parser = argparse.ArgumentParser(
        prog="say.py",
        description="Speak text aloud via Edge TTS neural voices.",
    )
    # The actual text to speak. Optional because --list-voices takes no text.
    parser.add_argument("text", nargs="?", help="Text to speak. Omit when using --list-voices.")
    # Voice selection. Default is the friendly US English voice above.
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"Edge voice name (default: {DEFAULT_VOICE})")
    # Rate is a percentage string like +10% / -5%. Edge-TTS parses it.
    parser.add_argument("--rate", default=DEFAULT_RATE, help="Speech rate, e.g. +10%% (default: +0%%)")
    # Pitch is Hz offset like +2Hz / -5Hz. Edge-TTS parses it.
    parser.add_argument("--pitch", default=DEFAULT_PITCH, help="Pitch shift, e.g. +2Hz (default: +0Hz)")
    # Output MP3 path. Default is a temp file the caller can play or move.
    parser.add_argument("--out", default=os.path.join("archive", "_tmp_say.mp3"), help="MP3 output path")
    # --play is a convenience: after saving the MP3, open it with the OS default player.
    parser.add_argument("--play", action="store_true", help="Open the MP3 with the system default player after saving")
    # --list-voices prints available voices and exits. Useful for picking one.
    parser.add_argument("--list-voices", nargs="?", const="", default=None, metavar="LOCALE",
                        help="List available voices, optionally filtered by locale (e.g. 'en').")
    args = parser.parse_args()

    # Branch 1: the user asked to list voices. We do that and exit cleanly.
    if args.list_voices is not None:
        # `args.list_voices` is "" when --list-voices was passed with no value.
        locale = args.list_voices or None
        voices = asyncio.run(_list_voices(locale))
        for v in voices:
            # Each voice dict has: Name (e.g. en-US-JennyNeural), Locale, Gender, ShortName.
            print(f"{v['ShortName']:40s} {v['Locale']:8s} {v['Gender']}")
        return 0

    # Branch 2: the user didn't pass any text. That's an error.
    if not args.text:
        print("error: no text provided. Pass a string or use --list-voices.", file=sys.stderr)
        return 2

    # Branch 3: synthesize the speech and write the MP3.
    try:
        asyncio.run(_synthesize_to_mp3(args.text, args.voice, args.rate, args.pitch, args.out))
    except Exception as e:  # noqa: BLE001 â€” edge-tts raises a few different types; collapse them.
        print(f"error: TTS failed: {e}", file=sys.stderr)
        return 1
    # Hand the MP3 to a background player. We deliberately avoid `os.startfile`
    # because it steals foreground focus. Instead we use the WSH Shell via a
    # hidden PowerShell subprocess so audio plays silently in the background.
    if os.name == "nt":
        try:
            import subprocess
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
                 "-Command", f"Start-Process -FilePath \u0027{args.out}\u0027 -WindowStyle Hidden"],
                creationflags=0x08000000,
                startupinfo=si,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"[warn] hidden play failed: {e}", file=sys.stderr)
    # and opens the file with whatever app is associated with .mp3.
    if args.play and os.name == "nt":
        try:
            import subprocess
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
                 "-Command", f"Start-Process -FilePath \u0027{args.out}\u0027 -WindowStyle Hidden"],
                creationflags=0x08000000,
                startupinfo=si,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            print(f"[warn] hidden play failed: {e}", file=sys.stderr)

    # Print the path so the caller (e.g. the PowerShell watcher) can verify it landed.
    print(args.out)
    return 0




def synth(text: str, voice: str, rate: str, pitch: str, out_path: str) -> None:
    """Sync wrapper around the async Edge-TTS synth. Used by watcher.py.

    Edge-TTS is async-only, but the watcher runs in a plain thread, so we
    spin a tiny event loop per call. This is fine for our throughput
    (one turn at a time, not a stream).
    """
    asyncio.run(_synthesize_to_mp3(text, voice, rate, pitch, out_path))

# Standard Python idiom: only run main() when this file is executed directly,
# not when it's imported. Lets us unit-test the helpers above later if needed.

    """Sync wrapper around the async Edge-TTS synth. Used by watcher.py.

    Edge-TTS is async-only, but the watcher runs in a plain thread, so we
    spin a tiny event loop per call. Fine for one turn at a time.
    """
    asyncio.run(_synthesize_to_mp3(text, voice, rate, pitch, out_path))

if __name__ == "__main__":
    sys.exit(main())

