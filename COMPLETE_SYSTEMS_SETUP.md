# World Eldoria — Complete Systems Pack

This pack extends the current RPG with the remaining planned systems and profile Fan Art integration.

## Added
- Profile Fan Art selection and actual image display in player profile.
- Group `/profile` command; selected Fan Art can be shown in group chats when enabled.
- Group `/eldoria` entry command.
- Settings: notifications + group Fan Art visibility.
- Party: create, join by ID, leave, member limits.
- Guild: create and membership foundation.
- Dungeon: run/floor progression foundation.
- PvP: player challenge foundation and `/pvp` by replying to a player's message.
- Ranking: level/XP/gold leaderboard.
- Crafting: recipe storage and material/gold consumption service.
- Pets: pet catalogue, ownership and activation service.
- Events: active event catalogue.
- Database migration for all new tables and profile Fan Art.
- Social seed script.

## Install

```powershell
alembic upgrade head
python -m utils.seed_social_systems
```

Then validate:

```powershell
python -m py_compile main.py handlers\social_systems.py handlers\profile.py services\social_service.py models\social_systems.py
python -m pytest -q
```

## Group commands

- `/eldoria`
- `/profile`
- Reply to a player and use `/pvp`
- `/party_join PARTY_ID`
- `/guild_create GuildName TAG`

## Fan Art profile

After a Fan Art is owned, open **Profile → 🎨 Fan Art پروفایل** and choose one.
The selected image is displayed in the profile. In groups, `/profile` displays the same image when the player's setting **نمایش Fan Art در گپ** is enabled.

## Important

The new player-facing systems do not hardcode any Telegram user ID. Admin-only Fan Art administration continues to use `ADMIN_ID` from settings.
