@echo off
REM install_path.cmd ? copy loud-reader.cmd into %USERPROFILE%\bin so it's on PATH.
set "DEST=%USERPROFILE%\bin"
if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%~dp0loud-reader.cmd" "%DEST%\loud-reader.cmd" >NUL
echo Added %DEST%\loud-reader.cmd
echo To activate in this shell: set PATH=%DEST%;%PATH%
