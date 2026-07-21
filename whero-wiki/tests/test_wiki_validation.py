from __future__ import annotations

import os
from pathlib import Path

from support import (
    FORMAT_VERSION,
    WikiTestCase,
    create_wiki,
    framework_fields,
    read_markdown,
    wiki_meta_text,
    write_markdown_atomic,
    write_view_status,
)

from whero_wiki_tools.curated import (
    init_curated_collection,
    init_curated_concept,
    init_index,
    record_source_digests,
    validate_wiki,
)
from whero_wiki_tools.errors import WheroToolError
from whero_wiki_tools.model import (
    CURATED_FORMAT_VERSION,
    is_view_root,
    validate_wiki_root,
)
from whero_wiki_tools.project import init_project_wiki


class WikiIdentityTests(WikiTestCase):
    def test_v002_is_the_only_wiki_format_version(self) -> None:
        self.assertEqual(validate_wiki_root(self.root), self.root)

        meta = self.root / "whero-wiki-meta.md"
        for version in ("", "0.0.1", "0.0.3"):
            meta.write_text(wiki_meta_text(version=version), encoding="utf-8")
            with self.subTest(version=version), self.assertRaisesRegex(
                WheroToolError,
                "unsupported format_version",
            ):
                validate_wiki_root(self.root)

    def test_wiki_identity_requires_all_canonical_flags(self) -> None:
        meta = self.root / "whero-wiki-meta.md"
        for field in ("whero_wiki", "whero_maintenance", "whero_view_required"):
            text = wiki_meta_text().replace(f"{field}: true\n", "")
            meta.write_text(text, encoding="utf-8")
            with self.subTest(field=field), self.assertRaisesRegex(
                WheroToolError,
                field,
            ):
                validate_wiki_root(self.root)

    def test_view_identity_uses_one_status_file_and_exact_version(self) -> None:
        view = self.view_parent / "manual"
        view.mkdir()
        (view / "whero-wiki-meta.md").symlink_to(
            os.path.relpath(self.root / "whero-wiki-meta.md", start=view)
        )
        status = write_view_status(view, self.root)

        self.assertTrue(is_view_root(view))
        self.assertEqual(validate_wiki_root(view, allow_symlink_meta=True), view)

        document = read_markdown(status)
        fields = dict(document.fields)
        fields["format_version"] = "0.0.3"
        write_markdown_atomic(status, fields, document.body, overwrite=True)
        with self.assertRaisesRegex(WheroToolError, "format_version"):
            is_view_root(view)

    def test_unrecognized_status_filename_does_not_identify_a_view(self) -> None:
        view = self.view_parent / "unrecognized"
        view.mkdir()
        write_markdown_atomic(
            view / "view-state.md",
            {
                "type": "Whero Wiki View",
                "format_version": FORMAT_VERSION,
                "whero_view": True,
            },
            "\n# View\n",
        )

        self.assertFalse(is_view_root(view))

    def test_validation_profiles_are_auto_full_and_view(self) -> None:
        for mode in ("auto", "full"):
            with self.subTest(mode=mode):
                self.assertFalse(validate_wiki(self.root, mode=mode).has_errors)

        with self.assertRaisesRegex(WheroToolError, "unsupported validation mode"):
            validate_wiki(self.root, mode="snapshot")

    def test_project_initializer_writes_v002_identity(self) -> None:
        project = self.workspace / "project"
        project.mkdir()

        paths = init_project_wiki(
            project,
            "Example Project",
            "Project knowledge.",
            agent_guide=Path("AGENTS.whero.md"),
        )

        self.assertEqual(len(paths), 4)
        self.assertEqual(
            read_markdown(project / "whero-wiki-meta.md").fields["format_version"],
            FORMAT_VERSION,
        )
        self.assertEqual(
            read_markdown(project / "index.md").fields[
                "whero_curated_format_version"
            ],
            CURATED_FORMAT_VERSION,
        )
        self.assertFalse(validate_wiki(project, mode="full").has_errors)


