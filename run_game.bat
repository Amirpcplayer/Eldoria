@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem aiogram>=3.25 supports Python 3.10-3.14, so use the project's tested Python 3.12.
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python 3.12 was not found.
  echo Install Python 3.12 x64 and enable the Python Launcher, then run this script again.
  echo Installed Python versions:
  py -0p
  pause
  exit /b 1
)

rem Standalone mode uses a local SQLite file and an in-process fakeredis backend.
set "DATABASE_URL=sqlite+aiosqlite:///./eldoria.db"
set "REDIS_URL=memory://"

if not exist ".env" (
  if not exist ".env.example" (
    echo ERROR: .env.example is missing.
    pause
    exit /b 1
  )
  copy ".env.example" ".env" >nul
  if errorlevel 1 (
    echo ERROR: Could not create .env. Check folder permissions.
    pause
    exit /b 1
  )
  echo.
  echo Created .env. Edit BOT_TOKEN and ADMIN_ID in that file, then run this script again.
  pause
  exit /b 1
)

findstr /i /b /c:"BOT_TOKEN=PASTE_YOUR_BOT_TOKEN_HERE" ".env" >nul
if not errorlevel 1 (
  echo ERROR: Replace the example BOT_TOKEN in .env before starting.
  pause
  exit /b 1
)
findstr /i /b /c:"BOT_TOKEN=" ".env" >nul
if errorlevel 1 (
  echo ERROR: BOT_TOKEN is missing from .env.
  pause
  exit /b 1
)
findstr /i /b /c:"ADMIN_ID=123456789" ".env" >nul
if not errorlevel 1 (
  echo WARNING: Change the example ADMIN_ID in .env to your numeric Telegram ID.
  pause
  exit /b 1
)

rem A previous run may have created .venv with Python 3.15 (or another version).
rem Detect that and recreate only the generated virtual environment with Python 3.12.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
  if errorlevel 1 (
    echo Existing .venv is not Python 3.12. Recreating the virtual environment...
    rmdir /s /q ".venv"
    if exist ".venv" (
      echo ERROR: Could not remove the old .venv folder. Close programs using it and delete .venv manually.
      pause
      exit /b 1
    )
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating Python 3.12 virtual environment...
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create the environment with Python 3.12.
    pause
    exit /b 1
  )
)

set "PY=.venv\Scripts\python.exe"
"%PY%" -m pip install --upgrade pip
if errorlevel 1 goto :failed

:launch
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 goto :failed
"%PY%" -m compileall -q .
if errorlevel 1 goto :failed
"%PY%" -m main
rem A trusted administrator upload creates this marker after applying an update.
rem Restart through this launcher so updated dependencies are installed first.
if exist ".restart_bot" (
  del /q ".restart_bot" >nul 2>&1
  echo.
  echo A bot update was applied. Restarting World Eldoria...
  goto :launch
)
if errorlevel 1 goto :failed
goto :eof

:failed
echo.
echo Startup failed. Check Python, package installation, .env credentials, and the error above.
pause
exit /b 1
