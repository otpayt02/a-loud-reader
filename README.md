# a-loud-reader

Local, open-source read-aloud for Codex chats. Append a `1p` / `1r` line to
`inbox/inbox.md` and a background watcher speaks it out loud via Microsoft
Edge neural TTS (free, no key, no quota). Toggle it off with one CLI command.

> GitHub: [otpayt02/a-loud-reader](https://github.com/otpayt02/a-loud-reader)

## Why

Reading chat with your eyes is slow. This turns Codex into a podcast. Tweak
the voice, the rate, and which turns get archived. Clipboard listening is
opt-in (off by default).

## Install (Windows / PowerShell)

```powershell
cd C:\Users\olive\Projects\a-loud-reader
python -m pip install -r requirements.txt
```

Then either run the script directly:

```powershell
.\src\loud-reader.ps1 status
```

Or install the shim on PATH:

```powershell
.\bin\install_path.cmd          # copies loud-reader.cmd to %USERPROFILE%\bin
$env:PATH = "$env:USERPROFILE\bin;$env:PATH"
loud-reader status
```

## Quick start

```powershell
# 1. turn the watcher on
loud-reader on
loud-reader start               # boot the background Python process

# 2. append a turn. Index 1, kind 'p' (prompt) or 'r' (response).
Add-Content inbox\inbox.md "1p Hello from Codex, this is turn one."

# 3. hear it. The watcher reads any new line, then advances its cursor.
# Re-running the same line won't re-speak it (the cursor moved past it).

# 4. when you're done
loud-reader off
loud-reader stop
```

To speak a specific turn by index, even if the watcher is off:

```powershell
loud-reader read 1p             # speak turn "1p" right now
loud-reader read 12r            # speak turn "12r" right now
```

To start over from the beginning:

```powershell
loud-reader reset-cursor
```

## CLI cheat sheet

| Command | What it does |
|---|---|
| `loud-reader on` | Master switch on (Codex speaking enabled, clipboard off) |
| `loud-reader off` | Silent (watcher keeps running, just doesn't speak) |
| `loud-reader status` | Print flags, cursor, voice, archive state |
| `loud-reader codex on\|off` | Toggle Codex-inbox speaking |
| `loud-reader clipboard on\|off` | Toggle clipboard listening (off by default) |
| `loud-reader archive on\|off` | Toggle MP3 archival (default on; daily reset) |
| `loud-reader voice en-US-GuyNeural` | Change the Edge voice |
| `loud-reader rate +10%` | Faster / slower (`-5%`, `+25%`, etc.) |
| `loud-reader read 1p` | Speak one specific turn now |
| `loud-reader tail` | Live-tail the inbox file |
| `loud-reader reset-cursor` | Forget progress, re-read from oldest |
| `loud-reader pin <id>` / `unpin <id>` | Mark a thread keep-forever |
| `loud-reader inbox` | Print the inbox path (for Codex to append to) |
| `loud-reader start` / `stop` | Boot / kill the Python watcher |

## Codex integration

Tell Codex to append every turn to the inbox. Paste this into your
`CODEX_INSTRUCTIONS.md` (or your project's notes) and Codex will do it
automatically:

```
# a-loud-reader hook
After writing your final assistant response in any conversation, append a
single line to C:\Users\olive\Projects\a-loud-reader\inbox\inbox.md in the
format `<N>p <body>` for prompts and `<N>r <body>` for responses, where <N>
is the turn number in this conversation. Use the absolute path returned by
`loud-reader inbox` if the repo lives elsewhere.
```

`CODEX_INSTRUCTIONS.md` is shipped in this repo and contains that exact text.

## File layout

```
a-loud-reader/
+- inbox/
|  +- inbox.md             # Codex appends <N>p / <N>r lines here
+- data/
|  +- clipboard.md         # daily log of clipboard captures (rotates at midnight)
+- archive/
|  +- YYYY-MM-DD/*.mp3     # spoken turns (one MP3 per turn)
+- state/
|  +- flags.json           # on/off, voice, archive_mp3, etc.
|  +- positions.json       # per-thread cursor (next turn to speak)
|  +- pinned.json          # threads marked keep-forever
|  +- watcher.pid          # pid of the running Python watcher
|  +- watcher.log          # stdout/stderr from the watcher
+- src/
|  +- say.py               # Edge TTS wrapper (single-shot)
|  +- watcher.py           # inbox + clipboard loop, writes/reads state JSON
|  +- loud-reader.ps1      # the operator CLI
+- bin/
|  +- loud-reader.cmd      # PATH shim
|  +- install_path.cmd     # copy the shim into %USERPROFILE%\bin
+- scripts/
|  +- smoke_test.ps1       # one-shot end-to-end check
+- .gitignore
+- README.md
+- CODEX_INSTRUCTIONS.md
+- requirements.txt
```

## State files (safe to delete)

- `state/flags.json` â€” rebuilt with defaults if missing.
- `state/positions.json` â€” cursor only; deleting it = re-read everything.
- `state/pinned.json` â€” list of threads the user marked keep-forever.
- `state/watcher.pid` â€” only present while the watcher is alive.

## Archive policy

MP3s land in `archive/YYYY-MM-DD/`. Older days are kept unless you delete
them manually. Pinning a thread moves its logs to a `archive/pinned/<id>/`
folder (TODO; works as a flag now, folder wiring is the next pass).

The clipboard log `data/clipboard.md` is rotated at local midnight. Pinning
prevents rotation for that thread.

## Troubleshooting

- "watcher not running" but flags say `master=true` â€” run `loud-reader start`.
- No sound but MP3 exists in `archive/` â€” open the MP3 manually; your media
  player may be muted.
- TTS errors with no internet â€” Edge TTS is online-only. The watcher
  auto-falls back to Windows SAPI (robotic but always works).

## Smoke test

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1
```

Should print `OK: smoke test produced an MP3 at ...\archive\smoke.mp3`.


## Engines

- `loud-reader engine edge` (default) -- Microsoft Edge neural voices, online, free, no key.
- `loud-reader engine piper` -- Piper offline neural TTS, works without internet. Piper binary path is
  set via `A_LOUD_READER_PIPER` (default points at the existing yt_auto install). Voice model via
  `A_LOUD_READER_MODEL`. Both are picked up automatically.

If the active engine fails (e.g. offline + edge), the watcher falls back to Windows SAPI
(robotic, always works) and prints a warning to `state/watcher.log`.

## Pinned threads

Lines in `inbox.md` may include a thread prefix: `alpha:1p Hello` routes to thread `alpha`.
Pin a thread so its MP3s land in `archive/pinned/<thread>/` (survives daily rotation):

```
loud-reader pin alpha
loud-reader unpin alpha
```

`alpha:` and `work-thread:` style prefixes are both supported.
