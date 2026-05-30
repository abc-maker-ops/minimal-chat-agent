@echo off
cd /d "%~dp0"
set MECHANISM_AGENT_VERSION=v2_fewshot
python mechanism_client.py
if errorlevel 1 pause
