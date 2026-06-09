@echo off
cd /d "%~dp0"
set MECHANISM_VIEWER_PROFILE=viewer3
set MECHANISM_AGENT_VERSION=v3_fewshot
python mechanism_client.py
if errorlevel 1 pause
