from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

from whero.doctidex import imports as import_workflow
from whero.doctidex import worktree as worktree_workflow
from whero.doctidex.cli.main import main
from whero.doctidex.coordination import StoreCoordinator
from whero.doctidex.git_cache import GitCache
from whero.doctidex.model import BoundaryPoint, Installation, RuntimeState
from whero.doctidex.model_view import RuntimeModelView, scan_markdown_links
from whero.doctidex.store.runtime import RuntimeStore


def test_boundary_set_add_parse_remove_and_derived_import_point(tmp_path: Path, monkeypatch) -> None:
    root, source, commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")

    _run(root, "boundary-set", "add", "--path", "/docs/../guides")
    parsed = _run(root, "boundary-set", "parse", "--path", "/guides/topic.md")
    assert parsed["results"] == [
        {
            "path": "/guides/topic.md",
            "has-boundary": True,
            "boundary-point": "/guides",
            "boundary-type": "custom",
        }
    ]

    installed = _run(
        root,
        "import",
        "install",
        "--untracked",
        "--url",
        str(source),
        "--branch",
        "main",
        "--key",
        "guide",
    )
    install_path = installed["install-path"]
    assert (root / install_path.lstrip("/") / "readme.md").is_file()
    assert (
        subprocess.run(
            ["git", "-C", str(root / install_path.lstrip("/")), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == commit
    )

    parsed = _run(root, "boundary-set", "parse", "--path", f"{install_path}/readme.md")
    assert parsed["results"][0]["boundary-type"] == "import"
    assert parsed["results"][0]["boundary-point"] == install_path

    _run(root, "boundary-set", "remove", "--path", "/guides", "--path", "/guides")
    assert _run(root, "boundary-set", "parse", "--path", "/guides/topic.md")["results"] == [
        {"path": "/guides/topic.md", "has-boundary": False}
    ]
    assert _run(root, "boundary-set", "remove", "--path", "/not-recorded") == {
        "status": "ok",
        "message": {},
    }
    derived = _run_error(root, "boundary-set", "remove", "--path", install_path)
    assert derived["message"]["code"] == "boundary-point.remove.prohibited"


def test_boundary_queries_and_link_scanning_use_a_batch_snapshot(tmp_path: Path, monkeypatch) -> None:
    root, _, _ = _repositories(tmp_path)
    _run(root, "init")
    store = RuntimeStore(root)
    with store.write_transaction() as transaction:
        transaction.replace_state(
            RuntimeState(
                custom_boundary_points=(
                    BoundaryPoint(type="custom", path="/first"),
                    BoundaryPoint(type="custom", path="/first/nested"),
                    BoundaryPoint(type="custom", path="/second"),
                ),
                installations=(),
                refs=(),
                worktrees=(),
            )
        )

    with store.read_only_transaction() as transaction:
        view = RuntimeModelView(transaction)
        assert [
            point.path if point is not None else None
            for point in view.first_boundaries(("/second/file.md", "/first/nested/file.md", "/none/file.md"))
        ] == ["/second", "/first", None]

        calls: list[tuple[str, ...]] = []
        original = view.first_boundaries

        def recorded(paths):
            materialized = tuple(paths)
            calls.append(materialized)
            return original(materialized)

        monkeypatch.setattr(view, "first_boundaries", recorded)
        (root / "index.md").write_text("[one](/first/a.md)\n[two](/second/b.md)\n")
        links = scan_markdown_links(root, view)

    assert calls == [("/first/a.md", "/second/b.md")]
    assert [link.boundary_point.path for link in links if link.boundary_point is not None] == ["/first", "/second"]


def test_import_track_ref_query_unref_and_remove(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(
        root, "import", "install", "--untracked", "--url", str(source), "--branch", "main", "--key", "topic"
    )

    tracked = _run(root, "import", "track", "--install-id", installed["install-id"])
    assert tracked == {
        "status": "ok",
        "message": {},
        "install-id": installed["install-id"],
        "install-path": installed["install-path"],
    }
    _run(root, "import", "ref", "--install-id", installed["install-id"], "--target-dir", "/linked")
    assert (root / "linked").is_symlink()
    assert os.readlink(root / "linked") == os.path.relpath(root / installed["install-path"].lstrip("/"), root)

    candidates = _run(root, "import", "query", "--key", "topic")["candidates"]
    assert candidates[0]["install-id"] == installed["install-id"]
    assert candidates[0]["refs"] == [{"src-sub-dir": "", "target-dir": "/linked"}]
    assert candidates[0]["import-by-installations"] == []

    blocked = _run_error(root, "import", "remove", "--install-id", installed["install-id"])
    assert blocked["message"]["code"] == "installation.remove.blocked"
    assert blocked["message"]["details"]["blocked-installations"][0]["blocking-ref-target-dirs"] == ["/linked"]
    with RuntimeStore(root).read_only_transaction() as transaction:
        assert [item.target_dir for item in transaction.state.refs] == ["/linked"]

    _run(root, "import", "unref", "--target-dir", "/linked")
    _run(root, "import", "unref", "--target-dir", "/linked")
    _run(root, "import", "remove", "--install-id", installed["install-id"])
    assert _run(root, "import", "remove", "--install-id", installed["install-id"]) == {
        "status": "ok",
        "message": {},
    }
    with RuntimeStore(root).read_only_transaction() as transaction:
        assert transaction.state.installations == ()
        assert transaction.state.refs == ()


def test_import_query_fuzzy_keys_rank_match_count_then_exact_matches(tmp_path: Path) -> None:
    root, _, _ = _repositories(tmp_path)
    _run(root, "init")
    store = RuntimeStore(root)
    installations = (
        _query_installation("partial", ("guide-intro", "reference")),
        _query_installation("exact", ("guide", "reference")),
        _query_installation("many", ("guide", "guide-api", "other")),
    )
    with store.write_transaction() as transaction:
        transaction.replace_state(
            RuntimeState(
                custom_boundary_points=(),
                installations=installations,
                refs=(),
                worktrees=(),
            )
        )

    with store.read_only_transaction() as transaction:
        candidates = import_workflow.query(
            RuntimeModelView(transaction),
            install_id=None,
            install_path=None,
            ref_path=None,
            keys=["guide"],
        )

    assert [item["install-id"] for item in candidates] == ["many", "exact", "partial"]
    assert [item["import-by-installations"] for item in candidates] == [[], [], []]


def test_installation_context_rejects_forbidden_commands_before_writing(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--untracked", "--url", str(source), "--branch", "main")
    installation_root = root / installed["install-path"].lstrip("/")

    forbidden_init = _run_error(installation_root, "init")
    assert forbidden_init["message"]["code"] == "installation.context.forbidden"
    assert forbidden_init["message"]["subject"] == {
        "kind": "installation",
        "install-path": installed["install-path"],
    }
    assert not (installation_root / ".doctidex-git").exists()

    forbidden_worktree = _run_error(
        installation_root,
        "worktree",
        "create",
        "--url",
        str(source),
        "--branch",
        "main",
    )
    assert forbidden_worktree["message"]["code"] == "installation.context.forbidden"


def test_installation_context_defers_restore_and_query_to_phase_3(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--untracked", "--url", str(source), "--branch", "main")
    installation_root = root / installed["install-path"].lstrip("/")

    deferred_query = _run_error(installation_root, "import", "query", "--key", "topic")
    assert deferred_query["message"]["code"] == "installation.context.unavailable"
    assert deferred_query["message"]["details"]["next-phase"] == "3"

    deferred_restore = _run_error(installation_root, "import", "restore", "--install-id", "anything")
    assert deferred_restore["message"]["code"] == "installation.context.unavailable"


def test_installation_context_allows_validate_on_installation_itself(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--untracked", "--url", str(source), "--branch", "main")
    installation_root = root / installed["install-path"].lstrip("/")

    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(["--repos-path", str(installation_root), "validate", "--model-structure"])

    assert code == 1
    payload = json.loads(output.getvalue())
    assert payload["status"] == "ok"
    assert payload["valid"] is False
    assert payload["message"] == {}


def test_import_remove_is_blocked_by_link_outside_boundary(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    (root / "index.md").write_text(f"[external]({installed['install-path']}/readme.md)\n")

    blocked = _run_error(root, "import", "remove", "--install-id", installed["install-id"])
    links = blocked["message"]["details"]["blocked-installations"][0]["blocking-links"]
    assert links == [{"path": "/index.md", "line": 1, "link-path": f"{installed['install-path']}/readme.md"}]


def test_import_remove_recognizes_commonmark_inline_and_reference_links(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    _run(root, "import", "ref", "--install-id", installed["install-id"], "--target-dir", "/linked")
    (root / "index.md").write_text(
        "intro\n[inline](/linked/path(a).md \"title\")\n\n[reference][guide]\n\n[guide]: /linked/referenced.md\n"
    )

    blocked = _run_error(root, "import", "remove", "--install-id", installed["install-id"])
    assert blocked["message"]["details"]["blocked-installations"][0]["blocking-links"] == [
        {"path": "/index.md", "line": 2, "link-path": "/linked/path(a).md"},
        {"path": "/index.md", "line": 4, "link-path": "/linked/referenced.md"},
    ]


def test_import_ref_links_block_unref_and_installation_removal(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    _run(root, "import", "ref", "--install-id", installed["install-id"], "--target-dir", "/linked")
    (root / "index.md").write_text("[linked](/linked/readme.md)\n")

    blocked_installation = _run_error(root, "import", "remove", "--install-id", installed["install-id"])
    installation_details = blocked_installation["message"]["details"]["blocked-installations"][0]
    assert installation_details["blocking-links"] == [
        {"path": "/index.md", "line": 1, "link-path": "/linked/readme.md"}
    ]
    assert installation_details["blocking-ref-target-dirs"] == ["/linked"]

    blocked_ref = _run_error(root, "import", "unref", "--target-dir", "/linked")
    assert blocked_ref["message"]["code"] == "ref.remove.blocked"
    assert blocked_ref["message"]["subject"] == {"kind": "ref", "target-dir": "/linked"}
    assert blocked_ref["message"]["details"] == {
        "blocking-links": [{"path": "/index.md", "line": 1, "link-path": "/linked/readme.md"}]
    }

    (root / "index.md").write_text("")
    _run(root, "import", "unref", "--target-dir", "/linked")
    _run(root, "import", "remove", "--install-id", installed["install-id"])


def test_import_ref_links_below_another_boundary_do_not_block_unref(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    _run(root, "import", "ref", "--install-id", installed["install-id"], "--target-dir", "/linked")
    _run(root, "boundary-set", "add", "--path", "/excluded")
    assert _run(root, "boundary-set", "parse", "--path", "/excluded/index.md")["results"] == [
        {
            "path": "/excluded/index.md",
            "has-boundary": True,
            "boundary-point": "/excluded",
            "boundary-type": "custom",
        }
    ]
    (root / "excluded").mkdir()
    (root / "excluded" / "index.md").write_text("[linked](/linked/readme.md)\n")

    _run(root, "import", "unref", "--target-dir", "/linked")


def test_import_restore_uses_the_recorded_commit(tmp_path: Path, monkeypatch) -> None:
    root, source, commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--tag", "v1")
    install_directory = root / installed["install-path"].lstrip("/")
    subprocess.run(
        ["git", "-C", str(install_directory), "worktree", "remove", "--force", str(install_directory)],
        check=True,
        capture_output=True,
    )
    assert not install_directory.exists()
    _commit(source, "other.md", "other\n")
    subprocess.run(["git", "-C", str(source), "tag", "--force", "v1"], check=True)
    _run(root, "import", "restore", "--install-id", installed["install-id"])
    assert install_directory.is_dir()
    assert _head(install_directory) == commit


def test_import_restore_reuses_a_clean_detached_install_path(tmp_path: Path, monkeypatch) -> None:
    root, source, commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    install_directory = root / installed["install-path"].lstrip("/")

    newer_commit = _commit(source, "newer.md", "newer\n")
    subprocess.run(["git", "-C", str(install_directory), "fetch", "origin", "main"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(install_directory), "checkout", "--quiet", "--detach", newer_commit], check=True
    )

    def unexpected_create(*args, **kwargs) -> None:
        raise AssertionError("a clean detached install-path must be reused")

    monkeypatch.setattr(import_workflow, "_create_worktree", unexpected_create)
    restored = _run(root, "import", "restore", "--install-id", installed["install-id"])

    assert restored == installed
    assert _head(install_directory) == commit


def test_import_restore_fetches_a_recorded_commit_missing_from_cache(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    install_directory = root / installed["install-path"].lstrip("/")
    subprocess.run(
        ["git", "-C", str(install_directory), "worktree", "remove", "--force", str(install_directory)],
        check=True,
        capture_output=True,
    )
    next_commit = _commit(source, "next.md", "next\n")
    _set_installation_commit(root, installed["install-id"], next_commit)

    _run(root, "import", "restore", "--install-id", installed["install-id"])

    assert _head(install_directory) == next_commit
    assert _cache_contains_commit(GitCache.from_environment(), str(source), next_commit)


def test_import_restore_reports_an_unavailable_recorded_commit(tmp_path: Path, monkeypatch) -> None:
    root, source, original_commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    install_directory = root / installed["install-path"].lstrip("/")
    next_commit = _commit(source, "next.md", "next\n")
    _set_installation_commit(root, installed["install-id"], next_commit)
    source.rename(tmp_path / "source-unavailable")

    failure = _run_error(root, "import", "restore", "--install-id", installed["install-id"])

    assert failure["message"]["code"] == "installation.restore.unavailable"
    assert failure["message"]["details"] == {"commit-hash": next_commit}
    assert _head(install_directory) == original_commit


def test_import_install_rebuilds_a_non_git_install_path(tmp_path: Path, monkeypatch) -> None:
    root, source, commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    install_path = import_workflow._install_path(str(source), "main")
    install_directory = root / install_path.lstrip("/")
    install_directory.mkdir(parents=True)
    (install_directory / "incomplete.txt").write_text("incomplete\n")

    installed = _run(root, "import", "install", "--untracked", "--url", str(source), "--branch", "main")

    assert installed["install-path"] == install_path
    assert _head(install_directory) == commit
    assert not (install_directory / "incomplete.txt").exists()


def test_import_install_reuses_a_clean_detached_same_source_worktree(tmp_path: Path, monkeypatch) -> None:
    root, source, commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    install_path = import_workflow._install_path(str(source), "main")
    install_directory = root / install_path.lstrip("/")
    install_directory.parent.mkdir(parents=True)
    subprocess.run(["git", "clone", "--quiet", str(source), str(install_directory)], check=True)
    subprocess.run(
        ["git", "-C", str(install_directory), "checkout", "--quiet", "--detach", commit], check=True
    )

    installed = _run(root, "import", "install", "--untracked", "--url", str(source), "--branch", "main")

    assert installed["install-path"] == install_path
    assert _head(install_directory) == commit
    assert (install_directory / ".git").is_dir()


def test_import_install_rebuilds_a_dirty_same_source_worktree(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    install_directory = root / installed["install-path"].lstrip("/")
    (install_directory / "readme.md").write_text("local edit\n")

    repeated = _run(root, "import", "install", "--untracked", "--url", str(source), "--branch", "main")

    assert repeated == installed
    assert (install_directory / "readme.md").read_text() == "source\n"
    assert subprocess.run(
        ["git", "-C", str(install_directory), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout == ""


def test_import_install_preserves_a_different_source_worktree(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    install_path = import_workflow._install_path(str(source), "main")
    install_directory = root / install_path.lstrip("/")
    install_directory.parent.mkdir(parents=True)
    subprocess.run(["git", "clone", "--quiet", str(source), str(install_directory)], check=True)
    subprocess.run(
        ["git", "-C", str(install_directory), "remote", "set-url", "origin", "https://example.test/other.git"],
        check=True,
    )

    failure = _run_error(root, "import", "install", "--untracked", "--url", str(source), "--branch", "main")

    assert failure["message"]["code"] == "installation.target.unavailable"
    assert failure["message"]["details"] == {"operation": "install", "occupant": "different-git-url"}
    assert subprocess.run(
        ["git", "-C", str(install_directory), "remote", "get-url", "origin"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == "https://example.test/other.git"


def test_import_restore_rejects_a_different_source_worktree(tmp_path: Path, monkeypatch) -> None:
    root, source, commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    install_directory = root / installed["install-path"].lstrip("/")
    subprocess.run(
        ["git", "-C", str(install_directory), "worktree", "remove", "--force", str(install_directory)],
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "clone", "--quiet", str(source), str(install_directory)], check=True)
    subprocess.run(
        ["git", "-C", str(install_directory), "remote", "set-url", "origin", "https://example.test/other.git"],
        check=True,
    )

    failure = _run_error(root, "import", "restore", "--install-id", installed["install-id"])

    assert failure["message"]["code"] == "installation.restore.unavailable"
    assert failure["message"]["details"] == {"commit-hash": commit}
    assert install_directory.is_dir()


def test_import_branch_install_reuses_current_revision_then_replaces_on_update(tmp_path: Path, monkeypatch) -> None:
    root, source, first_commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")

    initial = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    repeated = _run(root, "import", "install", "--untracked", "--url", str(source), "--branch", "main")
    assert repeated == initial
    assert initial["install-path"] == f"/.doctidex-git/imports/local/{source.as_posix().lstrip('/')}/main"
    with RuntimeStore(root).read_only_transaction() as transaction:
        assert transaction.state.installations[0].tracked is True

    current_commit = _commit(source, "next.md", "next\n")
    updated = _run(root, "import", "install", "--untracked", "--url", str(source), "--branch", "main")
    assert updated["install-path"] == initial["install-path"]
    assert updated["install-id"] != initial["install-id"]
    assert _head(root / updated["install-path"].lstrip("/")) == current_commit
    with RuntimeStore(root).read_only_transaction() as transaction:
        assert [item.install_id for item in transaction.state.installations] == [updated["install-id"]]
        assert transaction.state.installations[0].commit_hash == current_commit
    assert transaction.state.installations[0].commit_hash != first_commit


def test_import_path_preserves_branch_path_components(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    subprocess.run(["git", "-C", str(source), "branch", "feature/one"], check=True)

    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "feature/one")

    assert installed["install-path"].endswith("/feature/one")


def test_import_path_uses_git_url_domain_repository_and_selector() -> None:
    assert import_workflow._install_path("git@github.com:Viennan/doctidex.git", "feature/one") == (
        "/.doctidex-git/imports/github.com/Viennan/doctidex/feature/one"
    )


def test_import_revision_replacement_retains_managed_ref_relationship(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    initial = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    _run(root, "import", "ref", "--install-id", initial["install-id"], "--target-dir", "/linked")

    _commit(source, "next.md", "next\n")
    updated = _run(root, "import", "install", "--untracked", "--url", str(source), "--branch", "main")

    with RuntimeStore(root).read_only_transaction() as transaction:
        installation = transaction.state.installations[0]
        assert installation.install_id == updated["install-id"]
        assert installation.tracked is True
        assert transaction.state.refs[0].install_id == updated["install-id"]


def test_import_tag_install_reuses_current_revision_then_replaces_on_update(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")

    initial = _run(root, "import", "install", "--tracked", "--url", str(source), "--tag", "v1")
    assert _run(root, "import", "install", "--untracked", "--url", str(source), "--tag", "v1") == initial

    updated_commit = _commit(source, "next.md", "next\n")
    subprocess.run(["git", "-C", str(source), "tag", "--force", "v1"], check=True)
    updated = _run(root, "import", "install", "--untracked", "--url", str(source), "--tag", "v1")
    assert updated["install-path"] == initial["install-path"]
    assert updated["install-id"] != initial["install-id"]
    assert _head(root / updated["install-path"].lstrip("/")) == updated_commit


def test_import_commit_install_reuses_same_source_and_commit(tmp_path: Path, monkeypatch) -> None:
    root, source, commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")

    initial = _run(root, "import", "install", "--tracked", "--url", str(source), "--commit", commit)
    repeated = _run(root, "import", "install", "--untracked", "--url", str(source), "--commit", commit)

    assert repeated == initial
    assert initial["install-path"].endswith(f"/{commit}")


def test_import_cache_transaction_covers_revision_and_worktree_operations(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    _run(root, "init")
    store = RuntimeStore(root)
    cache = GitCache(tmp_path / "cache")
    cache_activity: list[str] = []
    runtime_active = False
    events: list[str] = []
    expected_cache_transaction = "write"

    _record_cache_transactions(cache, cache_activity, events, monkeypatch)
    original_write_transaction = store.write_transaction

    def write_transaction():
        @contextlib.contextmanager
        def recorded():
            nonlocal runtime_active
            assert cache_activity == [expected_cache_transaction]
            events.append("runtime:open")
            with original_write_transaction() as transaction:
                runtime_active = True
                try:
                    yield transaction
                finally:
                    runtime_active = False
            events.append("runtime:close")

        return recorded()

    monkeypatch.setattr(store, "write_transaction", write_transaction)
    original_resolve_revision = import_workflow._resolve_revision
    original_create_worktree = import_workflow._create_worktree

    def resolve_revision(*args, **kwargs):
        assert cache_activity == [expected_cache_transaction]
        assert not runtime_active
        return original_resolve_revision(*args, **kwargs)

    def create_worktree(*args, **kwargs):
        assert cache_activity == [expected_cache_transaction]
        assert runtime_active
        return original_create_worktree(*args, **kwargs)

    monkeypatch.setattr(import_workflow, "_resolve_revision", resolve_revision)
    monkeypatch.setattr(import_workflow, "_create_worktree", create_worktree)

    with StoreCoordinator(store, cache) as coordinator:
        installation = import_workflow.install(
            store,
            coordinator,
            tracked=True,
            git_url=str(source),
            branch="main",
            tag="",
            commit="",
            keys=[],
        )
    assert events == [
        "cache:read-only:open",
        "cache:read-only:close",
        "cache:write:open",
        "runtime:open",
        "runtime:close",
        "cache:write:close",
    ]

    install_directory = root / installation.install_path.lstrip("/")
    subprocess.run(
        ["git", "-C", str(install_directory), "worktree", "remove", "--force", str(install_directory)],
        check=True,
        capture_output=True,
    )
    events.clear()
    expected_cache_transaction = "read-only"

    with StoreCoordinator(store, cache) as coordinator:
        restored = import_workflow.restore(store, coordinator, installation.install_id)
    assert restored == installation
    assert events == [
        "cache:read-only:open",
        "runtime:open",
        "runtime:close",
        "cache:read-only:close",
    ]


def test_worktree_create_from_url_manages_custom_path_ignore_and_boundary(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    (root / ".gitignore").write_text("/kept/\n/projects/source/\n")

    created = _run(
        root,
        "worktree",
        "create",
        "--url",
        str(source),
        "--branch",
        "main",
        "--work-path",
        "/projects/source",
    )

    assert created == {"status": "ok", "message": {}, "work-path": "/projects/source"}
    target = root / "projects/source"
    assert target.is_dir()
    assert _head(target) == _head(source)
    with RuntimeStore(root).read_only_transaction() as transaction:
        assert transaction.state.worktrees[0].base_commit_hash == _head(source)
    assert _run(root, "worktree", "query", "--work-path", "/projects/source") == {"status": "ok", "message": {}}
    assert _run(root, "boundary-set", "parse", "--path", "/projects/source/readme.md")["results"] == [
        {
            "path": "/projects/source/readme.md",
            "has-boundary": True,
            "boundary-point": "/projects/source",
            "boundary-type": "worktree",
        }
    ]
    assert subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", "--no-index", "--", "projects/source/readme.md"],
        check=False,
    ).returncode == 0

    _run(root, "worktree", "remove", "--work-path", "/projects/source")

    assert not target.exists()
    assert (root / ".gitignore").read_text() == "/kept/\n/projects/source/\n"
    with RuntimeStore(root).read_only_transaction() as transaction:
        assert transaction.state.worktrees == ()


def test_worktree_create_from_installation_uses_recorded_commit_and_default_path(tmp_path: Path, monkeypatch) -> None:
    root, source, commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    _commit(source, "later.md", "later\n")

    created = _run(root, "worktree", "create", "--install-id", installed["install-id"])

    work_path = created["work-path"]
    assert work_path.startswith(f"/.doctidex-git/worktrees/local/{source.as_posix().lstrip('/')}/")
    assert len(work_path.rsplit("/", maxsplit=1)[-1]) == 7
    assert _head(root / work_path.lstrip("/")) == commit
    assert subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", "--no-index", "--", work_path.lstrip("/")],
        check=False,
    ).returncode == 0
    assert _run(root, "worktree", "query", "--work-path", work_path) == {
        "status": "ok",
        "message": {},
        "install-id": installed["install-id"],
    }
    with RuntimeStore(root).read_only_transaction() as transaction:
        assert transaction.state.worktrees[0].base_commit_hash == commit


def test_worktree_random_default_path_retries_after_model_and_physical_collisions(
    tmp_path: Path, monkeypatch
) -> None:
    root, source, commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    managed = _run(
        root,
        "worktree",
        "create",
        "--url",
        str(source),
        "--commit",
        commit,
        "--tree-name",
        "managed",
    )
    shutil.rmtree(root / managed["work-path"].lstrip("/"))
    default_root = root / ".doctidex-git/worktrees/local" / source.as_posix().lstrip("/")
    (default_root / "occupied").mkdir(parents=True)
    random_names = iter(("managed", "occupied", "usable1"))
    monkeypatch.setattr(worktree_workflow, "_random_tree_name", lambda: next(random_names))

    created = _run(root, "worktree", "create", "--url", str(source), "--commit", commit)

    assert created["work-path"] == f"/.doctidex-git/worktrees/local/{source.as_posix().lstrip('/')}/usable1"
    assert _head(root / created["work-path"].lstrip("/")) == commit


def test_worktree_url_selectors_use_and_record_the_resolved_base_commit(tmp_path: Path, monkeypatch) -> None:
    root, source, first_commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    current_commit = _commit(source, "later.md", "later\n")

    branch = _run(
        root,
        "worktree",
        "create",
        "--url",
        str(source),
        "--branch",
        "main",
        "--tree-name",
        "branch",
    )
    tag = _run(
        root,
        "worktree",
        "create",
        "--url",
        str(source),
        "--tag",
        "v1",
        "--tree-name",
        "tag",
    )
    commit = _run(
        root,
        "worktree",
        "create",
        "--url",
        str(source),
        "--commit",
        first_commit,
        "--tree-name",
        "commit",
    )

    assert _head(root / branch["work-path"].lstrip("/")) == current_commit
    assert _head(root / tag["work-path"].lstrip("/")) == first_commit
    assert _head(root / commit["work-path"].lstrip("/")) == first_commit
    with RuntimeStore(root).read_only_transaction() as transaction:
        assert {
            item.work_path: item.base_commit_hash for item in transaction.state.worktrees
        } == {
            branch["work-path"]: current_commit,
            tag["work-path"]: first_commit,
            commit["work-path"]: first_commit,
        }
    branch_directory = root / branch["work-path"].lstrip("/")
    subprocess.run(["git", "-C", str(branch_directory), "config", "user.email", "tests@example.test"], check=True)
    subprocess.run(["git", "-C", str(branch_directory), "config", "user.name", "Tests"], check=True)
    _commit(branch_directory, "worktree-only.md", "local change\n")
    assert _head(branch_directory) != current_commit
    with RuntimeStore(root).read_only_transaction() as transaction:
        assert transaction.state.worktrees[0].base_commit_hash == current_commit


def test_worktree_default_path_uses_git_url_hierarchy_and_nested_tree_name(tmp_path: Path, monkeypatch) -> None:
    root, source, commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")

    created = _run(
        root,
        "worktree",
        "create",
        "--url",
        str(source),
        "--commit",
        commit,
        "--tree-name",
        "review\\topic",
    )

    expected_path = f"/.doctidex-git/worktrees/local/{source.as_posix().lstrip('/')}/review/topic"
    assert created["work-path"] == expected_path
    assert _head(root / expected_path.lstrip("/")) == commit


def test_worktree_create_from_installation_fetches_a_recorded_commit_missing_from_cache(
    tmp_path: Path, monkeypatch
) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    next_commit = _commit(source, "next.md", "next\n")
    _set_installation_commit(root, installed["install-id"], next_commit)

    created = _run(
        root,
        "worktree",
        "create",
        "--install-id",
        installed["install-id"],
        "--work-path",
        "/from-installation",
    )

    assert _head(root / created["work-path"].lstrip("/")) == next_commit
    assert _cache_contains_commit(GitCache.from_environment(), str(source), next_commit)


def test_worktree_create_from_installation_reports_an_unavailable_recorded_commit(
    tmp_path: Path, monkeypatch
) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    installed = _run(root, "import", "install", "--tracked", "--url", str(source), "--branch", "main")
    next_commit = _commit(source, "next.md", "next\n")
    _set_installation_commit(root, installed["install-id"], next_commit)
    source.rename(tmp_path / "source-unavailable")

    failure = _run_error(
        root,
        "worktree",
        "create",
        "--install-id",
        installed["install-id"],
        "--work-path",
        "/from-installation",
    )

    assert failure["message"]["code"] == "worktree.source.unavailable"
    assert failure["message"]["details"] == {"operation": "create", "install-id": installed["install-id"]}


def test_worktree_remove_missing_and_dirty_paths(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    created = _run(
        root, "worktree", "create", "--url", str(source), "--branch", "main", "--work-path", "/work"
    )
    target = root / created["work-path"].lstrip("/")
    (target / "dirty.md").write_text("dirty\n")

    blocked = _run_error(root, "worktree", "remove", "--work-path", "/work")
    assert blocked["message"]["code"] == "worktree.remove.blocked"
    assert blocked["message"]["details"] == {"reason": "uncommitted-changes", "required-option": "--force"}
    assert target.exists()

    _run(root, "worktree", "remove", "--work-path", "/work", "--force")
    assert not target.exists()

    created = _run(
        root, "worktree", "create", "--url", str(source), "--branch", "main", "--work-path", "/missing"
    )
    target = root / created["work-path"].lstrip("/")
    shutil.rmtree(target)
    assert not target.exists()

    _run(root, "worktree", "remove", "--work-path", "/missing")
    assert _run_error(root, "worktree", "query", "--work-path", "/missing")["message"]["code"] == "worktree.not-found"
    recreated = _run(
        root, "worktree", "create", "--url", str(source), "--branch", "main", "--work-path", "/missing"
    )
    assert (root / recreated["work-path"].lstrip("/")).is_dir()
    assert _run(root, "worktree", "remove", "--work-path", "/not-recorded") == {
        "status": "ok",
        "message": {},
    }


def test_worktree_remove_directly_deletes_without_git_cache_or_git_remove(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    created = _run(
        root, "worktree", "create", "--url", str(source), "--branch", "main", "--work-path", "/work"
    )
    target = root / created["work-path"].lstrip("/")
    cache_calls: list[str] = []
    git_calls: list[object] = []

    def unexpected_cache_transaction(*args: object, **kwargs: object) -> object:
        cache_calls.append("transaction")
        raise AssertionError("worktree remove must not open a GitCache transaction")

    original_run = subprocess.run

    def record_git_call(arguments: object, *args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        git_calls.append(arguments)
        return original_run(arguments, *args, **kwargs)

    monkeypatch.setattr(GitCache, "read_only_transaction", unexpected_cache_transaction)
    monkeypatch.setattr(GitCache, "write_transaction", unexpected_cache_transaction)
    monkeypatch.setattr(worktree_workflow.subprocess, "run", record_git_call)

    _run(root, "worktree", "remove", "--work-path", "/work", "--force")

    assert not target.exists()
    assert cache_calls == []
    assert all(arguments[3:5] != ["worktree", "remove"] for arguments in git_calls)


def test_worktree_create_rejects_user_selected_occupied_paths_and_unknown_installation(
    tmp_path: Path, monkeypatch
) -> None:
    root, source, commit = _repositories(tmp_path)
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(tmp_path / "home"))
    _run(root, "init")
    (root / "occupied").mkdir()

    occupied = _run_error(
        root, "worktree", "create", "--url", str(source), "--branch", "main", "--work-path", "/occupied"
    )
    assert occupied["message"]["code"] == "worktree.target.unavailable"
    assert occupied["message"]["details"] == {"operation": "create", "occupant": "existing-path"}

    default_root = root / ".doctidex-git/worktrees/local" / source.as_posix().lstrip("/")
    (default_root / "occupied").mkdir(parents=True)
    named = _run_error(
        root,
        "worktree",
        "create",
        "--url",
        str(source),
        "--commit",
        commit,
        "--tree-name",
        "occupied",
    )
    assert named["message"]["code"] == "worktree.target.unavailable"
    assert named["message"]["details"] == {"operation": "create", "occupant": "existing-path"}

    unavailable = _run_error(root, "worktree", "create", "--install-id", "missing", "--work-path", "/work")
    assert unavailable["message"]["code"] == "worktree.source.unavailable"
    assert unavailable["message"]["details"] == {"operation": "create", "install-id": "missing"}


def test_worktree_create_keeps_gitcache_open_until_runtime_publication(tmp_path: Path, monkeypatch) -> None:
    root, source, _ = _repositories(tmp_path)
    _run(root, "init")
    store = RuntimeStore(root)
    cache = GitCache(tmp_path / "cache")
    cache_activity: list[str] = []
    events: list[str] = []
    _record_cache_transactions(cache, cache_activity, events, monkeypatch)
    original_write_transaction = store.write_transaction

    def write_transaction():
        @contextlib.contextmanager
        def recorded():
            assert cache_activity == ["write"]
            events.append("runtime:open")
            with original_write_transaction() as transaction:
                yield transaction
            events.append("runtime:close")

        return recorded()

    monkeypatch.setattr(store, "write_transaction", write_transaction)

    with StoreCoordinator(store, cache) as coordinator:
        record = worktree_workflow.create(
            store,
            coordinator,
            install_id=None,
            git_url=str(source),
            work_path="/work",
            branch="main",
        )

    assert record.work_path == "/work"
    assert events == [
        "cache:read-only:open",
        "cache:read-only:close",
        "cache:write:open",
        "runtime:open",
        "runtime:close",
        "cache:write:close",
    ]


def _record_cache_transactions(
    cache: GitCache, cache_activity: list[str], events: list[str], monkeypatch
) -> None:
    for name, kind in (("read_only_transaction", "read-only"), ("write_transaction", "write")):
        original = getattr(cache, name)

        def transaction(*, original=original, kind=kind):
            @contextlib.contextmanager
            def recorded():
                events.append(f"cache:{kind}:open")
                with original() as value:
                    cache_activity.append(kind)
                    try:
                        yield value
                    finally:
                        cache_activity.pop()
                events.append(f"cache:{kind}:close")

            return recorded()

        monkeypatch.setattr(cache, name, transaction)


def _repositories(tmp_path: Path) -> tuple[Path, Path, str]:
    root = tmp_path / "root"
    source = tmp_path / "source"
    for repository in (root, source):
        subprocess.run(["git", "init", "--quiet", "--initial-branch", "main", str(repository)], check=True)
        subprocess.run(["git", "-C", str(repository), "config", "user.email", "tests@example.test"], check=True)
        subprocess.run(["git", "-C", str(repository), "config", "user.name", "Tests"], check=True)
    commit = _commit(source, "readme.md", "source\n")
    return root, source, commit


def _commit(repository: Path, name: str, content: str) -> str:
    (repository / name).write_text(content)
    subprocess.run(["git", "-C", str(repository), "add", name], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "--quiet", "-m", name], check=True)
    if name == "readme.md":
        subprocess.run(["git", "-C", str(repository), "tag", "v1"], check=True)
    return subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _head(repository: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _set_installation_commit(git_root: Path, install_id: str, commit_hash: str) -> None:
    store = RuntimeStore(git_root)
    with store.write_transaction() as transaction:
        state = transaction.state
        updated = tuple(
            replace(item, commit_hash=commit_hash) if item.install_id == install_id else item
            for item in state.installations
        )
        assert updated != state.installations
        transaction.replace_state(replace(state, installations=updated))


def _cache_contains_commit(cache: GitCache, git_url: str, commit_hash: str) -> bool:
    with cache.read_only_transaction() as transaction:
        repository = transaction.repository(git_url)
    return subprocess.run(
        ["git", "-C", str(repository), "cat-file", "-e", f"{commit_hash}^{{commit}}"],
        check=False,
    ).returncode == 0


def _query_installation(install_id: str, keys: tuple[str, ...]) -> Installation:
    return Installation(
        tracked=False,
        git_url=f"https://example.test/{install_id}.git",
        commit_hash="0123456789abcdef",
        install_id=install_id,
        install_path=f"/.doctidex-git/imports/{install_id}",
        keys=keys,
    )


def _run(root: Path, *arguments: str) -> dict[str, object]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(["--repos-path", str(root), *arguments])
    assert code == 0, output.getvalue()
    return json.loads(output.getvalue())


def _run_error(root: Path, *arguments: str) -> dict[str, object]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(["--repos-path", str(root), *arguments])
    assert code == 2
    return json.loads(output.getvalue())
