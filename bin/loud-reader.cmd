@echo off
REM loud-reader.cmd ? Windows shim that lets the user type `loud-reader`
REM from anywhere on PATH. Forwards everything to loud-reader.ps1.

setlocal
set "SCRIPT_DIR=%~dp0"
set "ROOT=%SCRIPT_DIR%.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\src\loud-reader.ps1" %*
endlocal
