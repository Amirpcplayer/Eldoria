$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path '.env')) {
    if (-not (Test-Path '.env.example')) { throw 'Missing .env.example.' }
    Copy-Item '.env.example' '.env'
    Write-Host 'Created .env from .env.example. Edit it and set BOT_TOKEN, ADMIN_ID and database credentials before continuing.' -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    py -3.12 -m venv .venv
}
$Python = (Resolve-Path '.venv\Scripts\python.exe').Path
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }

docker compose up -d postgres redis
if ($LASTEXITCODE -ne 0) { throw 'Could not start PostgreSQL/Redis. Ensure Docker Desktop is running.' }
& $Python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database migrations failed; the bot was not started.' }
& $Python -m main
if ($LASTEXITCODE -ne 0) { throw 'The bot exited with an error.' }
