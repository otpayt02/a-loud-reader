# loud-reader.ps1 ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â the operator CLI for a-loud-reader.
#
# This is the single entry point a user types in their terminal. It flips
# JSON state files that the Python watcher polls, and it manages the
# watcher process (start/stop). Everything is implemented in plain
# PowerShell so it works on a fresh Windows install with no extra runtimes.
#
# Verb map (all of these are valid):
#   loud-reader on                    -> master on, codex on, clipboard off
#   loud-reader off                   -> master off (watcher keeps running but is silent)
#   loud-reader status                -> print current flags + cursor
#   loud-reader codex on|off          -> toggle Codex-inbox speaking
#   loud-reader clipboard on|off      -> toggle clipboard speaking (off by default)
#   loud-reader archive on|off        -> toggle MP3 archival (default on)
#   loud-reader pin <thread_id>       -> mark a thread keep-forever (survives daily reset)
#   loud-reader unpin <thread_id>     -> remove keep-forever mark
#   loud-reader voice <name>          -> change the Edge voice (e.g. en-US-GuyNeural)
#   loud-reader rate <+-N%>           -> change speech rate (e.g. +10% / -5%)
#   loud-reader start                 -> boot the Python watcher as a background job
#   loud-reader stop                  -> kill the watcher
#   loud-reader tail                  -> live-print the inbox file as it grows
#   loud-reader read <token>          -> speak one turn by index, e.g. 1p / 12r
#   loud-reader reset-cursor          -> forget progress, start from oldest unread
#   loud-reader inbox                 -> print the path of inbox.md (for Codex to append to)
#
# Exit codes: 0 on success, 1 on bad usage, 2 on watcher failure.

#Requires -Version 5.1
# Strict mode catches typos in variable names ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â worth the noise during dev.
Set-StrictMode -Version Latest

# Resolve repo root from this script's location. Works whether the user
# invokes the .ps1 directly or via the loud-reader.cmd shim.
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$root       = (Resolve-Path "$scriptRoot\..").Path

# State files. Same paths the Python watcher uses, defined in watcher.py.
$stateDir   = Join-Path $root 'state'
$flagsPath  = Join-Path $stateDir 'flags.json'
$posPath    = Join-Path $stateDir 'positions.json'
$pinPath    = Join-Path $stateDir 'pinned.json'
$pidPath    = Join-Path $stateDir 'watcher.pid'
$logPath    = Join-Path $root 'state\watcher.log'
$inboxPath  = Join-Path $root 'inbox\inbox.md'

# Default flags ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â kept in sync with watcher._default_flags() in Python.
$defaultFlags = [pscustomobject]@{
    master       = $true
    codex        = $true
    clipboard    = $false
    archive_mp3  = $true
    toast_on_speak = $false
    pin_threads  = @{}
    engine       = 'edge'
    voice        = 'en-US-JennyNeural'
    rate         = '+0%'
    pitch        = '+0Hz'
}

# Read flags.json or seed it with defaults if missing/corrupt.
function Get-Flags {
    if (-not (Test-Path -LiteralPath $flagsPath)) {
        $defaultFlags | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $flagsPath -Encoding UTF8
    }
    try {
        $raw = Get-Content -LiteralPath $flagsPath -Raw | ConvertFrom-Json
        # Backfill any keys that newer versions of the code added.
        foreach ($prop in $defaultFlags.PSObject.Properties) {
            if (-not $raw.PSObject.Properties.Name -contains $prop.Name) {
                Add-Member -InputObject $raw -NotePropertyName $prop.Name -NotePropertyValue $prop.Value
            }
        }
        return $raw
    } catch {
        # Corrupt file: rebuild it rather than crash the CLI.
        $defaultFlags | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $flagsPath -Encoding UTF8
        return $defaultFlags
    }
}

# Persist the flags object. PowerShell's ConvertTo-Json emits clean JSON.
function Set-Flags([pscustomobject]$flags) {
    $flags | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $flagsPath -Encoding UTF8
}

# Pretty print the current state. This is the `status` command.
function Show-Status {
    $flags = Get-Flags
    $running = Test-Path -LiteralPath $pidPath
    $pos     = $null
    if (Test-Path -LiteralPath $posPath) {
        try { $pos = Get-Content -LiteralPath $posPath -Raw | ConvertFrom-Json } catch {}
    }
    Write-Host "watcher running : $running"
    Write-Host ("master          : {0}" -f $flags.master)
    Write-Host ("codex speaking  : {0}" -f $flags.codex)
    Write-Host ("clipboard speak : {0}" -f $flags.clipboard)
    Write-Host ("archive mp3     : {0}" -f $flags.archive_mp3)
    Write-Host ("engine/voice    : {0} / {1}" -f $flags.engine, $flags.voice)
    Write-Host ("rate            : {0}" -f $flags.rate)
    if ($pos) { Write-Host ("cursor          : {0}" -f ($pos.cursor -join ',')) }
    Write-Host "inbox file      : $inboxPath"
}

