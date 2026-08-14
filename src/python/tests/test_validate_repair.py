from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

import whero.doctidex.coordination as coordination
import whero.doctidex.imports as import_workflow
import whero.doctidex.worktree as worktree_workflow
from whero.doctidex.cli.main import main
from whero.doctidex.coordination import StoreCoordinator
from whero.doctidex.git_cache import GitCache
from whero.doctidex.store.runtime import RuntimeStore


def test_validate_uninitialized_is_a_diagnostic_result(tmp_path: Path) -> None:
    root = _git_repository(tmp_path / "root")

    result = _run(root, "validate")

    assert result.code == 1
    assert result.payload["status"] == "ok"
    assert result.payload["valid"] is False
    assert result.payload["diagnostics"][0]["details"]["violations"][0]["code"] == "workspace.uninitialized"


def test_validate_valid_root_and_missing_link_include_scope_and_line(tmp_path: Path) -> None:
    root = _initialized_root(tmp_path)
    _write_root_index(root, "[missing](/missing.md)\n")

    result = _run(root, "validate")

    assert result.code == 1
    assert result.payload["scope"] == {"repos-path": str(root), "subdir": "/"}
    diagnostic = next(item for item in result.payload["diagnostics"] if item["rule"] == "link.target.exists")
    assert diagnostic["path"] == "/index.md"
    assert diagnostic["line"] == 7
    assert diagnostic["details"]["target-path"] == "/missing.md"


def test_validate_diagnostic_transaction_does_not_recover_or_create_journal(tmp_path: Path) -> None:
    root = _initialized_root(tmp_path)
    _write_root_index(root)
    store = RuntimeStore(root)
    transaction = store.write_transaction()
    transaction.__enter__()
    journal_directory = next(store.transactions_path.iterdir())
    store._lock.release()

    result = _run(root, "validate")

    assert result.code == 1
    assert result.payload["diagnostics"][0]["details"]["content-scan"] == "skipped"
    assert result.payload["diagnostics"][0]["details"]["violations"][0]["code"] == "transaction.recovery.required"
    assert journal_directory.exists()


def test_ordinary_command_repairs_recovered_transaction_before_running(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "cache-home"))
    root = _initialized_root(tmp_path)
    store = RuntimeStore(root)
    transaction = store.write_transaction()
    transaction.__enter__()
    journal_directory = next(store.transactions_path.iterdir())
    store._lock.release()

    result = _run(root, "boundary-set", "parse", "--path", "/docs")

    assert result.code == 0
    assert not journal_directory.exists()


def test_ordinary_command_reports_recovery_retry_exhaustion(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "cache-home"))
    root = _initialized_root(tmp_path)
    store = RuntimeStore(root)
    transaction = store.write_transaction()
    transaction.__enter__()
    journal_directory = next(store.transactions_path.iterdir())
    store._lock.release()
    monkeypatch.setattr(coordination, "repair_core", lambda _store, _transaction: None)

    result = _run(root, "boundary-set", "parse", "--path", "/docs")

    assert result.code == 2
    assert result.payload["message"]["code"] == "store.transaction.unavailable"
    assert result.payload["message"]["summary"].endswith("inspect the environment and retry.")
    assert result.payload["message"]["details"]["attempts"] == 3
    assert result.payload["message"]["details"]["transaction-ids"] == [journal_directory.name]
    assert journal_directory.exists()


def test_runtime_only_command_does_not_open_a_cache_transaction(tmp_path: Path, monkeypatch) -> None:
    root = _initialized_root(tmp_path)
    cache = GitCache(tmp_path / "cache")
    calls: list[str] = []
    monkeypatch.setattr(GitCache, "from_environment", classmethod(lambda _cls: cache))
    monkeypatch.setattr(cache, "read_only_transaction", lambda: _unexpected_cache_access(calls, "read"))
    monkeypatch.setattr(cache, "write_transaction", lambda: _unexpected_cache_access(calls, "write"))

    result = _run(root, "boundary-set", "parse", "--path", "/docs")

    assert result.code == 0
    assert calls == []


