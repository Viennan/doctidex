from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from whero.doctidex.protocol.document import DoctidexDocument


def run(command: list[str], cwd: Path, env: dict[str, str], expected: int = 0) -> dict:
    process = subprocess.run(
        [sys.executable, "-m", "whero.doctidex.cli.main", *command, "--json"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert process.returncode == expected, process.stdout + process.stderr
    return json.loads(process.stdout)


def git(cwd: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )
    return process.stdout.strip()


def commit_all(repository: Path, message: str) -> str:
    git(repository, "add", ".")
    git(repository, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", message)
    return git(repository, "rev-parse", "HEAD")


@pytest.fixture
def environment(tmp_path: Path) -> dict[str, str]:
    value = os.environ.copy()
    value["WHERO_DOCTIDEX_STATE_DIR"] = str(tmp_path / "state")
    return value


def make_source(path: Path) -> str:
    path.mkdir()
    git(path, "init", "-b", "main")
    (path / "index.md").write_text(
        """---
type: index
doctidex:
  type: index
  root: true
  excludes:
    - path: .doctidex/mounts
---
# Source

[Content](content.md)
[Guide](guide/)
""",
        encoding="utf-8",
    )
    (path / ".gitignore").write_text("/.doctidex/mounts/\n", encoding="utf-8")
    (path / "content.md").write_text("version one\n", encoding="utf-8")
    (path / "guide").mkdir()
    (path / "guide" / "notes.md").write_text("notes\n", encoding="utf-8")
    return commit_all(path, "initial")


def make_host(path: Path, env: dict[str, str]) -> None:
    path.mkdir()
    git(path, "init", "-b", "main")
    result = run(["init", ".", "--apply"], path, env)
    assert result["operation"] == "init"
    (path / "index.md").write_text(
        (path / "index.md").read_text(encoding="utf-8") + "\n# Host\n",
        encoding="utf-8",
    )
    commit_all(path, "initialize host")


def test_lazy_mount_sync_reuse_and_maintenance(tmp_path: Path, environment: dict[str, str]) -> None:
    source = tmp_path / "source"
    host = tmp_path / "host"
    first_commit = make_source(source)
    make_host(host, environment)

    for name in ("design", "design-copy"):
        result = run(
            [
                "mount",
                "add",
                "--url",
                str(source),
                "--branch",
                "main",
                "--mount-path",
                f"/.doctidex/mounts/{name}",
                "--apply",
            ],
            host,
            environment,
        )
        assert result["mount_state"] == "not_prepared"

    listing = run(["mount", "list"], host, environment)
    assert all(item["state"] == "not_prepared" for item in listing["items"])
    assert not (host / ".doctidex" / "mounts" / "design").exists()

    reference = host / "reference.md"
    reference.write_text("[External](/.doctidex/mounts/design/content.md)\n", encoding="utf-8")
    blocked_remove = run(["mount", "remove", "/.doctidex/mounts/design", "--dry-run"], host, environment, expected=2)
    assert blocked_remove["findings"][0]["code"] == "mount_still_referenced"
    reference.unlink()

    prepared = run(["mount", "prepare", "/.doctidex/mounts/design"], host, environment)
    assert prepared["effective_commit"] == first_commit
    mounted = host / ".doctidex" / "mounts" / "design" / "content.md"
    assert mounted.read_text(encoding="utf-8") == "version one\n"

    run(["mount", "prepare", "/.doctidex/mounts/design-copy"], host, environment)
    nested = host / ".doctidex" / "mounts" / "design" / "guide" / ".doctidex" / "mounts" / "design-copy" / "content.md"
    assert nested.read_text(encoding="utf-8") == "version one\n"

    source_document = host / ".doctidex" / "mounts" / "design" / "content.md"
    resolved_source = run(
        ["resolve", "/guide/notes.md", "--from", str(source_document)],
        host,
        environment,
    )
    assert resolved_source["root"] == str(host)
    assert resolved_source["link_document"] == str(source_document)
    assert resolved_source["link_root"] == str(host / ".doctidex" / "mounts" / "design")
    assert resolved_source["link_root_kind"] == "mounted_source"
    assert resolved_source["working_path"] == str(host / ".doctidex" / "mounts" / "design" / "guide" / "notes.md")
    assert resolved_source["mount"]["mount_path"] == "/.doctidex/mounts/design"

    resolved_namespace = run(
        ["resolve", "/.doctidex/mounts/design-copy/content.md", "--from", str(source_document)],
        host,
        environment,
    )
    assert resolved_namespace["link_root"] == str(host)
    assert resolved_namespace["link_root_kind"] == "host_root"
    assert resolved_namespace["working_path"] == str(
        host / ".doctidex" / "mounts" / "design-copy" / "content.md"
    )

    inspected = run(["inspect", str(source_document)], host, environment)
    assert inspected["root"] == str(host)
    assert inspected["path_context"]["source"] == "mount"
    assert inspected["source_context"]["host_root"] == str(host / ".doctidex" / "mounts" / "design")

    (source / "content.md").write_text("version two\n", encoding="utf-8")
    second_commit = commit_all(source, "second")
    preview = run(["mount", "sync", "/.doctidex/mounts/design", "--dry-run"], host, environment)
    assert preview["old_effective_commit"] == first_commit
    assert preview["new_effective_commit"] == second_commit
    assert mounted.read_text(encoding="utf-8") == "version one\n"

    run(["mount", "sync", "/.doctidex/mounts/design", "--apply"], host, environment)
    assert mounted.read_text(encoding="utf-8") == "version two\n"
    assert (host / ".doctidex" / "mounts" / "design-copy" / "content.md").read_text(encoding="utf-8") == "version one\n"

    opened = run(["maintenance", "open", "/.doctidex/mounts/design"], host, environment)
    maintenance = Path(opened["maintenance_root"])
    status = run(["maintenance", "status", str(maintenance)], tmp_path, environment)
    assert status["items"][0]["maintenance_root"] == str(maintenance)
    (maintenance / "content.md").write_text("maintenance change\n", encoding="utf-8")
    handoff = run(["maintenance", "handoff", str(maintenance)], tmp_path, environment)
    assert handoff["maintenance_root"] == str(maintenance)
    assert mounted.read_text(encoding="utf-8") == "version two\n"
    blocked = run(["maintenance", "close", str(maintenance)], host, environment, expected=2)
    assert blocked["status"] == "blocked"
    assert maintenance.exists()

    clean_opened = run(["maintenance", "open", "/.doctidex/mounts/design-copy"], host, environment)
    clean_maintenance = Path(clean_opened["maintenance_root"])
    closed = run(["maintenance", "close", str(clean_maintenance)], tmp_path, environment)
    assert closed["maintenance_root"] == str(clean_maintenance)
    assert not clean_maintenance.exists()


def test_self_reference_same_commit_recommends_host_scope(tmp_path: Path, environment: dict[str, str]) -> None:
    host = tmp_path / "host"
    make_host(host, environment)
    head = git(host, "rev-parse", "HEAD")
    run(
        [
            "mount",
            "add",
            "--url",
            str(host),
            "--commit",
            head,
            "--mount-path",
            "/.doctidex/mounts/self",
            "--apply",
        ],
        host,
        environment,
    )
    run(["mount", "prepare", "/.doctidex/mounts/self"], host, environment)

    resolved = run(["resolve", "/.doctidex/mounts/self/index.md"], host, environment)
    assert resolved["working_path"] == str(host / ".doctidex" / "mounts" / "self" / "index.md")
    assert resolved["root_relation"] == {
        "source": "same_repository",
        "revision": "same_commit",
    }
    assert resolved["maintenance_reuse"] == {
        "status": "recommended",
        "scope_kind": "host_root",
        "write_path": str(host),
        "target_branch": "main",
        "candidate_count": 1,
        "reason": "current_root_same_commit",
    }

    scoped = run(
        ["maintenance", "scope", ".", ".doctidex/mounts/self/index.md"],
        host,
        environment,
    )
    host_item = next(item for item in scoped["items"] if item["kind"] == "host_root")
    mount_item = next(item for item in scoped["items"] if item["kind"] == "mounted_source")
    assert host_item["write_path"] == str(host)
    assert mount_item["maintenance_reuse"]["scope_kind"] == "host_root"
    assert mount_item["maintenance_reuse"]["write_path"] == str(host)
    assert mount_item["write_action"] is None

    opened = run(["maintenance", "open", "/.doctidex/mounts/self"], host, environment)
    assert opened["status"] == "warning"
    assert opened["root_relation"]["revision"] == "same_commit"
    assert opened["maintenance_reuse"]["write_path"] == str(host)
    assert Path(opened["maintenance_root"]) != host
    run(["maintenance", "close", opened["maintenance_root"]], host, environment)


def test_self_reference_same_commit_respects_target_branch(
    tmp_path: Path, environment: dict[str, str]
) -> None:
    host = tmp_path / "host"
    make_host(host, environment)
    git(host, "branch", "feature")
    run(
        [
            "mount",
            "add",
            "--url",
            str(host),
            "--branch",
            "feature",
            "--mount-path",
            "/.doctidex/mounts/self-feature",
            "--apply",
        ],
        host,
        environment,
    )
    run(["mount", "prepare", "/.doctidex/mounts/self-feature"], host, environment)

    resolved = run(["resolve", "/.doctidex/mounts/self-feature/index.md"], host, environment)
    assert resolved["root_relation"] == {
        "source": "same_repository",
        "revision": "same_commit",
    }
    assert resolved["maintenance_reuse"] == {
        "status": "not_available",
        "scope_kind": None,
        "write_path": None,
        "target_branch": None,
        "candidate_count": 0,
        "reason": "delivery_target_conflict",
    }

    item = run(
        ["maintenance", "scope", ".doctidex/mounts/self-feature/index.md"],
        host,
        environment,
    )["items"][0]
    assert item["declared_revision"] == {"kind": "branch", "value": "feature"}
    assert item["target_branch"] == "feature"
    assert item["write_action"] == "doctidex-git maintenance open /.doctidex/mounts/self-feature"


def test_self_reference_different_commit_keeps_independent_scope(
    tmp_path: Path, environment: dict[str, str]
) -> None:
    host = tmp_path / "host"
    make_host(host, environment)
    old_commit = git(host, "rev-parse", "HEAD")
    (host / "current.md").write_text("current\n", encoding="utf-8")
    commit_all(host, "advance host")
    run(
        [
            "mount",
            "add",
            "--url",
            str(host),
            "--commit",
            old_commit,
            "--mount-path",
            "/.doctidex/mounts/old-self",
            "--apply",
        ],
        host,
        environment,
    )
    run(["mount", "prepare", "/.doctidex/mounts/old-self"], host, environment)

    resolved = run(["resolve", "/.doctidex/mounts/old-self/index.md"], host, environment)
    assert resolved["root_relation"] == {
        "source": "same_repository",
        "revision": "different_commit",
    }
    assert resolved["maintenance_reuse"]["status"] == "not_available"
    assert resolved["maintenance_reuse"]["reason"] == "current_root_different_commit"

    scoped = run(
        ["maintenance", "scope", ".doctidex/mounts/old-self/index.md"],
        host,
        environment,
    )
    item = scoped["items"][0]
    assert item["root_relation"]["revision"] == "different_commit"
    assert item["write_action"] == "doctidex-git maintenance open /.doctidex/mounts/old-self"


def test_nested_root_does_not_claim_repository_root_self_reference(
    tmp_path: Path, environment: dict[str, str]
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    nested = repository / "docs"
    nested.mkdir()
    (nested / "index.md").write_text(
        """---
type: index
doctidex:
  type: index
  root: true
  excludes:
    - path: .doctidex/mounts
---
""",
        encoding="utf-8",
    )
    (nested / ".gitignore").write_text("/.doctidex/mounts/\n", encoding="utf-8")
    head = commit_all(repository, "nested root")
    (nested / "index.md").write_text(
        f"""---
type: index
doctidex:
  type: index
  root: true
  excludes:
    - path: .doctidex/mounts
  mounts:
    - type: git
      url: {repository}
      revision:
        commit: {head}
      mount_path: /.doctidex/mounts/repository
---
""",
        encoding="utf-8",
    )

    scoped = run(["maintenance", "scope", ".doctidex/mounts/repository/index.md"], nested, environment)
    assert scoped["items"][0]["root_relation"] == {"source": "unknown", "revision": "unknown"}


def test_scp_remote_is_not_misread_as_an_equivalent_local_source(
    tmp_path: Path, environment: dict[str, str]
) -> None:
    host = tmp_path / "host"
    make_host(host, environment)
    local_source = host / "git@example.com:repo.git"
    source_commit = make_source(local_source)
    git(host, "remote", "add", "origin", "git@example.com:repo.git")
    run(
        [
            "mount",
            "add",
            "--url",
            "./git@example.com:repo.git",
            "--commit",
            source_commit,
            "--mount-path",
            "/.doctidex/mounts/local-lookalike",
            "--apply",
        ],
        host,
        environment,
    )

    item = run(
        ["maintenance", "scope", ".doctidex/mounts/local-lookalike/index.md"],
        host,
        environment,
    )["items"][0]
    assert item["root_relation"] == {"source": "unknown", "revision": "unknown"}


def test_same_source_commit_reuses_open_maintenance_scope(tmp_path: Path, environment: dict[str, str]) -> None:
    source = tmp_path / "source"
    host = tmp_path / "host"
    source_commit = make_source(source)
    make_host(host, environment)
    for name in ("one", "two"):
        run(
            [
                "mount",
                "add",
                "--url",
                str(source),
                "--commit",
                source_commit,
                "--mount-path",
                f"/.doctidex/mounts/{name}",
                "--apply",
            ],
            host,
            environment,
        )
        run(["mount", "prepare", f"/.doctidex/mounts/{name}"], host, environment)

    initial = run(
        [
            "maintenance",
            "scope",
            ".doctidex/mounts/one/index.md",
            ".doctidex/mounts/two/index.md",
        ],
        host,
        environment,
    )
    assert {item["source"] for item in initial["items"]} == {str(source)}
    assert {item["base_commit"] for item in initial["items"]} == {source_commit}
    assert all(item["maintenance_reuse"]["status"] == "not_available" for item in initial["items"])

    opened = run(["maintenance", "open", "/.doctidex/mounts/one"], host, environment)
    maintenance_root = opened["maintenance_root"]
    scoped = run(
        [
            "maintenance",
            "scope",
            ".doctidex/mounts/one/index.md",
            ".doctidex/mounts/two/index.md",
        ],
        host,
        environment,
    )
    assert all(item["maintenance_reuse"]["status"] == "recommended" for item in scoped["items"])
    assert all(item["maintenance_reuse"]["write_path"] == maintenance_root for item in scoped["items"])
    assert all(item["write_action"] is None for item in scoped["items"])

    second_opened = run(["maintenance", "open", "/.doctidex/mounts/two"], host, environment)
    assert second_opened["status"] == "warning"
    assert second_opened["maintenance_reuse"]["write_path"] == maintenance_root
    selection = run(
        ["maintenance", "scope", ".doctidex/mounts/two/index.md"],
        host,
        environment,
    )["items"][0]
    assert selection["maintenance_reuse"] == {
        "status": "selection_required",
        "scope_kind": "maintenance_root",
        "write_path": None,
        "target_branch": None,
        "candidate_count": 2,
        "reason": "multiple_existing_scopes",
    }
    assert selection["write_action"] == "doctidex-git maintenance status --json"

    run(["maintenance", "close", maintenance_root], host, environment)
    run(["maintenance", "close", second_opened["maintenance_root"]], host, environment)


def test_same_commit_branch_mounts_do_not_reuse_conflicting_delivery_targets(
    tmp_path: Path, environment: dict[str, str]
) -> None:
    source = tmp_path / "source"
    host = tmp_path / "host"
    source_commit = make_source(source)
    git(source, "branch", "feature")
    make_host(host, environment)
    for name, branch in (("main-source", "main"), ("feature-source", "feature")):
        run(
            [
                "mount",
                "add",
                "--url",
                str(source),
                "--branch",
                branch,
                "--mount-path",
                f"/.doctidex/mounts/{name}",
                "--apply",
            ],
            host,
            environment,
        )
        run(["mount", "prepare", f"/.doctidex/mounts/{name}"], host, environment)

    opened = run(["maintenance", "open", "/.doctidex/mounts/main-source"], host, environment)
    feature = run(
        ["maintenance", "scope", ".doctidex/mounts/feature-source/index.md"],
        host,
        environment,
    )["items"][0]
    assert feature["base_commit"] == source_commit
    assert feature["target_branch"] == "feature"
    assert feature["maintenance_reuse"] == {
        "status": "not_available",
        "scope_kind": None,
        "write_path": None,
        "target_branch": None,
        "candidate_count": 0,
        "reason": "delivery_target_conflict",
    }
    assert feature["write_action"] == "doctidex-git maintenance open /.doctidex/mounts/feature-source"

    main = run(
        ["maintenance", "scope", ".doctidex/mounts/main-source/index.md"],
        host,
        environment,
    )["items"][0]
    assert main["maintenance_reuse"]["write_path"] == opened["maintenance_root"]
    assert main["maintenance_reuse"]["target_branch"] == "main"
    run(["maintenance", "close", opened["maintenance_root"]], host, environment)


def test_resolve_rejects_missing_link_source(tmp_path: Path, environment: dict[str, str]) -> None:
    host = tmp_path / "host"
    make_host(host, environment)
    result = run(["resolve", "/guide.md", "--from", str(host / "missing.md")], host, environment, expected=2)
    assert result["findings"][0]["code"] == "link_source_invalid"


def test_resolve_preserves_nested_root_ambiguity(tmp_path: Path, environment: dict[str, str]) -> None:
    host = tmp_path / "host"
    make_host(host, environment)
    nested = host / "nested"
    nested.mkdir()
    document = DoctidexDocument.new_root(nested / "index.md")
    document.write()
    (nested / "source.md").write_text("[Target](/target.md)\n", encoding="utf-8")

    ambiguous = run(
        ["resolve", "/target.md", "--from", str(nested / "source.md")],
        host,
        environment,
        expected=2,
    )
    assert ambiguous["findings"][0]["code"] == "root_ambiguous"

    outside = tmp_path / "outside"
    make_host(outside, environment)
    unrelated = run(
        ["resolve", "/target.md", "--from", str(nested / "source.md")],
        outside,
        environment,
        expected=2,
    )
    assert unrelated["findings"][0]["code"] == "root_ambiguous"

    selected = run(
        ["resolve", "/target.md", "--from", str(nested / "source.md")],
        nested,
        environment,
    )
    assert selected["link_root"] == str(nested)
    assert selected["working_path"] == str(nested / "target.md")


def test_check_separates_protocol_and_plugin_status(tmp_path: Path, environment: dict[str, str]) -> None:
    host = tmp_path / "host"
    make_host(host, environment)
    (host / ".gitignore").write_text("", encoding="utf-8")
    result = run(["check"], host, environment)
    assert result["protocol_structure"] == "pass"
    assert result["plugin_readiness"] == "blocked"
    assert any(item["domain"] == "plugin_readiness" for item in result["findings"])
