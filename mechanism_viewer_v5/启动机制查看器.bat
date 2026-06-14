@echo off
chcp 65001 >nul
cd /d "%~dp0"
set MECHANISM_VIEWER_PROFILE=viewer5
set MECHANISM_AGENT_VERSION=v5_refine_fewshot
python mechanism_client.py
pause
