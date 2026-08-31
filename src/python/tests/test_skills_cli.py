from __future__ import annotations

from pathlib import Path

from conftest import CliRunner


def test_skills_install_copies_without_git_root(cli: CliRunner, tmp_path: Path) -> None:
    destination = tmp_path / "skills"

    result = cli.run("skills", "install", "--path", str(destination))

    assert result.code == 0
    assert result.payload["skills"] == ["doctidex-git"]
    assert result.payload["install-path"] == str(destination / "doctidex-git")
    assert (destination / "doctidex-git" / "SKILL.md").is_file()


def test_skills_install_missing_path_is_structured_error(cli: CliRunner) -> None:
    result = cli.run("skills", "install")

    assert result.code == 2
    assert result.payload["message"]["code"] == "argument.invalid"
    assert result.payload["message"]["context"]["command"] == "skills install"
    assert result.payload["message"]["details"]["parameter"] == "--path"


def test_skills_install_rejects_file_destination(cli: CliRunner, tmp_path: Path) -> None:
    destination = tmp_path / "destination"
    destination.write_text("not a directory")

    result = cli.run("skills", "install", "--path", str(destination))

    assert result.code == 2
    assert result.payload["message"]["code"] == "skills.install.target.unavailable"
