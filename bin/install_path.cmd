@echo off
REM install_path.cmd - copy loud-reader.cmd into %USERPROFILE%\bin\ and pin the repo root.

set "DEST=%USERPROFILE%\bin"
if not exist "%DEST%" mkdir "%DEST%"
set "SRC=%~dp0loud-reader.cmd"
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
powershell -NoProfile -Command "(Get-Content -LiteralPath '%SRC%' -Raw) -replace '__LOUD_READER_ROOT__','%ROOT%' | Set-Content -LiteralPath '%DEST%\loud-reader.cmd' -Encoding ASCII -NoNewline"
echo Installed %DEST%\loud-reader.cmd pointing at %ROOT%
echo To use in this shell: set PATH=%DEST%;%PATH%