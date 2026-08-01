from __future__ import annotations

from pathlib import Path

import pytest

from whero.doctidex.errors import DoctidexError
from whero.doctidex.protocol.root import root_at
from whero.doctidex.protocol.validation import normalize_scopes, validate_protocol


def write_root(root: Path, *, config: str = "", body: str = "# Root\n") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.md").write_text(
        f"""---
type: index
doctidex:
  type: index
  root: true
{config}---
{body}
""",
        encoding="utf-8",
    )


def validate(root: Path, **kwargs: object) -> dict:
    context = root_at(root)
    assert context is not None
    return validate_protocol(context, **kwargs)


def test_valid_tree_and_scopes(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(root, body="# Root\n\n[Guide](guide.md)\n")
    (root / "guide.md").write_text("# Guide\n", encoding="utf-8")

    result = validate(root)
    assert result["schema_version"] == "1.0"
    assert result["coverage"] == "full"
    assert result["scopes"] == ["/"]
    assert result["protocol_structure"] == "pass"
    assert result["scan_complete"] is True
    assert result["collection"]["lists"]["findings"]["total"] == 0
    assert normalize_scopes(root, ["/", "/./"]) == ["/"]


def test_boundary_unsafe_annotation_and_reachability(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(
        root,
        config="""  boundary-set:
    - path: external
  unsafe:
    - path: external
""",
        body=("# Root\n\n[External](external/readme.md)\n<!-- doctidex: {unsafe: true} -->\n"),
    )
    (root / "external").mkdir()
    (root / "external" / "readme.md").write_text("[Missing annotation is exempt here](../index.md)\n", encoding="utf-8")

    result = validate(root)
    assert result["protocol_structure"] == "pass"
    assert result["semantic_review"] == "required"
    assert {item["code"] for item in result["semantic_candidates"]} == {"unsafe_scope_review"}


def test_invalid_annotation_and_unreachable_path_are_separate_findings(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(
        root,
        config="""  boundary-set:
    - path: external
""",
        body="# Root\n\n[Local](local.md)\n",
    )
    (root / "local.md").write_text("[External](external/readme.md)\n", encoding="utf-8")
    (root / "external").mkdir()
    (root / "external" / "readme.md").write_text("external\n", encoding="utf-8")
    (root / "orphan.md").write_text("orphan\n", encoding="utf-8")

    result = validate(root)
    codes = {item["code"] for item in result["findings"]}
    assert result["protocol_structure"] == "fail"
    assert "link_annotation_invalid" in codes
    assert "path_unreachable" in codes


def test_index_log_and_atomic_rules(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(
        root,
        config="""  atomic-indexing:
    - path: bundle
""",
        body="# Root\n\n[Bundle](bundle)\n[Child](child/index.md)\n",
    )
    (root / "bundle").mkdir()
    (root / "bundle" / "index.md").write_text("broken\n", encoding="utf-8")
    (root / "child").mkdir()
    (root / "child" / "index.md").write_text(
        "---\ntype: index\ndoctidex:\n  type: index\n---\n# Child\n",
        encoding="utf-8",
    )
    (root / "child" / "log.md").write_text(
        "---\ntype: log\ndoctidex:\n  type: log\n---\n# Log\n",
        encoding="utf-8",
    )

    result = validate(root)
    codes = {item["code"] for item in result["findings"]}
    assert "atomic_indexing_invalid" in codes
    assert "log_continuity_invalid" in codes


def test_scoped_validation_filters_output_and_cursor_is_state_bound(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(root, body="# Root\n\n[A](a)\n[B](b)\n")
    for name in ("a", "b"):
        (root / name).mkdir()
        (root / name / "orphan.md").write_text(name, encoding="utf-8")

    result = validate(root, scopes=["/a"], limit=1)
    assert result["coverage"] == "scoped"
    assert result["scopes"] == ["/a"]
    assert all("/b/" not in item["path"] for item in result["findings"])
    cursor = result["collection"]["next_cursor"]
    if cursor:
        (root / "a" / "new.md").write_text("new", encoding="utf-8")
        with pytest.raises(DoctidexError) as caught:
            validate(root, scopes=["/a"], limit=1, cursor=cursor)
        assert caught.value.code == "cursor_invalid"


def test_invalid_scope_does_not_fall_back_to_full(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(root)
    with pytest.raises(DoctidexError) as caught:
        validate(root, scopes=["../outside"])
    assert caught.value.code == "scope_invalid"


def test_directory_only_local_config_rejects_an_existing_file(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(
        root,
        config="""  boundary-set:
    - path: guide.md
  atomic-indexing:
    - path: guide.md
""",
        body="# Root\n\n[Guide](guide.md)\n",
    )
    (root / "guide.md").write_text("# Guide\n", encoding="utf-8")
    result = validate(root)
    matching = [item for item in result["findings"] if item["code"] == "local_config_invalid"]
    assert len(matching) == 2


def test_reference_link_annotation_is_associated_with_the_link(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(
        root,
        config="""  boundary-set:
    - path: external
""",
        body="# Root\n\n[Guide](guide.md)\n[External](external)\n",
    )
    (root / "external").mkdir()
    (root / "external" / "readme.md").write_text("external\n", encoding="utf-8")
    (root / "guide.md").write_text(
        "[External guide][external-guide]\n"
        "<!-- another-standard: retained -->\n"
        "<!-- doctidex: {cross-boundary-point: /external} -->\n\n"
        "[external-guide]: external/readme.md\n",
        encoding="utf-8",
    )

    result = validate(root)
    assert "link_annotation_invalid" not in {item["code"] for item in result["findings"]}


def test_scoped_validation_does_not_read_unrelated_subtree(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(root, body="# Root\n\n[A](a)\n[B](b)\n")
    (root / "a").mkdir()
    (root / "a" / "guide.md").write_text("guide\n", encoding="utf-8")
    (root / "b").mkdir()
    (root / "b" / "invalid.md").write_bytes(b"\xff")

    scoped = validate(root, scopes=["/a"])
    assert scoped["scan_complete"] is True
    assert all("/b/" not in (item["path"] or "") for item in scoped["findings"])

    full = validate(root)
    assert full["scan_complete"] is False
    assert any(item["code"] == "document_unreadable" for item in full["findings"])