def test_cache_write_transaction_is_reused_for_repair_after_a_cache_miss(tmp_path: Path, monkeypatch) -> None:
    root, source = _source_and_root(tmp_path)
    store = RuntimeStore(root)
    _leave_residual_transaction(store)
    cache = GitCache(tmp_path / "cache")
    events: list[str] = []
    _record_cache_transactions(cache, events, monkeypatch)

    with StoreCoordinator(store, cache) as coordinator:
        result = coordinator.with_repository(
            str(source),
            lambda _repository: _runtime_marker(store),
        )

    assert result == "ready"
    assert events == ["read:enter", "read:exit", "write:enter", "write:exit"]


def test_cache_read_only_transaction_exits_before_write_repair(tmp_path: Path, monkeypatch) -> None:
    root, source = _source_and_root(tmp_path)
    store = RuntimeStore(root)
    cache = GitCache(tmp_path / "cache")
    with cache.write_transaction() as transaction:
        transaction.load(str(source))
    _leave_residual_transaction(store)
    events: list[str] = []
    _record_cache_transactions(cache, events, monkeypatch)

    with StoreCoordinator(store, cache) as coordinator:
        result = coordinator.with_repository(
            str(source),
            lambda _repository: _runtime_marker(store),
        )

    assert result == "ready"
    assert events == ["read:enter", "read:exit", "write:enter", "write:exit"]


def test_import_retry_reuses_the_resolved_revision(tmp_path: Path, monkeypatch) -> None:
    root, source = _source_and_root(tmp_path)
    store = RuntimeStore(root)
    _leave_residual_transaction(store)
    resolved: list[str] = []
    original = import_workflow._resolve_revision

    def resolve(*args, **kwargs):
        value = original(*args, **kwargs)
        resolved.append(value)
        return value

    monkeypatch.setattr(import_workflow, "_resolve_revision", resolve)

    result = _run(root, "import", "install", "--untracked", "--url", str(source), "--branch", "main")

    assert result.code == 0
    assert len(resolved) == 1


def test_worktree_retry_reuses_the_resolved_revision(tmp_path: Path, monkeypatch) -> None:
    root, source = _source_and_root(tmp_path)
    store = RuntimeStore(root)
    _leave_residual_transaction(store)
    resolved: list[str] = []
    original = worktree_workflow._resolve_revision

    def resolve(*args, **kwargs):
        value = original(*args, **kwargs)
        resolved.append(value)
        return value

    monkeypatch.setattr(worktree_workflow, "_resolve_revision", resolve)

    result = _run(root, "worktree", "create", "--url", str(source), "--branch", "main")

    assert result.code == 0
    assert len(resolved) == 1


def test_validate_rejects_subdir_inside_boundary(tmp_path: Path) -> None:
    root = _initialized_root(tmp_path)
    _write_root_index(root)
    _run(root, "boundary-set", "add", "--path", "/external")
    (root / "external" / "docs").mkdir(parents=True)

    result = _run(root, "validate", "--subdir", "/external/docs")

    assert result.code == 2
    assert result.payload["message"]["code"] == "validation.scope.unavailable"
    assert result.payload["message"]["details"]["reason"] == "outside-current-tree"


def test_repair_recreates_missing_ref_and_removes_unregistered_install_link(tmp_path: Path) -> None:
    root, source = _source_and_root(tmp_path)
    _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    installation = RuntimeStore(root).read_state().installations[0]
    _run(root, "import", "ref", "--install-id", installation.install_id, "--target-dir", "/linked")
    (root / "linked").unlink()
    (root / "orphan").symlink_to(root / installation.install_path.lstrip("/"))

    assert _run(root, "repair").code == 0
    assert (root / "linked").is_symlink()
    assert not (root / "orphan").exists()
    assert _run(root, "repair").code == 0


