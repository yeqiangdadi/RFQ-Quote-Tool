@echo off
chcp 65001 >nul
cd /d "%~dp0"
title RFQ Quote Tool
set "PYTHONUTF8=1"

if not exist ".venv\Scripts\python.exe" (
  echo First run: the environment is not installed yet.
  call "%~dp0install.bat"
)

if not exist ".venv\Scripts\python.exe" (
  echo .venv is still missing. Please run install.bat manually.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -c "import fastapi,uvicorn,openpyxl,pypdfium2" >nul 2>nul
if errorlevel 1 (
  echo.
  echo Dependencies are missing or broken - running install.bat again ...
  call "%~dp0install.bat"
  ".venv\Scripts\python.exe" -c "import fastapi,uvicorn,openpyxl,pypdfium2" >nul 2>nul
  if errorlevel 1 (
    echo.
    echo Still not working. Please run install.bat once more and watch the messages.
    echo If it fails, send the file install.log from this folder.
    pause
    exit /b 1
  )
)

echo.
echo Starting RFQ Quote Tool ...
echo The browser will open at http://127.0.0.1:8765
echo Keep this window open. Press Ctrl+C to stop the service.
echo.
".venv\Scripts\python.exe" -m quote_app.server
if errorlevel 1 (
  echo.
  echo The service stopped with an error. See the messages above.
  pause
)