# Boot the Python watcher as a detached background process.
function Start-Watcher {
    if (Test-Path -LiteralPath $pidPath) {
        Write-Host "watcher already running (pid file present)"
        return
    }
    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
    # Use Start-Process with -WindowStyle Hidden so no console pops up.
    # The watcher writes its own log to state/watcher.log for debugging.
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName               = (Get-Command python).Source
    $psi.Arguments              = "-u src\watcher.py start"
    # Make `import say` work from src/watcher.py.
    $psi.EnvironmentVariables["PYTHONPATH"] = "$root\src"
    $psi.WorkingDirectory       = $root
    $psi.UseShellExecute        = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $psi.CreateNoWindow         = $true
    $proc = [System.Diagnostics.Process]::Start($psi)
    # Write the pid file immediately so a second `loud-reader start` won't double-launch.
    Set-Content -LiteralPath $pidPath -Value $proc.Id -Encoding ASCII
    Write-Host "watcher starting (pid $proc.Id). log: $logPath"
    # Also tee the watcher's stdout/stderr to a log file.
    Start-Job -Name loud-reader-log -ScriptBlock {
        param($p, $log)
        while (-not $p.HasExited) {
            $line = $p.StandardOutput.ReadLine()
            if ($line) { Add-Content -LiteralPath $log -Value $line }
        }
    } -ArgumentList $proc, $logPath | Out-Null
}

# Kill the watcher if it's running.
function Stop-Watcher {
    if (-not (Test-Path -LiteralPath $pidPath)) {
        Write-Host "watcher not running"
        return
    }
    $procId = (Get-Content -LiteralPath $pidPath -Raw).Trim()
    try {
        # taskkill /T kills the process tree (in case it spawned a child Python).
        & taskkill.exe /PID $procId /T /F 2>$null | Out-Null
        Write-Host "watcher stopped (pid $procId)"
    } catch {
        Write-Host "could not kill pid $procId : $_"
    }
    Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}

# Live-tail the inbox file. Useful for watching Codex append in real time.
function Show-InboxTail {
    if (-not (Test-Path -LiteralPath $inboxPath)) {
        Write-Host "(inbox does not exist yet: $inboxPath)"
        return
    }
    Get-Content -LiteralPath $inboxPath -Wait -Tail 20
}

# Speak a single turn by token (e.g. "1p", "12r"). Looks the line up in the
# inbox and hands the body to say.py. Used by `loud-reader read`.
function Invoke-ReadTurn([string]$token) {
    if (-not (Test-Path -LiteralPath $inboxPath)) {
        Write-Host "(no inbox file yet)"
        return
    }
    $line = Select-String -Path $inboxPath -Pattern "^\s*${token}\s+" -List | Select-Object -First 1
    if (-not $line) {
        Write-Host "(no line matching $token)"
        return
    }
    $body = ($line.Line -replace "^\s*${token}\s+", '')
    $flags = Get-Flags
    & python "$root\src\say.py" $body --voice $flags.voice --rate $flags.rate --pitch $flags.pitch --out "$root\archive\_adhoc.mp3" --play
}

# Forget the cursor so the watcher re-reads from the top on next tick.
function Reset-Cursor {
    $blank = @{ cursor = @(0, 'p'); threads = @{} } | ConvertTo-Json
    Set-Content -LiteralPath $posPath -Value $blank -Encoding UTF8
    Write-Host "cursor reset"
}

# Read pin/unpin/voice/etc. flags. Tiny helpers so the switch below stays readable.
function Set-FlagBool([string]$name, [bool]$value) {
    $f = Get-Flags
    $f.$name = $value
    Set-Flags $f
    Write-Host "$name = $value"
}
function Set-FlagString([string]$name, [string]$value) {
    $f = Get-Flags
    $f.$name = $value
    Set-Flags $f
    Write-Host "$name = $value"
}

