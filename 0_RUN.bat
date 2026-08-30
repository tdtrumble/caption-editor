@echo off
cd /d "%~dp0"
set "IMAGE_ROOT=%~1"
if not defined IMAGE_ROOT set "IMAGE_ROOT=%USERPROFILE%"
py caption_editor.py --root "%IMAGE_ROOT%"
if errorlevel 1 pause
