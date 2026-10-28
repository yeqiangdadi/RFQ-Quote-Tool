@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title RFQ Quote Tool - Setup

set "LOG=%~dp0install.log"
break > "%LOG%" 2>nul
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "WHEELS="
if exist "wheels\*.whl" set "WHEELS=1"

echo ============================================
echo   RFQ Quote Tool - first-time setup
if defined WHEELS echo   Offline install: no internet needed.
if not defined WHEELS echo   Needs internet. About 1-2 GB download.
echo ============================================
echo   Folder: %CD%
echo.

echo [check] Is this folder really extracted? ...
echo "%CD%" | find /I "AppData\Local\Temp" >nul && goto inzip
echo "%CD%" | find /I "Rar$" >nul && goto inzip
echo "%CD%" | find /I "Temp1_" >nul && goto inzip
echo       OK
echo.

echo [check] Looking for 64-bit Python 3.10 - 3.13 ...
set "PYEXE="
call :probe py -3.12
if not defined PYEXE call :probe py -3.13
if not defined PYEXE call :probe py -3.11
if not defined PYEXE call :probe py -3.10
if not defined PYEXE call :probe py -3.14
set "SKIP="
where python 2>nul | find /I "WindowsApps" >nul && set "SKIP=1"
if not defined SKIP call :probe python
set "SKIP="
where python3 2>nul | find /I "WindowsApps" >nul && set "SKIP=1"
if not defined SKIP call :probe python3
if not defined PYEXE goto nopython

:pychecks
echo       using: "%PYEXE%"
"%PYEXE%" --version
"%PYEXE%" -c "import sys,struct;print('       exe :',sys.executable);print('       arch:',struct.calcsize('P')*8,'bit')"
if errorlevel 1 goto nopython
"%PYEXE%" -c "import struct,sys;sys.exit(0 if struct.calcsize('P')*8==64 else 1)"
if errorlevel 1 goto python32
"%PYEXE%" -c "import sys;sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,13) else 1)"
if errorlevel 1 goto pyversion
echo       OK
echo.

echo [check] Can we write to this folder? ...
mkdir ".venv_write_test" >nul 2>nul
if errorlevel 1 goto nowrite
rmdir ".venv_write_test" >nul 2>nul
echo       OK
echo.

echo === setup %DATE% %TIME% === >> "%LOG%"
"%PYEXE%" --version >> "%LOG%" 2>&1

if exist ".venv\Scripts\python.exe" goto checkvenv
if not exist ".venv" goto makevenv
echo [1/4] Removing incomplete .venv from a previous attempt ...
rmdir /s /q ".venv"

:makevenv
echo [1/4] Creating virtual environment .venv ...
"%PYEXE%" -m venv .venv >> "%LOG%" 2>&1
set "VENVRC=!errorlevel!"
if not "!VENVRC!"=="0" goto venvfail
if not exist ".venv\Scripts\python.exe" goto venvfail
".venv\Scripts\python.exe" -m pip --version >> "%LOG%" 2>&1
echo       OK
echo.
goto deps

:checkvenv
".venv\Scripts\python.exe" -c "import sys;sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,13) else 1)" >nul 2>nul
if errorlevel 1 (
  echo [1/4] Removing .venv that cannot be used ...
  rmdir /s /q ".venv"
  goto makevenv
)
echo [1/4] Existing .venv found, skipping creation.
echo.

:deps
echo [2/4] Preparing pip ...
if defined WHEELS goto skipupgrade
".venv\Scripts\python.exe" -m pip install --upgrade pip -q --timeout 60 --retries 2 --log "%LOG%"
:skipupgrade
echo.
echo [3/4] Installing dependencies (5-20 minutes, do not close this window) ...
if not defined WHEELS goto netpip
set "NWHEELS=0"
for /f %%C in ('dir /b "wheels\*.whl" 2^>nul ^| find /c ".whl"') do set "NWHEELS=%%C"
echo       !NWHEELS! packages are bundled, no internet needed.
echo       This step unpacks about 700 MB, please be patient ...
".venv\Scripts\python.exe" -m pip install --isolated --no-index --find-links "wheels" --no-compile -r requirements.txt --log "%LOG%"
if not errorlevel 1 goto verify
echo.
echo       The bundled wheels failed to install. Last lines of install.log:
call :logtail
echo.
echo       Trying the network as a fallback ...
goto netpip

:netpip
rem A stale proxy on this machine kills every network fallback; bypass it.
set "HTTP_PROXY="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="
call :pipreq
if errorlevel 1 (
  echo.
  echo       PyPI is slow or blocked, retrying with a China mirror ...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt --timeout 60 --retries 3 --log "%LOG%" -i https://pypi.tuna.tsinghua.edu.cn/simple --no-compile
  if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt --timeout 60 --retries 3 --log "%LOG%" -i https://mirrors.aliyun.com/pypi/simple --no-compile
    if errorlevel 1 goto pipfail
  )
)

