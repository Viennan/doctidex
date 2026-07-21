from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from whero_wiki_tools.frontmatter import (  # noqa: E402
    read_markdown,
    write_markdown_atomic,
)
from whero_wiki_tools.model import FORMAT_VERSION  # noqa: E402
from whero_wiki_tools.view_service import execute_view  # noqa: E402
from whero_wiki_tools.view_types import OperationResult, ViewRequest  # noqa: E402


def wiki_meta_text(
    *,
    version: str = FORMAT_VERSION,
    title: str = "Test Wiki",
    extra: dict[str, Any] | None = None,
) -> str:
    fields: dict[str, Any] = {
        "type": "Whero Wiki",
        "title": title,
        "description": "Test knowledge fixture.",
        "format_version": version,
        "whero_wiki": True,
        "whero_maintenance": True,
        "whero_view_required": True,
    }
    fields.update(extra or {})
    lines = ["---", *(f"{key}: {yaml_scalar(value)}" for key, value in fields.items()), "---"]
    return "\n".join(lines) + f"\n\n# {title}\n"


def yaml_scalar(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return str(value)


def create_wiki(root: Path, *, title: str = "Test Wiki") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "whero-wiki-meta.md").write_text(
        wiki_meta_text(title=title),
        encoding="utf-8",
    )
    return root


def framework_fields(
    document_type: str,
    title: str,
    **extra: Any,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "type": document_type,
        "title": title,
        "description": f"{title} routes.",
        "whero_maintenance": True,
        "whero_view_required": True,
    }
    fields.update(extra)
    return fields


def write_index(
    path: Path,
    *,
    title: str = "Test Index",
    body: str | None = None,
    **extra: Any,
) -> Path:
    write_markdown_atomic(
        path,
        framework_fields("Whero Wiki Index", title, **extra),
        body or f"\n# {title}\n",
    )
    return path


def write_view_status(
    view: Path,
    source: Path,
    *,
    requested: tuple[str, ...] = ("whero-wiki-meta.md",),
    effective: tuple[str, ...] | None = None,
) -> Path:
    status = view / "whero-wiki-view.md"
    write_markdown_atomic(
        status,
        {
            "type": "Whero Wiki View",
            "title": "Whero Wiki View",
            "description": "Test View fixture.",
            "format_version": FORMAT_VERSION,
            "whero_maintenance": True,
            "whero_view_required": True,
            "whero_view": True,
            "source": os.path.relpath(source, start=view),
            "source_validation": "path",
            "layout": "source-relative",
            "view_name": view.name,
            "collapse_threshold": 0,
            "requested_selections": list(requested),
            "effective_roots": list(effective or requested),
            "disclosed_symlinks": len(requested),
        },
        "\n# Whero Wiki View\n",
    )
    return status


class WikiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)
        self.root = create_wiki(self.workspace / "wiki")
        self.view_parent = self.workspace / "views"
        self.view_parent.mkdir()

    def write(
        self,
        relative: str,
        text: str = "# Source\n",
        *,
        root: Path | None = None,
    ) -> Path:
        path = (root or self.root).joinpath(*PurePosixPath(relative).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def build_view(
        self,
        *paths: str,
        source: Path | None = None,
        target: Path | None = None,
        view_name: str = "view",
        collapse_threshold: float = 0,
        dry_run: bool = False,
        allow_path_relocation: bool = False,
    ) -> OperationResult:
        request = ViewRequest(
            source=source or self.root,
            target=target or self.view_parent,
            view_name=view_name,
            includes=tuple(paths),
            include_files=(),
            collapse_threshold=collapse_threshold,
            dry_run=dry_run,
            allow_path_relocation=allow_path_relocation,
        )
        return execute_view(request)

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "whero_wiki.py"), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def git(self, repository: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def init_git(self, repository: Path) -> None:
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")

    def commit_all(self, repository: Path, message: str) -> str:
        self.git(repository, "add", "-A")
        self.git(repository, "commit", "-qm", message)
        return self.git(repository, "rev-parse", "HEAD")

    def append_index_link(self, index: Path, destination: str, label: str) -> None:
        document = read_markdown(index)
        write_markdown_atomic(
            index,
            document.fields,
            document.body.rstrip() + f"\n\n[{label}]({destination})\n",
            overwrite=True,
        )
