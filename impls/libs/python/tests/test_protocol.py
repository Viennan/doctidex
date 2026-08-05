from __future__ import annotations

from pathlib import Path

import pytest

from whero.doctidex.errors import DoctidexError
from whero.doctidex.protocol.root import root_at
from whero.doctidex.protocol.validation import normalize_scopes, tree_observations, validate_protocol


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


def test_empty_child_index_is_reachable_from_its_parent(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(root, body="# Root\n\n[Empty](empty/index.md)\n")
    empty = root / "empty"
    empty.mkdir()
    (empty / "index.md").write_text(
        "---\n"
        "type: index\n"
        "doctidex:\n"
        "  type: index\n"
        "---\n"
        "\n"
        "# Empty\n",
        encoding="utf-8",
    )

    assert validate(root)["protocol_structure"] == "pass"


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


def test_unsafe_directory_keeps_its_entry_without_scanning_contents(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(
        root,
        config="""  unsafe:
    - path: collected
""",
        body="# Root\n\n[Collected](collected)\n<!-- doctidex: {unsafe: true} -->\n",
    )
    (root / "collected").mkdir()
    (root / "collected" / "index.md").write_text("not a doctidex index\n", encoding="utf-8")
    (root / "collected" / "unreachable.md").write_text("# Unreachable\n", encoding="utf-8")

    context = root_at(root)
    assert context is not None
    observations = tree_observations(context)
    result = validate(root)

    assert root / "collected" in observations.paths
    assert root / "collected" / "index.md" not in observations.paths
    assert root / "collected" / "unreachable.md" not in observations.paths
    assert result["protocol_structure"] == "pass"


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


def test_block_mapping_link_annotation_is_valid(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(
        root,
        config="""  boundary-set:
    - path: external
""",
        body="# Root\n\n[Guide](guide.md)\n[External](external)\n",
    )
    (root / "external").mkdir()
    (root / "external" / "readme.md").write_text("# External\n", encoding="utf-8")
    (root / "guide.md").write_text(
        "[External guide](external/readme.md)\n"
        "<!-- doctidex:\n"
        "  cross-boundary-point: /external\n"
        "-->\n",
        encoding="utf-8",
    )

    result = validate(root)

    assert result["protocol_structure"] == "pass"


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


def test_tree_observations_share_link_resolution(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(root, body="# Root\n\n[Guide](/guide.md#details)\n")
    (root / "guide.md").write_text("# Guide\n", encoding="utf-8")
    context = root_at(root)
    assert context is not None

    observations = tree_observations(context)
    assert len(observations.links) == 1
    link = observations.links[0]
    assert link.document == root / "index.md"
    assert link.raw_target == "/guide.md#details"
    assert link.target == root / "guide.md"
    assert link.is_file_link is True
    assert validate(root)["protocol_structure"] == "pass"


def test_query_links_do_not_form_file_path_edges(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(
        root,
        body=(
            "# Root\n\n"
            "[Search](?view=compact)\n"
            "[Guide query](guide.md?view=compact)\n"
            "[Anchor](#details?view=compact)\n"
        ),
    )
    (root / "guide.md").write_text("# Guide\n", encoding="utf-8")
    context = root_at(root)
    assert context is not None

    observations = tree_observations(context)

    assert [link.is_file_link for link in observations.links] == [False, False, True]
    assert [link.target for link in observations.links] == [None, None, root / "index.md"]
    assert any(
        item["code"] == "path_unreachable" and item["path"] == str(root / "guide.md")
        for item in validate(root)["findings"]
    )


def test_tree_observations_preserve_boundary_unsafe_and_symlink_scan(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(
        root,
        config="""  boundary-set:
    - path: boundary
  unsafe:
    - path: unsafe
""",
        body="# Root\n",
    )
    for name in ("boundary", "unsafe", "payload"):
        (root / name).mkdir()
    (root / "boundary" / "guide.md").write_text("# Boundary\n", encoding="utf-8")
    (root / "unsafe" / "guide.md").write_text("# Unsafe\n", encoding="utf-8")
    (root / "payload" / "nested.md").write_text("# Payload\n", encoding="utf-8")
    link = root / "payload-link"
    try:
        link.symlink_to(root / "payload", target_is_directory=True)
    except OSError:
        pytest.skip("This environment cannot create directory symlinks")

    context = root_at(root)
    assert context is not None
    observations = tree_observations(context, excluded_roots=[root / "payload"])
    assert link in observations.paths
    assert root / "payload" in observations.paths
    assert root / "payload" / "nested.md" not in observations.paths
    assert observations.is_within_boundary(root / "boundary" / "guide.md") is True
    assert observations.is_unsafe(root / "unsafe" / "guide.md") is True

    safe_observations = tree_observations(
        context,
        excluded_roots=[root / "payload"],
        excluded_configuration_fields=("boundary-set", "unsafe"),
    )
    assert root / "boundary" in safe_observations.paths
    assert root / "unsafe" in safe_observations.paths
    assert root / "boundary" / "guide.md" not in safe_observations.paths
    assert root / "unsafe" / "guide.md" not in safe_observations.paths


def test_validator_keeps_symlink_entries_without_scanning_their_targets(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_root(root, body="# Root\n\n[Linked](linked)\n[Linked document](linked-document.md)\n")
    external = tmp_path / "external"
    external.mkdir()
    (external / "index.md").write_text("not a doctidex index\n", encoding="utf-8")
    (external / "unreachable.md").write_text("# Unreachable\n", encoding="utf-8")
    (external / "linked-document.md").write_text("[Outside](../../outside.md)\n", encoding="utf-8")
    linked = root / "linked"
    linked_document = root / "linked-document.md"
    try:
        linked.symlink_to(external, target_is_directory=True)
        linked_document.symlink_to(external / "linked-document.md")
    except OSError:
        pytest.skip("This environment cannot create directory symlinks")

    observations = tree_observations(root_at(root))
    scoped = validate(root, scopes=["/linked"])

    assert linked in observations.paths
    assert linked / "index.md" not in observations.paths
    assert linked / "unreachable.md" not in observations.paths
    assert linked_document in observations.paths
    assert linked_document not in observations.markdown
    assert scoped["protocol_structure"] == "pass"
    assert scoped["scan_complete"] is True
