from __future__ import annotations

from pathlib import Path

from whero.doctidex.protocol.document import DoctidexDocument
from whero.doctidex.protocol.paths import normalize_internal_path, validate_mount_path
from whero.doctidex.protocol.regex import DoctidexPattern
from whero.doctidex.protocol.tree import RootContext
from whero.doctidex.protocol.validation import validate_protocol


def test_mount_namespace_normalization() -> None:
    assert (
        normalize_internal_path("/.doctidex/mounts/a/guide/.doctidex/mounts/b/index.md")
        == "/.doctidex/mounts/b/index.md"
    )
    assert validate_mount_path("/.doctidex/mounts/source") == "/.doctidex/mounts/source"


def test_regex_version1_utf_search() -> None:
    pattern = DoctidexPattern(r"(^|/)知识(?:/|$)")
    assert pattern.search("guide/知识/index.md")
    assert not pattern.search("guide/knowledge/index.md")


def test_round_trip_yaml_and_markdown_links(tmp_path: Path) -> None:
    path = tmp_path / "index.md"
    path.write_text(
        """---
type: index
custom: keep-me
doctidex:
  type: index
  root: true
  excludes:
    - path: .doctidex/mounts
---
# Root

[Guide](guide/index.md)
""",
        encoding="utf-8",
    )
    document = DoctidexDocument.load(path)
    document.doctidex["protected"] = [{"path": "vendor"}]
    document.write()
    reloaded = DoctidexDocument.load(path)
    assert reloaded.data["custom"] == "keep-me"
    assert reloaded.links()[0].target == "guide/index.md"


def test_validation_prunes_excluded_and_recurses_semantic_candidates(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "index.md").write_text(
        """---
type: index
doctidex:
  type: index
  root: true
  excludes:
    - path: .doctidex/mounts
    - path: ignored
---
# Root
""",
        encoding="utf-8",
    )
    (root / "guide").mkdir()
    (root / "guide" / "deep.md").write_text("deep\n", encoding="utf-8")
    (root / "ignored").mkdir()
    (root / "ignored" / "index.md").write_text("not frontmatter\n", encoding="utf-8")
    context = RootContext(root, DoctidexDocument.load(root / "index.md"))
    result = validate_protocol(context)
    candidate_paths = {item["path"] for item in result["semantic_candidates"]}
    assert result["protocol_structure"] == "pass"
    assert str(root / "guide" / "deep.md") in candidate_paths
    assert not any("ignored" in item.get("path", "") for item in result["findings"])


def test_malformed_child_index_and_atomic_document_are_findings(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "index.md").write_text(
        """---
type: index
doctidex:
  type: index
  root: true
  excludes:
    - path: .doctidex/mounts
  atomic_entries:
    - path: bundle
---
# Root
""",
        encoding="utf-8",
    )
    (root / "child").mkdir()
    (root / "child" / "index.md").write_text("broken\n", encoding="utf-8")
    (root / "bundle").mkdir()
    (root / "bundle" / "log.md").write_text("broken\n", encoding="utf-8")
    result = validate_protocol(RootContext(root, DoctidexDocument.load(root / "index.md")))
    codes = {item["code"] for item in result["findings"]}
    assert result["protocol_structure"] == "fail"
    assert "frontmatter_missing" in codes
    assert "atomic_document" in codes


def test_link_boundary_is_checked_in_plain_markdown(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    document = DoctidexDocument.new_root(root / "index.md")
    document.body = "[Plain](plain.md)\n"
    document.write()
    (root / "plain.md").write_text("[Escape](../../outside.md)\n", encoding="utf-8")
    result = validate_protocol(RootContext(root, DoctidexDocument.load(root / "index.md")))
    assert any(item["code"] == "link_path_escape" for item in result["findings"])
