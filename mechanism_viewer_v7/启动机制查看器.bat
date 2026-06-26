@echo off
chcp 65001 >nul
set MECHANISM_VIEWER_PROFILE=viewer7
cd /d "%~dp0"
python mechanism_client.py
pause
