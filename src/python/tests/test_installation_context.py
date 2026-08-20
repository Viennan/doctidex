from __future__ import annotations

from pathlib import Path

import pytest

from whero.doctidex.errors import CommandFailure
from whero.doctidex.installation import resolve_installation_context


def test_resolve_installation_context_returns_none_for_ordinary_root(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()

    assert resolve_installation_context(root) is None


def test_resolve_installation_context_rejects_ambiguous_nesting(tmp_path: Path) -> None:
    root = (
        tmp_path
        / "owner"
        / ".doctidex-git"
        / "imports"
        / "outer"
        / ".doctidex-git"
        / "imports"
        / "inner"
    )
    root.mkdir(parents=True)

    with pytest.raises(CommandFailure) as raised:
        resolve_installation_context(root)

    assert raised.value.code == "installation.owner.ambiguous"
    assert [Path(path) for path in raised.value.details["owner-paths"]] == [
        (tmp_path / "owner" / ".doctidex-git" / "imports" / "outer").resolve(),
        (tmp_path / "owner").resolve(),
    ]
