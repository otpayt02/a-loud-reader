$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot\..").Path
$inbox = Join-Path $root 'inbox\inbox.md'
$archive = Join-Path $root 'archive'
New-Item -ItemType Directory -Force -Path (Split-Path $inbox) | Out-Null
New-Item -ItemType Directory -Force -Path $archive | Out-Null
"smoke p`n1p hello from the a loud reader smoke test`n" | Set-Content -LiteralPath $inbox -Encoding UTF8
$posPath = Join-Path $root 'state\positions.json'
@{ cursor = @(0,'p'); threads = @{} } | ConvertTo-Json | Set-Content -LiteralPath $posPath -Encoding UTF8
python "$root\src\say.py" "smoke test passed" --out "$archive\smoke.mp3"
if (Test-Path "$archive\smoke.mp3") {
    Write-Host "OK: smoke test produced an MP3 at $archive\smoke.mp3"
    Remove-Item "$archive\smoke.mp3" -Force
} else {
    Write-Host "FAIL: no MP3 was produced"
    exit 1
}
