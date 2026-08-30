from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, read_json


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
