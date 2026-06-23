# a-loud-reader — step-by-step operator guide

This walks you through getting a-loud-reader running from a clean shell.
Tested on Windows 10/11 with PowerShell 5.1+ and Python 3.12.

## 0. Where things live
- Repo:        `C:\Users\olive\Projects\a-loud-reader`
- Inbox:       `<repo>\inbox\inbox.md`
- Archive:     `<repo>\archive\YYYY-MM-DD\` (and `<repo>\archive\pinned\<thread>\` for pinned)
- State files: `<repo>\state\flags.json` and `<repo>\state\positions.json`
- Watcher log: `<repo>\state\watcher.log`

## 1. Install (one-time)
```powershell
cd C:\Users\olive\Projects\a-loud-reader
python -m pip install -r requirements.txt
```

If `pip` times out downloading `piper-tts`, that's fine — the project ships
without it. Piper is the offline fallback and is optional.

## 2. Put the CLI on PATH (one-time)
```powershell
.\bin\install_path.cmd
$env:PATH = "$env:USERPROFILE\bin;$env:PATH"
```

`install_path.cmd` copies `loud-reader.cmd` to `%USERPROFILE%\bin`. After this,
`loud-reader` is reachable from any new PowerShell window.

## 3. Pick a TTS engine
```powershell
loud-reader engine edge     # online, neural, free. Default.
loud-reader engine piper    # offline, slower first run, no internet needed.
```

`piper` reuses the binary + voice model that already live in `yt_auto`. Set
`A_LOUD_READER_PIPER` and `A_LOUD_READER_MODEL` to override the paths.

## 4. Tune the voice
```powershell
loud-reader voice en-US-AriaNeural
loud-reader rate +5%
```

## 5. Start the watcher
```powershell
loud-reader on            # master switch on
loud-reader start         # boot the Python watcher as a background process
```

You'll see `watcher starting (pid ...)`. From this moment on, every line you
append to `inbox\inbox.md` in the format `<N>p <body>` or `<N>r <body>` is
spoken in the background. Audio plays via Windows MCI; **no media player
window pops up**.

## 6. Append turns
From PowerShell:
```powershell
"1p Hello, world." | Add-Content inbox\inbox.md
"1r Hi there!"        | Add-Content inbox\inbox.md
"2p Next question?"   | Add-Content inbox\inbox.md
```
From Codex: paste the snippet in `CODEX_INSTRUCTIONS.md` into your Codex notes.

Threaded example:
```powershell
"alpha:1p Pinned thread prompt" | Add-Content inbox\inbox.md
loud-reader pin alpha
```

After pinning, MP3s for `alpha:*` land in `archive\pinned\alpha\`.

## 7. Tray icon (optional but recommended)
```powershell
loud-reader tray
```
Right-click the speaker icon in the system tray to toggle on/off, pause, voice,
rate, engine, and to open the archive folder. The tray mirrors `flags.json`
every second; whatever you change there is what the watcher sees.

## 8. Toasts (optional)
```powershell
loud-reader toast on
```
Every spoken turn also pops a Windows toast (off by default).

## 9. Stop when done
```powershell
loud-reader off
loud-reader stop
```

## 10. Read me a specific turn out of order
```powershell
loud-reader read 12r       # speak turn 12r right now
loud-reader read alpha:3p  # pinned-thread turn
loud-reader reset-cursor   # forget progress, re-read everything
```

## Troubleshooting
Run this any time something feels wrong:

```powershell
.\scripts\diagnose.ps1
```

The diagnose script prints:
- repo path, Python version, pip list of required deps
- watcher running? (pid file vs actual process)
- current flags.json contents (with explanations)
- current positions.json cursor
- last 20 lines of `state\watcher.log`
- a 5-second live test: writes `1p diagnose test` to the inbox and waits
  for a new MP3 in `archive\YYYY-MM-DD\`

### Common issues

**"loud-reader not recognized" in a fresh shell**
Run `.\bin\install_path.cmd` once, then open a new PowerShell. PowerShell
reads PATH at startup; new shells spawned by tools may not see the change
until you relaunch them.

**Watcher pid file exists but `Get-Process python` shows nothing**
The pid file is stale. Run:
```powershell
loud-reader stop
Remove-Item state\watcher.pid -Force
loud-reader start
```

**Watcher fires but no sound plays**
- The MP3 is in `archive\YYYY-MM-DD\`; open it manually to confirm audio exists.
- If MP3 is 0 bytes, your internet dropped during Edge TTS synthesis. Toggle to Piper:
  `loud-reader engine piper`.
- If MP3 exists and the system has sound, the MCI playback is happening — just
  no audible level. Unmute / raise volume.

**JSON file corrupt / "Extra data" error on flags.json**
The CLI has BOM-protection now. If you still hit it:
```powershell
$txt = Get-Content state\flags.json -Raw -Encoding UTF8
if ($txt[0] -eq [char]0xFEFF) { $txt = $txt.Substring(1) }
[System.IO.File]::WriteAllText('state\flags.json', $txt, (New-Object System.Text.UTF8Encoding $false))
```

**Tray icon doesn't appear**
- Check `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` — the tray
  app doesn't auto-start yet; you have to run `loud-reader tray` once per session.
- Run `python src\tray.py` directly to see any traceback.

**"Failed to find piper model"**
Either set `A_LOUD_READER_MODEL` to a real `.onnx` file or switch back to Edge:
`loud-reader engine edge`.

**The watcher says it's running but isn't responding**
Kill and restart:
```powershell
loud-reader stop
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item state\watcher.pid -Force -ErrorAction SilentlyContinue
loud-reader start
```