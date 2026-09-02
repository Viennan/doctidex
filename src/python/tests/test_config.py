from __future__ import annotations

from pathlib import Path

import pytest
from conftest import CliRunner, read_json

from whero.doctidex.config import Config
from whero.doctidex.errors import CommandFailure


def test_global_config_is_created_with_default_cache_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(home))

    config = Config.from_environment()

    assert (home / "config.toml").is_file()
    assert config.cache_path == home / "cache"
    assert config.options == {}


def test_relative_cache_path_resolves_against_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    (home / "config.toml").parent.mkdir(parents=True)
    (home / "config.toml").write_text("cache-path = 'custom'\n")
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(home))

    config = Config.from_environment()

    assert config.cache_path == home / "custom"


def test_absolute_cache_path_is_used_as_is(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    cache_path = tmp_path / "absolute-cache"
    (home / "config.toml").parent.mkdir(parents=True)
    (home / "config.toml").write_text(f"cache-path = {str(cache_path)!r}\n")
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(home))

    config = Config.from_environment()

    assert config.cache_path == cache_path


def test_repository_cache_path_overrides_global(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    git_root = tmp_path / "repository"
    repo_config = git_root / ".doctidex-git" / "config.toml"
    (home / "config.toml").parent.mkdir(parents=True)
    repo_config.parent.mkdir(parents=True)
    (home / "config.toml").write_text("cache-path = 'global-cache'\n")
    repo_config.write_text("cache-path = 'repo-cache'\n")
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(home))

    config = Config.from_environment(git_root)

    assert config.cache_path == git_root / ".doctidex-git" / "repo-cache"
    assert config.options["cache-path"] == "repo-cache"
    assert config.sources["cache-path"] == "repository"


def test_malformed_global_config_raises_config_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.toml").write_text("{not valid toml\n")
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(home))

    with pytest.raises(CommandFailure) as exc_info:
        Config.from_environment()

    assert exc_info.value.code == "config.invalid"


def test_invalid_cache_path_raises_config_invalid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.toml").write_text("cache-path = 3\n")
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(home))

    with pytest.raises(CommandFailure) as exc_info:
        Config.from_environment()

    assert exc_info.value.code == "config.invalid"


def test_first_cache_write_creates_home_config_and_cache_status(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
    )

    assert result.code == 0
    assert (cache_home / "config.toml").is_file()
    status = read_json(cache_home / "cache" / "cache-status.json")
    record = status["records"][0]
    assert record["status"] == "published"
    assert record["path"].startswith("data/")
    assert (cache_home / "cache" / record["path"]).is_dir()


def test_repository_cache_path_override_changes_git_root_cache(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    repository_config = initialized_root / ".doctidex-git" / "config.toml"
    repository_config.write_text("cache-path = 'repo-cache'\n")

    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
    )

    assert result.code == 0
    assert (initialized_root / ".doctidex-git" / "repo-cache" / "cache-status.json").is_file()
    assert not (cache_home / "cache" / "cache-status.json").exists()


def test_cache_command_reports_invalid_global_config(cache_home: Path, cli: CliRunner) -> None:
    cache_home.mkdir()
    (cache_home / "config.toml").write_text("{not valid toml\n")

    result = cli.run("cache", "compact")

    assert result.code == 2
    assert result.payload["message"]["code"] == "config.invalid"
