@echo off
cd /d "%~dp0"
set "IMAGE_ROOT=%~1"
if not defined IMAGE_ROOT set "IMAGE_ROOT=%USERPROFILE%"
rem Use a free port for each launch so another local service or an older
rem Caption Editor window cannot receive requests meant for this instance.
py caption_editor.py --root "%IMAGE_ROOT%" --port 0
if errorlevel 1 pause
