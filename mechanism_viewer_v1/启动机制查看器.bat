@echo off
cd /d "%~dp0"
python mechanism_client.py
if errorlevel 1 pause