class CuratedValidationTests(WikiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.provider = self.root / "provider"
        self.provider.mkdir()
        self.source = self.write(
            "provider/source.md",
            "# Source\n\nAuthoritative text.\n",
        )
        init_index(
            self.root,
            "provider",
            "Provider References",
            "Collected provider references and maintained knowledge.",
        )
        self.collection = init_curated_collection(
            self.root,
            "provider",
            "knowledge",
            "Provider Knowledge",
            "Concept-oriented provider knowledge.",
        )

    def create_indexed_concept(self, *, status: str = "reviewed") -> Path:
        concept = init_curated_concept(
            self.root,
            "provider/knowledge/model.md",
            "API Model",
            "Provider Model",
            "The provider's source-backed operating model.",
            "adapted",
            ["provider/source.md"],
            status=status,
        )
        document = read_markdown(concept)
        write_markdown_atomic(
            concept,
            document.fields,
            "\n# Provider Model\n\n[Source](../source.md)\n",
            overwrite=True,
        )
        self.append_index_link(self.collection / "index.md", "model.md", "Provider Model")
        return concept

    def test_curated_collection_and_concept_validate_as_v002(self) -> None:
        self.create_indexed_concept()

        fields = read_markdown(self.collection / "index.md").fields
        diagnostics = validate_wiki(self.root, mode="full")

        self.assertEqual(fields["whero_curated_format_version"], FORMAT_VERSION)
        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertEqual(diagnostics.items, [])

    def test_curated_collection_rejects_a_different_format_version(self) -> None:
        index = self.collection / "index.md"
        document = read_markdown(index)
        fields = dict(document.fields)
        fields["whero_curated_format_version"] = "0.0.3"
        write_markdown_atomic(index, fields, document.body, overwrite=True)

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertIn("CURATED_FORMAT_VERSION", diagnostics.render_text())

    def test_stale_source_is_warning_or_strict_error(self) -> None:
        self.create_indexed_concept()
        self.source.write_text("# Source\n\nChanged.\n", encoding="utf-8")

        normal = validate_wiki(self.root, mode="full")
        strict = validate_wiki(self.root, mode="full", strict_stale=True)

        self.assertFalse(normal.has_errors, normal.render_text())
        self.assertIn("CURATED_SOURCE_STALE", normal.render_text())
        self.assertTrue(strict.has_errors)

    def test_recording_reviewed_digests_clears_staleness(self) -> None:
        concept = self.create_indexed_concept(status="needs-review")
        self.source.write_text("# Source\n\nReviewed replacement.\n", encoding="utf-8")

        record_source_digests(
            self.root,
            concept.relative_to(self.root).as_posix(),
            status="reviewed",
        )

        diagnostics = validate_wiki(self.root, mode="full", strict_stale=True)
        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertNotIn("CURATED_SOURCE_STALE", diagnostics.render_text())

    def test_curated_concept_must_not_be_view_required(self) -> None:
        concept = self.create_indexed_concept()
        document = read_markdown(concept)
        fields = dict(document.fields)
        fields["whero_view_required"] = True
        write_markdown_atomic(concept, fields, document.body, overwrite=True)

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertIn("CURATED_VIEW_REQUIRED", diagnostics.render_text())

    def test_curated_concept_requires_reachable_index_coverage(self) -> None:
        concept = init_curated_concept(
            self.root,
            "provider/knowledge/unlisted.md",
            "API Model",
            "Unlisted",
            "Not routed by an index.",
            "adapted",
            ["provider/source.md"],
            status="reviewed",
        )
        self.assertTrue(concept.is_file())

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertIn("CURATED_INDEX_COVERAGE", diagnostics.render_text())

    def test_framework_documents_require_maintenance_and_view_flags(self) -> None:
        index = self.provider / "index.md"
        write_markdown_atomic(
            index,
            framework_fields("Whero Wiki Index", "Provider", whero_maintenance=False),
            "\n# Provider\n",
            overwrite=True,
        )

        diagnostics = validate_wiki(self.root, mode="full")

        rendered = diagnostics.render_text()
        self.assertIn("FRAMEWORK_MAINTENANCE", rendered)
        self.assertIn("VIEW_REQUIRED_MAINTENANCE", rendered)
