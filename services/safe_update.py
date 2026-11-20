"""Validate and safely apply an administrator-uploaded World Eldoria ZIP update.

The update is an overlay only: it never deletes files, and it deliberately keeps
local configuration, databases, the virtual environment, and the Windows launcher.
"""
from __future__ import annotations

import filecmp
import os
import shutil
import stat
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
MAX_EXPANDED_BYTES = 300 * 1024 * 1024
MAX_FILES = 10_000
MAX_SINGLE_FILE_BYTES = 100 * 1024 * 1024
REQUIRED_PROJECT_FILES = {"main.py", "requirements.txt", "handlers/__init__.py"}

PROTECTED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    "update_backups", "updates", "logs", "backups",
}
PROTECTED_NAMES = {".env", ".restart_bot", "run_game.bat"}
PROTECTED_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pyc", ".log", ".wal", ".shm"}
BACKUP_MARKERS = (".bak_", ".before_", ".backup", ".old", ".orig")


class UpdateArchiveError(ValueError):
    """The uploaded file is not a safe, valid project update."""


@dataclass(frozen=True)
class _ArchiveEntry:
    info: zipfile.ZipInfo
    relative_path: PurePosixPath


def _normalized_parts(name: str) -> tuple[str, ...] | None:
    """Validate a ZIP entry name before using it as a filesystem path."""
    if "\x00" in name or "\\" in name:
        raise UpdateArchiveError("ZIP حاوی مسیر نامعتبر است.")
    if name.startswith("/") or (len(name) >= 2 and name[1] == ":"):
        raise UpdateArchiveError("ZIP حاوی مسیر مطلق است و پذیرفته نشد.")
    raw = name[:-1] if name.endswith("/") else name
    if not raw:
        return None
    parts = tuple(raw.split("/"))
    reserved_windows_names = {"CON", "PRN", "AUX", "NUL"} | {
        f"COM{number}" for number in range(1, 10)
    } | {f"LPT{number}" for number in range(1, 10)}
    if any(
        part in {"", ".", ".."}
        or any(char in part for char in '<>:"|?*')
        or part.endswith((" ", "."))
        or part.split(".", 1)[0].upper() in reserved_windows_names
        for part in parts
    ):
        raise UpdateArchiveError("ZIP حاوی مسیر ناامن یا نامعتبر برای ویندوز است.")
    return parts


def _is_junk(parts: tuple[str, ...]) -> bool:
    return bool(parts) and (parts[0] == "__MACOSX" or parts[-1] == ".DS_Store")


def _is_protected(relative: PurePosixPath) -> bool:
    parts = relative.parts
    name = relative.name
    lowered = name.lower()
    if any(part.lower() in PROTECTED_DIRS for part in parts):
        return True
    if lowered in PROTECTED_NAMES:
        return True
    if Path(lowered).suffix in PROTECTED_SUFFIXES:
        return True
    if any(marker in lowered for marker in BACKUP_MARKERS):
        return True
    return False


def _identify_project_prefix(paths: Iterable[tuple[str, ...]]) -> tuple[str, ...]:
    path_set = set(paths)
    required = {tuple(item.split("/")) for item in REQUIRED_PROJECT_FILES}
    if required.issubset(path_set):
        return ()

    candidates: set[tuple[str, ...]] = set()
    first_parts = {path[0] for path in path_set if len(path) > 1}
    for first in first_parts:
        prefix = (first,)
        if {prefix + item for item in required}.issubset(path_set):
            candidates.add(prefix)
    if len(candidates) != 1:
        raise UpdateArchiveError(
            "این ZIP نسخهٔ کامل پروژه نیست؛ فایل‌های main.py، requirements.txt و handlers/__init__.py باید داخل آن باشند."
        )
    return next(iter(candidates))


def _inspect_archive(archive: zipfile.ZipFile, archive_size: int) -> list[_ArchiveEntry]:
    if archive_size > MAX_ARCHIVE_BYTES:
        raise UpdateArchiveError("حجم ZIP بیشتر از حد مجاز ۲۰ مگابایت است.")

    raw_files: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []
    expanded_size = 0
    for info in archive.infolist():
        parts = _normalized_parts(info.filename)
        if parts is None:
            continue
        if info.is_dir():
            continue
        if _is_junk(parts):
            continue
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            raise UpdateArchiveError("ZIP شامل پیوند نمادین است؛ برای امنیت پذیرفته نشد.")
        if info.file_size > MAX_SINGLE_FILE_BYTES:
            raise UpdateArchiveError(f"فایل داخل ZIP بیش از حد بزرگ است: {parts[-1]}")
        expanded_size += info.file_size
        if expanded_size > MAX_EXPANDED_BYTES:
            raise UpdateArchiveError("حجم استخراج‌شدهٔ ZIP از ۳۰۰ مگابایت بیشتر است.")
        raw_files.append((info, parts))
        if len(raw_files) > MAX_FILES:
            raise UpdateArchiveError("تعداد فایل‌های داخل ZIP بیش از حد مجاز است.")

    if not raw_files:
        raise UpdateArchiveError("ZIP هیچ فایل قابل استفاده‌ای ندارد.")

    prefix = _identify_project_prefix(parts for _, parts in raw_files)
    entries: list[_ArchiveEntry] = []
    for info, parts in raw_files:
        if prefix:
            if parts[: len(prefix)] != prefix:
                raise UpdateArchiveError("فایل‌هایی خارج از پوشهٔ اصلی پروژه در ZIP پیدا شد.")
            relative_parts = parts[len(prefix):]
        else:
            relative_parts = parts
        if not relative_parts:
            continue
        relative = PurePosixPath(*relative_parts)
        if not _is_protected(relative):
            entries.append(_ArchiveEntry(info=info, relative_path=relative))

    if not entries:
        raise UpdateArchiveError("هیچ فایل قابل به‌روزرسانی در ZIP پیدا نشد.")
    # Windows paths are case-insensitive; reject duplicate/case-colliding names.
    seen_paths: set[str] = set()
    for entry in entries:
        key = entry.relative_path.as_posix().casefold()
        if key in seen_paths:
            raise UpdateArchiveError(
                f"دو فایل با مسیر تکراری یا تفاوت فقط در حروف بزرگ/کوچک وجود دارد: {entry.relative_path.as_posix()}"
            )
        seen_paths.add(key)
    # Require the actual program entry point to be included in the update payload.
    if PurePosixPath("main.py") not in {entry.relative_path for entry in entries}:
        raise UpdateArchiveError("فایل main.py در بخش قابل‌اعمال ZIP موجود نیست.")
    return entries