# Main dispatch. Verb in $args[0] decides which branch runs.
$verb = $args[0]
if (-not $verb) {
    Show-Status
    exit 0
}
switch ($verb.ToLower()) {
    'on'         { Set-FlagBool 'master' $true; (Get-Flags).clipboard = $false; Set-Flags (Get-Flags); Write-Host 'loud-reader ON (codex only)' }
    'off'        { Set-FlagBool 'master' $false; Write-Host 'loud-reader OFF (silent)' }
    'status'     { Show-Status }
    'codex'      {
        if ($args[1] -eq 'on')  { Set-FlagBool 'codex' $true }
        elseif ($args[1] -eq 'off') { Set-FlagBool 'codex' $false }
        else { Write-Host 'usage: loud-reader codex on|off' ; exit 1 }
    }
    'clipboard'  {
        if ($args[1] -eq 'on')  { Set-FlagBool 'clipboard' $true;  Write-Host 'clipboard listening ON' }
        elseif ($args[1] -eq 'off') { Set-FlagBool 'clipboard' $false; Write-Host 'clipboard listening OFF' }
        else { Write-Host 'usage: loud-reader clipboard on|off' ; exit 1 }
    }
    'archive'    {
        if ($args[1] -eq 'on')  { Set-FlagBool 'archive_mp3' $true }
        elseif ($args[1] -eq 'off') { Set-FlagBool 'archive_mp3' $false }
        else { Write-Host 'usage: loud-reader archive on|off' ; exit 1 }
    }
    'voice'      { Set-FlagString 'voice' $args[1] }
    'engine'    {
        if ($args[1] -in @('edge','piper')) { Set-FlagString 'engine' $args[1] }
        else { Write-Host 'usage: loud-reader engine edge|piper' ; exit 1 }
    }
    'rate'       { Set-FlagString 'rate'  $args[1] }
    'start'      { Start-Watcher }
    'stop'       { Stop-Watcher }
    'tail'       { Show-InboxTail }
    'read'       { Invoke-ReadTurn $args[1] }
    'reset-cursor' { Reset-Cursor }
    'inbox'      { Write-Host $inboxPath }
    'pin'        {
        $f = Get-Flags
if (-not ($f.pin_threads -is [hashtable])) { $f.pin_threads = @{} }
        $f.pin_threads."$($args[1])" = $true
        Set-Flags $f
        Write-Host "pinned $($args[1])"
    }
    'unpin'      {
        $f = Get-Flags
        if ($f.pin_threads."$($args[1])") {
            $f.pin_threads.PSObject.Properties.Remove("$($args[1])")
            Set-Flags $f
            Write-Host "unpinned $($args[1])"
        } else { Write-Host "not pinned: $($args[1])" }
    }
    'toast'      {
        if ($args[1] -eq 'on')  { Set-FlagBool 'toast_on_speak' $true }
        elseif ($args[1] -eq 'off') { Set-FlagBool 'toast_on_speak' $false }
        else { Write-Host 'usage: loud-reader toast on|off' ; exit 1 }
    }
    'tray'       {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = (Get-Command python).Source
        $psi.Arguments = '-u src\tray.py'
        $psi.WorkingDirectory = $root
        $psi.UseShellExecute = $false
        $psi.EnvironmentVariables['PYTHONPATH'] = '$root\src'
        $psi.CreateNoWindow = $true
        [void][System.Diagnostics.Process]::Start($psi)
        Write-Host 'tray app started'
    }

        'refine'     {
        $rough = if ($args[1]) { $args[1] } else { Read-Host 'rough prompt' }
        if (-not $rough) { Write-Host 'usage: loud-reader refine <text>'; exit 1 }
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = (Get-Command python).Source
        # Use single-quoted Arguments string. PowerShell still parses it via
        # its own tokenizer; the trick is to surround $rough in literal quotes
        # so it stays one token after the Windows arg parser sees it.
        $quotedRough = '"' + $rough + '"'
        $psi.Arguments = '-u src\refine.py --canonical-only -- ' + $quotedRough
        # The trailing '--' tells argparse everything after is positional.
        $psi.WorkingDirectory = $root
        $psi.UseShellExecute = $false
        $psi.EnvironmentVariables['PYTHONPATH'] = $root + '\src'
        $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true
        $proc = [System.Diagnostics.Process]::Start($psi)
        $proc.WaitForExit()
        Write-Host $proc.StandardOutput.ReadToEnd()
    }
        'dod'        {
        & powershell -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\dod.ps1')
    }
    default      { Write-Host "unknown verb: $verb"; Write-Host 'try: on | off | status | codex on|off | clipboard on|off | archive on|off | voice <name> | rate <+-N%> | start | stop | tail | read <token> | reset-cursor | inbox | pin <id> | unpin <id>'; exit 1 }
}




