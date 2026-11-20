from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from services.safe_update import UpdateArchiveError, apply_update_archive


def make_project_zip(path: Path, *, main_code: str, extra: dict[str, str] | None = None) -> Path:
    files = {
        "World_Eldoria_Standalone_Windows/main.py": main_code,
        "World_Eldoria_Standalone_Windows/requirements.txt": "aiogram>=3.25,<4.0\n",
        "World_Eldoria_Standalone_Windows/handlers/__init__.py": '"handlers"\n',
        "World_Eldoria_Standalone_Windows/config/settings.py": "# updated settings module\n",
    }
    if extra:
        files.update(extra)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return path


def test_valid_update_backups_replaced_files_and_sets_restart_marker(tmp_path: Path) -> None:
    project = tmp_path / "World_Eldoria_Standalone_Windows"
    project.mkdir()
    (project / "main.py").write_text("print('old')\n", encoding="utf-8")
    (project / "requirements.txt").write_text("old-requirement\n", encoding="utf-8")
    (project / ".env").write_text("BOT_TOKEN=keep-me\n", encoding="utf-8")
    (project / "eldoria.db").write_bytes(b"user-database")
    (project / "run_game.bat").write_text("launcher-with-restart-loop\n", encoding="utf-8")

    archive_path = make_project_zip(tmp_path / "release.zip", main_code="print('new')\n", extra={
        "World_Eldoria_Standalone_Windows/.env": "BOT_TOKEN=overwrite-me\n",
        "World_Eldoria_Standalone_Windows/eldoria.db": "wipe",
        "World_Eldoria_Standalone_Windows/run_game.bat": "old-launcher\n",
    })

    changed, backup = apply_update_archive(archive_path, project)

    assert "main.py" in changed
    assert "config/settings.py" in changed
    assert (project / "main.py").read_text(encoding="utf-8") == "print('new')\n"
    assert (project / ".env").read_text(encoding="utf-8") == "BOT_TOKEN=keep-me\n"
    assert (project / "eldoria.db").read_bytes() == b"user-database"
    assert (project / "run_game.bat").read_text(encoding="utf-8") == "launcher-with-restart-loop\n"
    assert (project / ".restart_bot").is_file()
    assert backup is not None
    assert (Path(backup) / "main.py").read_text(encoding="utf-8") == "print('old')\n"


def test_rejects_zip_path_traversal_without_writing_outside_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("main.py", "print('new')\n")
        archive.writestr("requirements.txt", "aiogram\n")
        archive.writestr("handlers/__init__.py", "")
        archive.writestr("../../outside.txt", "not allowed")

    with pytest.raises(UpdateArchiveError):
        apply_update_archive(archive_path, project)
    assert not (tmp_path / "outside.txt").exists()
    assert not (project / "main.py").exists()


def test_rejects_zip_that_is_not_a_project_release(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    archive_path = tmp_path / "not-release.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("readme.txt", "just a document")

    with pytest.raises(UpdateArchiveError):
        apply_update_archive(archive_path, project)


def test_second_identical_update_does_not_schedule_restart(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    archive_path = make_project_zip(tmp_path / "release.zip", main_code="print('same')\n")

    changed, _ = apply_update_archive(archive_path, project)
    assert changed
    (project / ".restart_bot").unlink()

    changed_again, backup_again = apply_update_archive(archive_path, project)
    assert changed_again == []
    assert backup_again is None
    assert not (project / ".restart_bot").exists()


def test_rejects_non_zip_archive(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    file_path = tmp_path / "text.zip"
    file_path.write_text("this is not a zip", encoding="utf-8")

    with pytest.raises(UpdateArchiveError):
        apply_update_archive(file_path, project)


def test_rejects_case_colliding_paths_for_windows(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    archive_path = tmp_path / "case-collision.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("main.py", "print('new')\n")
        archive.writestr("MAIN.py", "print('conflict')\n")
        archive.writestr("requirements.txt", "aiogram\n")
        archive.writestr("handlers/__init__.py", "")

    with pytest.raises(UpdateArchiveError):
        apply_update_archive(archive_path, project)
    assert not (project / "main.py").exists()