:verify
echo.
echo [4/4] Verifying imports ...
".venv\Scripts\python.exe" -c "import fastapi,openpyxl,pypdfium2,uvicorn;print('       web deps OK')" >> "%LOG%" 2>&1
if errorlevel 1 goto verifyfail
".venv\Scripts\python.exe" -c "import paddle,paddleocr;print('       paddle',paddle.__version__)" >> "%LOG%" 2>&1
if errorlevel 1 goto verifyfail

echo.
echo Setup finished. Double-click start.bat to launch.
pause
exit /b 0

:probe
set "PYEXE="
for /f "delims=" %%I in ('%~1 %~2 -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%I"
exit /b 0

:pipreq
".venv\Scripts\python.exe" -m pip install -r requirements.txt --timeout 60 --retries 3 --log "%LOG%" --no-compile
exit /b %errorlevel%

:logtail
echo.
if not exist "%LOG%" exit /b 0
echo ---- last lines of install.log ----
powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG%' -Tail 15" 2>nul
exit /b 0

:inzip
echo.
echo ERROR: This script is running from inside the ZIP archive preview.
echo Windows only lets you run files there; it cannot create .venv.
echo.
echo Close this window, then:
echo   1. Right-click the ZIP file in Explorer
echo   2. Choose "Extract All..." (or use 7-Zip)
echo   3. Open the extracted folder, for example D:\RFQ-Quote-Tool
echo   4. Run install.bat there
goto fail

:nopython
echo.
echo       No Python 3.10 - 3.13 found on this computer.
if not exist "python\python-*-amd64.exe" goto nopython_manual
if defined PYTRIED goto nopython_manual
set "PYTRIED=1"
for %%F in ("python\python-*-amd64.exe") do set "PYINST=%%~fF"
echo.
echo   Python is required once. This tool bundles Python 3.12 and can
echo   install it for the current user now: no admin rights, no PATH
echo   settings, about 1 minute.
echo.
choice /C YN /N /M "  Install Python 3.12 now? [Y/N] "
if errorlevel 2 goto nopython_manual
echo.
echo   Installing Python 3.12, please wait (no progress is shown) ...
start "" /wait "%PYINST%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_doc=0 Include_launcher=1 InstallLauncherAllUsers=0 Shortcuts=0
set "IRC=!errorlevel!"
echo   installer exit code: !IRC!
if "!IRC!"=="0" goto findnewpy
if "!IRC!"=="3010" goto findnewpy
goto pyinstallfail

:findnewpy
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYEXE if exist "%ProgramFiles%\Python312\python.exe" set "PYEXE=%ProgramFiles%\Python312\python.exe"
if not defined PYEXE goto pyinstallfail
echo       Python installed.
echo.
goto pychecks

:nopython_manual
echo.
echo ERROR: Python 3.10 - 3.13 (64-bit) is required but was not found.
echo Install Python 3.12 from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during installation.
echo If "python" opens the Microsoft Store, turn off the App Execution
echo Aliases for python.exe in Windows Settings, then retry.
goto fail

:python32
echo.
echo ERROR: The detected Python is 32-bit. PaddleOCR needs 64-bit Python.
echo Uninstall it and install the 64-bit build from python.org.
goto fail

:pyversion
echo.
echo       Unsupported Python: %PYEXE%
echo       PaddleOCR in this tool needs Python 3.10 - 3.13 (64-bit).
set "PYEXE="
goto nopython

:nowrite
echo.
echo ERROR: This folder is not writable: %CD%
echo Extract the ZIP to a normal folder such as D:\RFQ-Quote-Tool
echo or your Desktop, then run install.bat again.
goto fail

:venvfail
echo.
echo ERROR: Failed to create .venv (exit code %VENVRC%).
echo Common causes:
echo   - Running inside the ZIP preview instead of an extracted folder
echo   - Antivirus blocking the folder
echo   - Python installed from the Microsoft Store
goto logtail2

:pyinstallfail
echo.
echo ERROR: Python installation did not complete.
echo Try again, or install Python 3.12 manually from
echo https://www.python.org/downloads/ and rerun install.bat.
goto logtail2

:verifyfail
echo.
echo ERROR: Packages installed but cannot be imported.
echo Common causes:
echo   - Antivirus quarantined DLLs in .venv
echo   - Missing Microsoft VC++ 2015-2022 runtime (x64)
goto logtail2

:pipfail
echo.
echo ERROR: Dependency installation failed.
echo Check the internet connection, then run install.bat again.
goto logtail2

:logtail2
call :logtail
goto fail

:fail
echo.
echo Do NOT run start.bat until the setup says "Setup finished".
echo Full log: %LOG%
echo If it still fails, send install.log to whoever maintains this tool.
pause
exit /b 1
