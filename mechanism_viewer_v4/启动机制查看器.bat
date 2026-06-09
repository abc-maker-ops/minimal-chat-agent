@echo off
cd /d "%~dp0"
set MECHANISM_VIEWER_PROFILE=viewer4
set MECHANISM_AGENT_VERSION=v4_cot_fewshot
python mechanism_client.py
if errorlevel 1 pause
