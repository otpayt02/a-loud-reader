@echo off
REM loud-reader.cmd - PATH shim for a-loud-reader.
REM The installer rewrites the LOUD_READER_ROOT line below to point at
REM the repo on this machine. Do not edit the marker line by hand;
REM re-run bin\install_path.cmd if the repo moves.

setlocal
set "ROOT=__LOUD_READER_ROOT__"
if exist "%ROOT%\src\loud-reader.ps1" goto found
echo Could not find src\loud-reader.ps1 under %ROOT% - re-run bin\install_path.cmd
exit /b 1
:found
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\src\loud-reader.ps1" %*
endlocal