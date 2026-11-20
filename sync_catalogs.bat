@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Python environment not found. Run run_game.bat once first.
  pause
  exit /b 1
)
if not exist ".env" (
  echo ERROR: .env was not found. Run run_game.bat once and finish setup first.
  pause
  exit /b 1
)

rem Use the same local SQLite database as the standalone Windows launcher.
set "DATABASE_URL=sqlite+aiosqlite:///./eldoria.db"
set "REDIS_URL=memory://"

echo.
echo ===============================================
echo       WORLD ELDORIA - CATALOG SYNC
echo ===============================================
echo Stop the bot before syncing. Backup eldoria.db first.
echo This tool adds/updates catalog data; it does not clear player data.
echo.
echo  1. ALL catalogs
echo 2. Monsters
echo 3. Adventure areas and enemies
echo 4. Items and materials
echo 5. Equipment
echo 6. Skills
echo 7. Quests (also checks enemy/skill targets)
echo 8. Crafting recipes
echo 9. Pets and starter event
echo 10. Fan Art catalog status
echo 0. Exit
echo.
set /p "CHOICE=Choose a catalog to sync: "

if "%CHOICE%"=="1" (
  set "CATALOG=all"
  goto :run
)
if "%CHOICE%"=="2" (
  set "CATALOG=monsters"
  goto :run
)
if "%CHOICE%"=="3" (
  set "CATALOG=adventure"
  goto :run
)
if "%CHOICE%"=="4" (
  set "CATALOG=items"
  goto :run
)
if "%CHOICE%"=="5" (
  set "CATALOG=equipment"
  goto :run
)
if "%CHOICE%"=="6" (
  set "CATALOG=skills"
  goto :run
)
if "%CHOICE%"=="7" (
  set "CATALOG=quests"
  goto :run
)
if "%CHOICE%"=="8" (
  set "CATALOG=crafting"
  goto :run
)
if "%CHOICE%"=="9" (
  set "CATALOG=pets-events"
  goto :run
)
if "%CHOICE%"=="10" (
  set "CATALOG=fanart"
  goto :run
)
if "%CHOICE%"=="0" goto :eof

echo Invalid choice.
pause
exit /b 1

:run
echo.
".venv\Scripts\python.exe" sync_catalogs.py %CATALOG%
if errorlevel 1 (
 echo.
  echo ERROR: Synchronization failed. Keep eldoria.db and read the error above.
  pause
  exit /b 1
)
echo.
echo Finished.
pause
