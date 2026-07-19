@echo off
cd /d "%~dp0"
set MECHANISM_VIEWER_PROFILE=viewer11
python mechanism_client.py
pause
