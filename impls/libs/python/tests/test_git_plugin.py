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
