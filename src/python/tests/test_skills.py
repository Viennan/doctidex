from __future__ import annotations

from pathlib import Path

import pytest

from whero.doctidex import skills
from whero.doctidex.errors import CommandFailure


def test_resolve_skill_root_uses_source_tree() -> None:
    root = skills.resolve_skill_root()

    assert (root / "doctidex-git" / "SKILL.md").is_file()


def test_install_skills_copies_and_replaces_only_the_skill_directory(tmp_path: Path) -> None:
    destination = tmp_path / "destination"

    installed, normalized = skills.install_skills(destination)

    assert installed == ("doctidex-git",)
    assert normalized == destination.resolve()
    skill_target = normalized / "doctidex-git"
    assert (skill_target / "SKILL.md").is_file()
    assert not (skill_target / "references" / "overview.md").is_symlink()

    sibling = normalized / "other-skill"
    sibling.mkdir()
    stale = skill_target / "stale.txt"
    stale.write_text("stale")

    skills.install_skills(destination)

    assert sibling.is_dir()
    assert not stale.exists()


def test_install_skills_rejects_file_destination(tmp_path: Path) -> None:
    destination = tmp_path / "destination"
    destination.write_text("not a directory")

    with pytest.raises(CommandFailure) as exc_info:
        skills.install_skills(destination)

    assert exc_info.value.code == "skills.install.target.unavailable"


def test_resolve_skill_root_falls_back_to_packaged_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packaged = tmp_path / "packaged"
    (packaged / "doctidex-git").mkdir(parents=True)
    (packaged / "doctidex-git" / "SKILL.md").write_text("skill")

    monkeypatch.setattr(skills, "_SOURCE_SKILLS", tmp_path / "missing-source")
    monkeypatch.setattr(skills, "_PACKAGED_SKILLS", packaged)

    assert skills.resolve_skill_root() == packaged


def test_resolve_skill_root_ignores_unrelated_source_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "skills"
    source.mkdir()
    packaged = tmp_path / "packaged"
    (packaged / "doctidex-git").mkdir(parents=True)
    (packaged / "doctidex-git" / "SKILL.md").write_text("skill")

    monkeypatch.setattr(skills, "_SOURCE_SKILLS", source)
    monkeypatch.setattr(skills, "_PACKAGED_SKILLS", packaged)

    assert skills.resolve_skill_root() == packaged