def apply_update_archive(archive_path: str | Path, project_root: str | Path) -> tuple[list[str], str | None]:
    """Validate, back up, and overlay an uploaded release ZIP.

    Returns (changed relative paths, backup directory or None). A restart marker is
    only created when at least one file changed. Existing files are backed up first;
    files not present in the archive are never deleted.
    """
    archive_path = Path(archive_path)
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise UpdateArchiveError("پوشهٔ اصلی پروژه پیدا نشد.")
    if not archive_path.is_file():
        raise UpdateArchiveError("فایل ZIP پیدا نشد.")
    if not zipfile.is_zipfile(archive_path):
        raise UpdateArchiveError("فایل ارسالی ZIP معتبر نیست.")

    with tempfile.TemporaryDirectory(prefix="eldoria_update_stage_") as temp_dir:
        stage_root = Path(temp_dir) / "stage"
        stage_root.mkdir()
        staged: list[tuple[PurePosixPath, Path]] = []
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                entries = _inspect_archive(archive, archive_path.stat().st_size)
                for entry in entries:
                    stage_path = stage_root.joinpath(*entry.relative_path.parts)
                    stage_path.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(entry.info, "r") as source, stage_path.open("wb") as destination:
                        shutil.copyfileobj(source, destination, length=1024 * 1024)
                    staged.append((entry.relative_path, stage_path))
        except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
            raise UpdateArchiveError(f"خواندن ZIP ناموفق بود: {exc}") from exc

        changed_candidates: list[tuple[PurePosixPath, Path]] = []
        for relative, stage_path in staged:
            destination = root.joinpath(*relative.parts)
            try:
                destination.resolve(strict=False).relative_to(root)
            except ValueError as exc:
                raise UpdateArchiveError("مسیر یک فایل از پوشهٔ پروژه خارج می‌شود.") from exc
            if destination.is_symlink():
                raise UpdateArchiveError(f"مقصد فایل پیوند نمادین است: {relative.as_posix()}")
            current = destination.parent
            while current != root:
                if current.is_symlink():
                    raise UpdateArchiveError(f"پوشهٔ مقصد پیوند نمادین است: {current}")
                current = current.parent
            if destination.exists() and not destination.is_file():
                raise UpdateArchiveError(f"مقصد یک فایل عادی نیست: {relative.as_posix()}")
            if destination.is_file() and filecmp.cmp(stage_path, destination, shallow=False):
                continue
            changed_candidates.append((relative, stage_path))

        if not changed_candidates:
            return [], None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        backup_root = root.parent / f"{root.name}_update_backups" / timestamp
        changes: list[tuple[Path, Path | None]] = []
        try:
            for relative, stage_path in changed_candidates:
                destination = root.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                backup_file: Path | None = None
                if destination.exists():
                    backup_file = backup_root.joinpath(*relative.parts)
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(destination, backup_file)

                temporary_target = destination.with_name(
                    f".{destination.name}.update-{uuid.uuid4().hex}.tmp"
                )
                try:
                    shutil.copy2(stage_path, temporary_target)
                    os.replace(temporary_target, destination)
                finally:
                    if temporary_target.exists():
                        temporary_target.unlink(missing_ok=True)
                changes.append((destination, backup_file))

            marker = root / ".restart_bot"
            marker_tmp = root / f".restart_bot.{uuid.uuid4().hex}.tmp"
            marker_tmp.write_text(f"updated={timestamp}\n", encoding="utf-8")
            os.replace(marker_tmp, marker)
        except Exception:
            for destination, backup_file in reversed(changes):
                try:
                    if backup_file is not None and backup_file.exists():
                        restore_temp = destination.with_name(
                            f".{destination.name}.restore-{uuid.uuid4().hex}.tmp"
                        )
                        shutil.copy2(backup_file, restore_temp)
                        os.replace(restore_temp, destination)
                    else:
                        destination.unlink(missing_ok=True)
                except OSError:
                    # Keep the backup directory for manual recovery if rollback fails.
                    pass
            raise

        return [relative.as_posix() for relative, _ in changed_candidates], str(backup_root)
