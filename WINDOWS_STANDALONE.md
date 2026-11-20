# Windows standalone quick start

1. Install Python 3.12 (recommended) and make sure the Python Launcher (`py`) is available.
2. Run `run_game.bat` once. It creates `.env.example`-based configuration and stops safely.
3. Edit `.env`: set the real Telegram `BOT_TOKEN` and your numeric `ADMIN_ID`. Do not share this file.
4. Double-click `run_game.bat` again. The script creates `.venv`, installs dependencies, and starts the bot.

Standalone mode forces `DATABASE_URL=sqlite+aiosqlite:///./eldoria.db` and `REDIS_URL=memory://`, overriding those two values from `.env`. SQLite data persists beside the project in `eldoria.db`; Redis-compatible transient state is provided by `fakeredis` and is cleared when the process stops. The Lua extra is required for atomic combat operations and scheduler locks. No PostgreSQL, Redis server, Docker, or Alembic migration is needed for this mode. Internet access is needed for initial dependency installation and Telegram API access.

For a persistent Redis backend and PostgreSQL, follow the main `README.md` and use `scripts/start.ps1` instead. The optional `TELEGRAM_PROXY` setting lets users behind a proxy configure it; the application no longer assumes a proxy is listening on a developer-specific local port.
