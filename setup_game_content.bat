@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo World Eldoria - Populate initial game content
echo =============================================
echo IMPORTANT: Stop the bot before continuing.
echo This script targets the standalone SQLite database: eldoria.db
echo It does not delete player accounts or inventory.
echo.

if not exist ".env" (
  echo ERROR: .env was not found. Run run_game.bat once and configure BOT_TOKEN and ADMIN_ID first.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Python environment not found. Run run_game.bat once to install dependencies.
  pause
  exit /b 1
)

rem Match the standalone database used by run_game.bat, regardless of DATABASE_URL in .env.
set "DATABASE_URL=sqlite+aiosqlite:///./eldoria.db"
set "REDIS_URL=memory://"

".venv\Scripts\python.exe" setup_game_content.py
if errorlevel 1 (
  echo.
  echo ERROR: Game content setup failed. Read the error above and do not delete eldoria.db.
  pause
  exit /b 1
)

echo.
echo Setup finished. Start run_game.bat, open /menu in Telegram, and press Adventure.
pause
