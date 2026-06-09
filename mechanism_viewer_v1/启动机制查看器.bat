@echo off
cd /d "%~dp0"
set MECHANISM_VIEWER_PROFILE=viewer1
set MECHANISM_AGENT_VERSION=v1_minimal
python mechanism_client.py
if errorlevel 1 pause
