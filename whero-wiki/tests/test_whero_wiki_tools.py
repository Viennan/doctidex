from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from whero_wiki_tools.curated import (  # noqa: E402
    init_curated_collection,
    init_curated_concept,
    init_index,
    record_source_digests,
    validate_wiki,
)
from whero_wiki_tools.errors import WheroToolError  # noqa: E402
from whero_wiki_tools.frontmatter import (  # noqa: E402
    read_markdown,
    write_markdown_atomic,
)


WIKI_META = """---
type: Whero Wiki
whero_wiki: true
whero_maintenance: true
whero_scope_required: true
---

# Test Wiki
"""


class WheroWikiToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "wiki"
        self.root.mkdir()
        (self.root / "whero-wiki-meta.md").write_text(WIKI_META, encoding="utf-8")
        self.scope = self.root / "provider"
        self.scope.mkdir()
        self.source = self.scope / "source.md"
        self.source.write_text("# Source\n\nAuthoritative text.\n", encoding="utf-8")
        init_index(
            self.root,
            "provider",
            "Provider References",
            "Collected provider references and maintained knowledge.",
        )
        init_curated_collection(
            self.root,
            "provider",
            "agent-curated",
            "Agent-Curated Knowledge",
            "Concept-oriented provider knowledge.",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_indexed_concept(self, status: str = "reviewed") -> Path:
        concept = init_curated_concept(
            self.root,
            "provider/agent-curated/model.md",
            "API Model",
            "Provider Model",
            "The provider's source-backed operating model.",
            "adapted",
            ["provider/source.md"],
            status=status,
        )
        document = read_markdown(concept)
        body = (
            "\n# Provider Model\n\n"
            "The provider's source-backed operating model.\n\n"
            "See the [authoritative source](../source.md).\n"
        )
        write_markdown_atomic(concept, document.fields, body, overwrite=True)
        index = concept.parent / "index.md"
        index_document = read_markdown(index)
        index_body = index_document.body.rstrip() + (
            "\n\n## Concepts\n\n"
            "- [Provider Model](model.md) - The source-backed operating model.\n"
        )
        write_markdown_atomic(
            index,
            index_document.fields,
            index_body,
            overwrite=True,
        )
        return concept

    def test_initialize_and_validate_curated_collection(self) -> None:
        self.create_indexed_concept()

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertEqual(diagnostics.items, [])

    def test_stale_source_is_warning_or_strict_error(self) -> None:
        self.create_indexed_concept()
        self.source.write_text("# Source\n\nChanged text.\n", encoding="utf-8")

        normal = validate_wiki(self.root, mode="full")
        strict = validate_wiki(self.root, mode="full", strict_stale=True)

        self.assertFalse(normal.has_errors, normal.render_text())
        self.assertTrue(
            any(item.code == "CURATED_SOURCE_STALE" for item in normal.items)
        )
        self.assertTrue(strict.has_errors)

    def test_record_source_digests_clears_reviewed_staleness(self) -> None:
        concept = self.create_indexed_concept(status="needs-review")
        self.source.write_text("# Source\n\nReviewed replacement.\n", encoding="utf-8")

        record_source_digests(
            self.root,
            concept.relative_to(self.root).as_posix(),
            status="reviewed",
        )
        diagnostics = validate_wiki(self.root, mode="full", strict_stale=True)

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertFalse(
            any(item.code == "CURATED_SOURCE_STALE" for item in diagnostics.items)
        )

    def test_available_mode_tolerates_undisclosed_source(self) -> None:
        self.create_indexed_concept()
        self.source.unlink()
        (self.root / "partial-disclosure.md").write_text(
            "---\nwhero_partial_disclosure: true\n---\n",
            encoding="utf-8",
        )

        diagnostics = validate_wiki(self.root, mode="available")

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertTrue(
            any(item.code == "CURATED_SOURCE_UNAVAILABLE" for item in diagnostics.items)
        )

    def test_available_mode_accepts_symlinked_wiki_meta(self) -> None:
        partial = self.root.parent / "partial"
        partial.mkdir()
        (partial / "whero-wiki-meta.md").symlink_to(
            self.root / "whero-wiki-meta.md"
        )
        (partial / "partial-disclosure.md").write_text(
            "---\nwhero_partial_disclosure: true\n---\n",
            encoding="utf-8",
        )

        diagnostics = validate_wiki(partial, mode="available")

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())

    def test_concept_cannot_use_curated_source(self) -> None:
        first = self.create_indexed_concept()

        with self.assertRaisesRegex(WheroToolError, "collected source snapshots"):
            init_curated_concept(
                self.root,
                "provider/agent-curated/derived.md",
                "API Model",
                "Derived Model",
                "Invalid curated-to-curated provenance.",
                "synthesized",
                [first.relative_to(self.root).as_posix()],
            )

    def test_validator_rejects_scope_required_concept(self) -> None:
        concept = self.create_indexed_concept()
        document = read_markdown(concept)
        fields = dict(document.fields)
        fields["whero_scope_required"] = True
        write_markdown_atomic(concept, fields, document.body, overwrite=True)

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertTrue(diagnostics.has_errors)
        self.assertTrue(
            any(item.code == "CURATED_SCOPE_REQUIRED" for item in diagnostics.items)
        )

    def test_validator_requires_index_coverage(self) -> None:
        init_curated_concept(
            self.root,
            "provider/agent-curated/orphan.md",
            "Reference Model",
            "Orphan Concept",
            "A concept missing from curated navigation.",
            "adapted",
            ["provider/source.md"],
            status="reviewed",
        )

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertTrue(diagnostics.has_errors)
        self.assertTrue(
            any(item.code == "CURATED_INDEX_COVERAGE" for item in diagnostics.items)
        )

    def test_curated_depth_beyond_three_is_warning(self) -> None:
        concept = init_curated_concept(
            self.root,
            "provider/agent-curated/one/two/three/deep.md",
            "Reference Model",
            "Deep Concept",
            "A deliberately deep concept.",
            "adapted",
            ["provider/source.md"],
            status="reviewed",
        )
        document = read_markdown(concept)
        write_markdown_atomic(
            concept,
            document.fields,
            "\n# Deep Concept\n\nA deliberately deep concept.\n",
            overwrite=True,
        )
        index = concept.parents[3] / "index.md"
        index_document = read_markdown(index)
        write_markdown_atomic(
            index,
            index_document.fields,
            index_document.body.rstrip()
            + "\n\n- [Deep Concept](one/two/three/deep.md) - Deliberately deep.\n",
            overwrite=True,
        )

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertTrue(any(item.code == "CURATED_DEPTH" for item in diagnostics.items))


if __name__ == "__main__":
    unittest.main()
