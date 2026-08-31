@echo off
cd /d "%~dp0"

set "IMAGE_ROOT=%~1"
if not defined IMAGE_ROOT set "IMAGE_ROOT=%USERPROFILE%"
set "HOST=0.0.0.0"
set "PORT=8070"
set "KEYS_FILE=%~dp0access_keys.txt"
set "READ_ONLY=N"
set "NO_BROWSER=N"

echo Configure Caption Editor. Press Enter to accept the value in brackets.
set /p "IMAGE_ROOT=Image root [%IMAGE_ROOT%]: "
set /p "HOST=Network interface [%HOST%]: "
set /p "PORT=TCP port [%PORT%]: "
set /p "KEYS_FILE=Access keys file [%KEYS_FILE%]: "
set /p "READ_ONLY=Run in read-only mode? (Y/N) [%READ_ONLY%]: "
set /p "NO_BROWSER=Disable automatic browser opening? (Y/N) [%NO_BROWSER%]: "

set "READ_ONLY_ARG="
if /i "%READ_ONLY%"=="Y" set "READ_ONLY_ARG=--read-only"
if /i "%READ_ONLY%"=="YES" set "READ_ONLY_ARG=--read-only"

set "NO_BROWSER_ARG="
if /i "%NO_BROWSER%"=="Y" set "NO_BROWSER_ARG=--no-browser"
if /i "%NO_BROWSER%"=="YES" set "NO_BROWSER_ARG=--no-browser"

py caption_editor.py --root "%IMAGE_ROOT%" --host "%HOST%" --port "%PORT%" --keys-file "%KEYS_FILE%" %READ_ONLY_ARG% %NO_BROWSER_ARG%
if errorlevel 1 pause
