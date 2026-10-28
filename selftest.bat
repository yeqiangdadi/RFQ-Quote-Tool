@echo off
chcp 65001 >nul
cd /d "%~dp0"
title RFQ Quote Tool - Self Test
set "PYTHONUTF8=1"

if not exist ".venv\Scripts\python.exe" (
  echo The environment is not installed yet.
  echo Run install.bat first, then run this self test again.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m quote_app.selftest
echo.
pause
