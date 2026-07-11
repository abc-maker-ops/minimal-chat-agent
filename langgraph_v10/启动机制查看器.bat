@echo off
chcp 65001 >nul
set MECHANISM_VIEWER_PROFILE=viewer10
cd /d "%~dp0\..\mechanism_viewer_v10"
python mechanism_client.py
pause
