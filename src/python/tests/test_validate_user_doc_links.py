from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.validator_script, pytest.mark.no_cover]

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "validate-user-doc-links.py"


def _write(directory: Path, name: str, content: str) -> None:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _run_validator(docs_root: Path, references_root: Path) -> tuple[int, list[dict[str, object]]]:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--docs-root",
            str(docs_root),
            "--references-root",
            str(references_root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    violations = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    return completed.returncode, violations


def test_relative_link_resolves(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    refs = tmp_path / "refs"
    _write(docs, "a.md", "[b](b.md)\n")
    _write(docs, "b.md", "# B\n")
    _write(refs, "b.md", "# B\n")

    code, violations = _run_validator(docs, refs)

    assert code == 0
    assert violations == []


def test_scheme_link_is_rejected(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    refs = tmp_path / "refs"
    _write(docs, "a.md", "[b](https://example.com/b.md)\n")

    code, violations = _run_validator(docs, refs)

    assert code == 1
    assert violations[0]["kind"] == "non-relative"


def test_root_absolute_link_is_rejected(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    refs = tmp_path / "refs"
    _write(docs, "a.md", "[b](/b.md)\n")

    code, violations = _run_validator(docs, refs)

    assert code == 1
    assert violations[0]["kind"] == "non-relative"


def test_parent_escape_is_rejected(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    refs = tmp_path / "refs"
    _write(docs, "a.md", "[outside](../outside.md)\n")

    code, violations = _run_validator(docs, refs)

    assert code == 1
    assert violations[0]["kind"] == "out-of-scope"


def test_dangling_packaged_target_is_rejected(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    refs = tmp_path / "refs"
    _write(docs, "a.md", "[b](b.md)\n")
    _write(docs, "b.md", "# B\n")

    code, violations = _run_validator(docs, refs)

    assert code == 1
    assert violations[0]["kind"] == "dangling"


def test_missing_fragment_is_rejected(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    refs = tmp_path / "refs"
    _write(docs, "a.md", "[b](b.md#missing)\n")
    _write(docs, "b.md", "# Present\n")
    _write(refs, "b.md", "# Present\n")

    code, violations = _run_validator(docs, refs)

    assert code == 1
    assert violations[0]["kind"] == "missing-fragment"


def test_code_block_example_is_ignored(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    refs = tmp_path / "refs"
    _write(docs, "a.md", "```markdown\n[outside](/outside.md)\n```\n")

    code, violations = _run_validator(docs, refs)

    assert code == 0
    assert violations == []
