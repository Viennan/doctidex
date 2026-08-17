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
from whero.doctidex.model import InlineAnnotation, Ref, RuntimeState
from whero.doctidex.model_view import parse_inline_annotation, resolve_inline_annotation_boundary
from whero.doctidex.store.runtime import RuntimeStore


def test_validate_uninitialized_is_a_diagnostic_result(tmp_path: Path) -> None:
    root = _git_repository(tmp_path / "root")

    result = _run(root, "validate")

    assert result.code == 1
    assert result.payload["status"] == "ok"
    assert result.payload["valid"] is False
    assert result.payload["diagnostics"][0]["details"]["violations"][0]["code"] == "workspace.uninitialized"


def test_validate_model_structure_skips_directory_tree_checks(tmp_path: Path) -> None:
    root = _initialized_root(tmp_path)
    _write_root_index(root, "[missing](/missing.md)\n")

    structure = _run(root, "validate", "--model-structure")
    complete = _run(root, "validate")

    assert structure.code == 0
    assert structure.payload["valid"] is True
    assert structure.payload["scope"] == {"repos-path": str(root), "subdir": "/"}
    assert complete.code == 1
    assert any(item["rule"] == "link.target.exists" for item in complete.payload["diagnostics"])


def test_validate_model_structure_checks_root_index_frontmatter(tmp_path: Path) -> None:
    root = _initialized_root(tmp_path)
    (root / "index.md").write_text("---\ntype: guide\n---\n")

    result = _run(root, "validate", "--model-structure")

    assert result.code == 1
    assert any(item["rule"] == "index.conforms" for item in result.payload["diagnostics"])


def test_validate_model_structure_reports_an_absent_root_index_with_an_uninitialized_workspace(tmp_path: Path) -> None:
    root = _git_repository(tmp_path / "root")

    result = _run(root, "validate", "--model-structure")

    assert result.code == 1
    assert {item["rule"] for item in result.payload["diagnostics"]} == {"work-model.valid", "index.conforms"}


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


def test_validate_extracts_each_link_annotation_from_its_own_comment_sequence(tmp_path: Path) -> None:
    root = _initialized_root(tmp_path)
    (root / "first").mkdir()
    (root / "second").mkdir()
    _run(root, "boundary-set", "add", "--path", "/first", "--path", "/second")
    _write_root_index(
        root,
        "[first](/first) <!-- another comment --><!--\n"
        "  doctidex:\n"
        "    cross-boundary-point: /first\n"
        "--> [second](/second) <!-- doctidex: {cross-boundary-point: /second} -->\n",
    )

    result = _run(root, "validate")

    assert result.code == 0
    assert result.payload["valid"] is True


def test_validate_does_not_share_an_annotation_between_identical_links_on_one_line(tmp_path: Path) -> None:
    root = _initialized_root(tmp_path)
    (root / "external").mkdir()
    _run(root, "boundary-set", "add", "--path", "/external")
    _write_root_index(
        root,
        "[same](/external) [same](/external) "
        "<!-- doctidex: {cross-boundary-point: /external} -->\n",
    )

    result = _run(root, "validate")

    annotations = [item for item in result.payload["diagnostics"] if item["rule"] == "link.annotation.required"]
    assert result.code == 1
    assert len(annotations) == 1


def test_parse_inline_annotation_returns_the_first_valid_annotation_after_position() -> None:
    content = (
        "[external](/external) <!-- another comment --> <!-- doctidex: not-a-mapping -->"
        "<!-- doctidex: {cross-boundary-point: /external} -->"
    )
    position = content.index(")") + 1

    assert parse_inline_annotation(content, position) == InlineAnnotation(cross_boundary_point="/external")


def test_inline_annotation_must_be_a_link_path_prefix_before_normalization() -> None:
    relative_annotation = InlineAnnotation(cross_boundary_point="../external")
    absolute_annotation = InlineAnnotation(cross_boundary_point="/external")

    assert (
        resolve_inline_annotation_boundary("/guides/intro.md", "../external/readme.md", relative_annotation)
        == "/external"
    )
    assert resolve_inline_annotation_boundary("/guides/intro.md", "../external/readme.md", absolute_annotation) is None


def test_validate_accepts_relative_cross_boundary_annotation(tmp_path: Path) -> None:
    root = _initialized_root(tmp_path)
    _write_root_index(root)
    (root / "external").mkdir()
    (root / "external" / "readme.md").write_text("external\n")
    (root / "guides").mkdir()
    _run(root, "boundary-set", "add", "--path", "/external")
    (root / "guides" / "intro.md").write_text(
        "[external](../external/readme.md) <!-- doctidex: {cross-boundary-point: ../external} -->\n"
    )

    result = _run(root, "validate")

    assert result.code == 0
    assert result.payload["valid"] is True


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


def test_repair_removes_a_ref_without_an_installation_without_scanning_links(tmp_path: Path) -> None:
    root = _initialized_root(tmp_path)
    _write_root_index(root, "[obsolete](/obsolete)\n")
    store = RuntimeStore(root)
    with store.write_transaction() as transaction:
        transaction.replace_state(
            RuntimeState(
                custom_boundary_points=(),
                installations=(),
                refs=(Ref(install_id="missing", src_sub_dir="", target_dir="/obsolete"),),
                worktrees=(),
            )
        )
    (root / "obsolete").write_text("obsolete target\n")

    assert _run(root, "repair").code == 0
    assert not (root / "obsolete").exists()
    assert RuntimeStore(root).read_state().refs == ()


def test_repair_rebuilds_an_inconsistent_ref_target(tmp_path: Path) -> None:
    root, source = _source_and_root(tmp_path)
    _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    installation = RuntimeStore(root).read_state().installations[0]
    _run(root, "import", "ref", "--install-id", installation.install_id, "--target-dir", "/linked")
    target = root / "linked"
    target.unlink()
    target.mkdir()
    (target / "old-content").write_text("replace me\n")

    assert _run(root, "repair").code == 0
    assert target.is_symlink()
    assert target.resolve(strict=False) == (root / installation.install_path.lstrip("/")).resolve(strict=False)


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