def test_repair_recreates_a_dangling_ref_when_tracked_install_is_missing(tmp_path: Path) -> None:
    root, source = _source_and_root(tmp_path)
    _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    installation = RuntimeStore(root).read_state().installations[0]
    _run(root, "import", "ref", "--install-id", installation.install_id, "--target-dir", "/linked")
    shutil.rmtree(root / installation.install_path.lstrip("/"))
    (root / "linked").unlink()

    assert _run(root, "repair").code == 0
    assert (root / "linked").is_symlink()
    assert (root / "linked").resolve(strict=False) == (
        root / installation.install_path.lstrip("/")
    ).resolve(strict=False)


def test_repair_removes_stale_tool_worktree_ignore_pairs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "cache-home"))
    root = _initialized_root(tmp_path)
    (root / ".gitignore").write_text(
        (root / ".gitignore").read_text() + "# doctidex-git worktree: /old-work\n/old-work/\n"
    )

    assert _run(root, "repair").code == 0
    assert "# doctidex-git worktree: /old-work" not in (root / ".gitignore").read_text()


def test_repair_recreates_missing_worktree(tmp_path: Path) -> None:
    root, source = _source_and_root(tmp_path)
    created = _run(root, "worktree", "create", "--url", str(source), "--branch", "main")
    work_path = created.payload["work-path"]
    shutil.rmtree(root / str(work_path).lstrip("/"))

    assert _run(root, "repair").code == 0
    assert (root / str(work_path).lstrip("/")).is_dir()
    assert _run(root, "validate").payload["valid"] is True


def _initialized_root(tmp_path: Path) -> Path:
    root = _git_repository(tmp_path / "repository")
    assert _run(root, "init").code == 0
    return root


def _source_and_root(tmp_path: Path) -> tuple[Path, Path]:
    root = _initialized_root(tmp_path)
    source = _git_repository(tmp_path / "source")
    (source / "readme.md").write_text("source\n")
    subprocess.run(["git", "-C", str(source), "add", "readme.md"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(source),
            "-c",
            "user.email=test@example.test",
            "-c",
            "user.name=Tests",
            "commit",
            "-qm",
            "source",
        ],
        check=True,
    )
    os.environ["DOCTIDEX-GIT-HOME"] = str(tmp_path / "cache-home")
    _write_root_index(root)
    return root, source


def _write_root_index(root: Path, body: str = "") -> None:
    (root / "index.md").write_text("---\ntype: index\ndoctidex:\n  type: index\n  root: true\n---\n" + body)


def _leave_residual_transaction(store: RuntimeStore) -> None:
    transaction = store.write_transaction()
    transaction.__enter__()
    store._lock.release()


def _runtime_marker(store: RuntimeStore) -> str:
    with store.read_only_transaction():
        return "ready"


def _record_cache_transactions(cache: GitCache, events: list[str], monkeypatch) -> None:
    for name, label in (("read_only_transaction", "read"), ("write_transaction", "write")):
        original = getattr(cache, name)

        @contextmanager
        def recorded(original: Callable = original, label: str = label):
            events.append(f"{label}:enter")
            try:
                with original() as transaction:
                    yield transaction
            finally:
                events.append(f"{label}:exit")

        monkeypatch.setattr(cache, name, recorded)


@contextmanager
def _unexpected_cache_access(calls: list[str], kind: str):
    calls.append(kind)
    raise AssertionError(f"unexpected {kind} cache transaction")
    yield


def _git_repository(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet", "--initial-branch", "main", str(path)], check=True)
    return path


class _Result:
    def __init__(self, code: int, payload: dict[str, object]) -> None:
        self.code = code
        self.payload = payload


def _run(root: Path, *arguments: str) -> _Result:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(["--repos-path", str(root), *arguments])
    return _Result(code, json.loads(output.getvalue()))
