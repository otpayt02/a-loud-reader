# diagnose.ps1 -- one-shot health check for a-loud-reader.
# Walks through everything that could be wrong and prints evidence.

$ErrorActionPreference = 'Continue'
$root = (Resolve-Path "$PSScriptRoot\..").Path
Write-Host "=== a-loud-reader diagnose ==="
Write-Host "repo            : $root"
Write-Host "python          : $((Get-Command python).Source)"
Write-Host "python version  : $(python --version 2>&1)"

# Required packages
foreach ($pkg in 'edge-tts','watchdog','pyperclip','pywin32','pystray','Pillow','plyer') {
    $present = pip show $pkg 2>&1 | Select-String -Pattern '^Name:'
    if ($present) { Write-Host "package $pkg : OK" } else { Write-Host "package $pkg : MISSING (pip install $pkg)" }
}

# Watcher state
$pidFile = Join-Path $root 'state\watcher.pid'
$running = Test-Path -LiteralPath $pidFile
$actual = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $PID }
Write-Host "watcher pidfile : $running"
Write-Host "actual python   : $(@($actual).Count) process(es)"
if ($running -and -not $actual) {
    Write-Host "  -> stale pid file; run: loud-reader stop; Remove-Item state\watcher.pid"
}

# Flags
$flagsPath = Join-Path $root 'state\flags.json'
if (Test-Path -LiteralPath $flagsPath) {
    Write-Host "flags.json      :"
    Get-Content -LiteralPath $flagsPath | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "flags.json      : missing (will be created on first run)"
}

# Cursor
$posPath = Join-Path $root 'state\positions.json'
if (Test-Path -LiteralPath $posPath) {
    $pos = Get-Content -LiteralPath $posPath -Raw | ConvertFrom-Json
    Write-Host "cursor          : $($pos.cursor -join ',')"
}

# Watcher log tail
$logPath = Join-Path $root 'state\watcher.log'
if (Test-Path -LiteralPath $logPath) {
    Write-Host "watcher.log tail:"
    Get-Content -LiteralPath $logPath -Tail 20 | ForEach-Object { Write-Host "  $_" }
}

# Live test: write a turn, wait, check archive.
Write-Host "live test       : appending 1p diagnose test..."
$inbox = Join-Path $root 'inbox\inbox.md'
if (-not (Test-Path -LiteralPath $inbox)) { '' | Set-Content -LiteralPath $inbox -Encoding UTF8 }
"1p diagnose test" | Add-Content -LiteralPath $inbox -Encoding UTF8
Start-Sleep -Seconds 5
$today = Get-Date -Format 'yyyy-MM-dd'
$newMp3 = Get-ChildItem (Join-Path $root "archive\$today") -Filter '*.mp3' -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddSeconds(-15) } |
    Select-Object -First 1
if ($newMp3) {
    Write-Host "live test       : OK -> $($newMp3.FullName) ($($newMp3.Length) bytes)"
} else {
    Write-Host "live test       : NO MP3 produced. Is master on? Try: loud-reader on; loud-reader start"
}