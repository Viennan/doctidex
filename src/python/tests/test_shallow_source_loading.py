from __future__ import annotations

from pathlib import Path

import pytest
from conftest import CliRunner, commit_file, git, git_head, read_json


def _cache_repository(cache_home: Path) -> Path:
    status = read_json(cache_home / "cache" / "status.json")
    record = status["records"][0]
    return cache_home / "cache" / record["path"]


def _selector_args_and_expected_commit(source_repository: Path, selector: str) -> tuple[tuple[str, str], str]:
    first_commit = git_head(source_repository)
    current_commit = commit_file(source_repository, "later.md", "later\n")

    if selector == "branch":
        return ("--branch", "main"), current_commit
    if selector == "tag":
        return ("--tag", "v1"), first_commit
    return ("--commit", first_commit), first_commit


@pytest.mark.parametrize(
    "selector",
    (
        "branch",
        "tag",
        "commit",
    ),
)
def test_import_install_from_file_url_uses_shallow_source_for_each_selector(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
    selector: str,
) -> None:
    selector_args, expected_commit = _selector_args_and_expected_commit(source_repository, selector)

    installed = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--tracked",
        "--url",
        source_repository.as_uri(),
        *selector_args,
    )

    assert installed.code == 0
    assert git_head(initialized_root / installed.payload["install-path"].lstrip("/")) == expected_commit
    repository = _cache_repository(cache_home)
    assert git(repository, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"


def test_import_restore_from_file_url_uses_recorded_commit(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    commit = git_head(source_repository)
    installed = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--tracked",
        "--url",
        source_repository.as_uri(),
        "--tag",
        "v1",
    )

    install_directory = initialized_root / installed.payload["install-path"].lstrip("/")
    backing_directory = install_directory.resolve()
    assert git(backing_directory, "worktree", "remove", "--force", str(backing_directory)).returncode == 0
    install_directory.unlink()
    assert not install_directory.exists()

    commit_file(source_repository, "other.md", "other\n")
    git(source_repository, "tag", "--force", "v1")
    restored = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "restore",
        "--install-id",
        installed.payload["install-id"],
    )

    assert restored.code == 0
    assert install_directory.is_dir()
    assert git_head(install_directory) == commit
    repository = _cache_repository(cache_home)
    assert git(repository, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"


@pytest.mark.parametrize(
    "selector",
    (
        "branch",
        "tag",
        "commit",
    ),
)
def test_worktree_create_from_file_url_uses_shallow_source_for_each_selector(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
    selector: str,
) -> None:
    selector_args, expected_commit = _selector_args_and_expected_commit(source_repository, selector)

    work_path = f"/work-{selector}"
    created = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        source_repository.as_uri(),
        *selector_args,
        "--work-path",
        work_path,
    )

    assert created.code == 0
    assert git_head(initialized_root / work_path.lstrip("/")) == expected_commit
    repository = _cache_repository(cache_home)
    assert git(repository, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"


def test_worktree_create_from_file_url_installation_can_commit_forward(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    base_commit = git_head(source_repository)
    installed = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--tracked",
        "--url",
        source_repository.as_uri(),
        "--branch",
        "main",
    )
    commit_file(source_repository, "later.md", "later\n")

    created = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--install-id",
        installed.payload["install-id"],
        "--work-path",
        "/forward",
    )

    assert created.code == 0
    target = initialized_root / created.payload["work-path"].lstrip("/")
    assert git_head(target) == base_commit

    assert git(target, "config", "user.email", "tests@example.test").returncode == 0
    assert git(target, "config", "user.name", "Tests").returncode == 0
    (target / "forward.md").write_text("forward\n")
    assert git(target, "add", "forward.md").returncode == 0
    assert git(target, "commit", "--quiet", "-m", "forward").returncode == 0
    assert git_head(target) != base_commit

    repository = _cache_repository(cache_home)
    assert git(repository, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"
