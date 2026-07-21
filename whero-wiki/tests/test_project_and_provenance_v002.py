from __future__ import annotations

from pathlib import Path, PurePosixPath

from support import WikiTestCase, read_markdown, write_index, write_markdown_atomic

from whero_wiki_tools.curated import validate_wiki
from whero_wiki_tools.errors import WheroToolError
from whero_wiki_tools.git import changed_paths, sanitize_remote_url
from whero_wiki_tools.project import init_project_wiki
from whero_wiki_tools.provenance import affected_concepts


class ProjectKnowledgeTests(WikiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.project = self.workspace / "project"
        self.project.mkdir()

    def init_project(self) -> None:
        init_project_wiki(
            self.project,
            "Example Project",
            "Project design and implementation knowledge.",
        )

    def append_root_link(self, destination: str, label: str = "Knowledge") -> None:
        index = self.project / "index.md"
        document = read_markdown(index)
        write_markdown_atomic(
            index,
            document.fields,
            document.body.rstrip() + f"\n\n[{label}]({destination})\n",
            overwrite=True,
        )

    def write_concept(
        self,
        provenance: list[dict[str, str]],
        *,
        relative: str = "docs/design/runtime.md",
        indexed: bool = True,
    ) -> Path:
        concept = self.project / relative
        write_markdown_atomic(
            concept,
            {
                "type": "Design Model",
                "title": "Runtime",
                "description": "Runtime design model.",
                "whero_maintenance": True,
                "whero_curated": True,
                "curation_mode": "adapted",
                "curation_status": "reviewed",
                "provenance": provenance,
                "timestamp": "2026-07-21",
            },
            "\n# Runtime\n",
        )
        if indexed:
            self.append_root_link(relative, "Runtime")
        return concept

    def test_initializer_creates_framework_only_and_optional_agent_guide(self) -> None:
        paths = init_project_wiki(
            self.project,
            "Example Project",
            "Project knowledge.",
            agent_guide=Path("AGENTS.whero.md"),
        )

        self.assertEqual(len(paths), 4)
        self.assertTrue((self.project / "AGENTS.whero.md").is_file())
        self.assertIn(
            "Keep curated knowledge under root `docs/` by default",
            (self.project / "AGENTS.whero.md").read_text(encoding="utf-8"),
        )
        for directory in ("user", "requirements", "design", "impl", "references"):
            self.assertFalse((self.project / "docs" / directory).exists())
        self.assertFalse(validate_wiki(self.project, mode="full").has_errors)

    def test_agent_guide_must_remain_inside_project_root(self) -> None:
        with self.assertRaisesRegex(WheroToolError, "inside the project root"):
            init_project_wiki(
                self.project,
                "Example Project",
                "Project knowledge.",
                agent_guide=Path("../outside.md"),
            )

    def test_repository_path_maps_a_change_to_its_concept(self) -> None:
        self.init_project()
        source = self.project / "src" / "runtime.py"
        source.parent.mkdir()
        source.write_text("def run():\n    return 1\n", encoding="utf-8")
        self.write_concept(
            [{"kind": "repository-path", "path": "src/runtime.py"}],
            relative="docs/impl/python/runtime.md",
        )

        affected = affected_concepts(
            self.project,
            self.project,
            [PurePosixPath("src/runtime.py")],
        )

        self.assertEqual(len(affected), 1)
        self.assertEqual(affected[0].concept, "docs/impl/python/runtime.md")
        self.assertEqual(affected[0].provenance_kind, "repository-path")
        self.assertFalse(validate_wiki(self.project, mode="full").has_errors)

    def test_project_concept_requires_reachable_index_coverage(self) -> None:
        self.init_project()
        source = self.project / "src" / "runtime.py"
        source.parent.mkdir()
        source.write_text("value = 1\n", encoding="utf-8")
        self.write_concept(
            [{"kind": "repository-path", "path": "src/runtime.py"}],
            indexed=False,
        )

        diagnostics = validate_wiki(self.project, mode="full")

        self.assertIn("CURATED_INDEX_COVERAGE", diagnostics.render_text())

    def test_isolated_nested_index_does_not_make_concept_reachable(self) -> None:
        self.init_project()
        source = self.project / "src" / "runtime.py"
        source.parent.mkdir()
        source.write_text("value = 1\n", encoding="utf-8")
        self.write_concept(
            [{"kind": "repository-path", "path": "src/runtime.py"}],
            relative="docs/impl/runtime.md",
            indexed=False,
        )
        write_index(
            self.project / "docs" / "impl" / "index.md",
            title="Implementation",
            body="\n# Implementation\n\n[Runtime](runtime.md)\n",
        )

        diagnostics = validate_wiki(self.project, mode="full")

        rendered = diagnostics.render_text()
        self.assertIn("INDEX_UNREACHABLE", rendered)
        self.assertIn("CURATED_INDEX_COVERAGE", rendered)

    def test_framework_heading_and_log_date_rules_are_enforced(self) -> None:
        self.init_project()
        index = self.project / "index.md"
        index_document = read_markdown(index)
        write_markdown_atomic(
            index,
            index_document.fields,
            "\n```markdown\n# Example Project\n```\n",
            overwrite=True,
        )
        heading = validate_wiki(self.project, mode="full")
        self.assertIn("FRAMEWORK_HEADING", heading.render_text())

        write_markdown_atomic(
            index,
            index_document.fields,
            index_document.body,
            overwrite=True,
        )
        log = self.project / "log.md"
        log_document = read_markdown(log)
        write_markdown_atomic(
            log,
            log_document.fields,
            "\n# Example Project Knowledge Log\n\n"
            "## 2026-07-01\n\n- Older.\n\n"
            "## 2026-07-21\n\n- Newer.\n",
            overwrite=True,
        )
        ordering = validate_wiki(self.project, mode="full")
        self.assertIn("LOG_DATE_ORDER", ordering.render_text())

    def test_git_revision_requires_a_real_commit(self) -> None:
        self.init_project()
        self.init_git(self.project)
        self.write_concept(
            [{"kind": "git-revision", "repository": ".", "commit": "deadbeef"}]
        )

        diagnostics = validate_wiki(self.project, mode="full")

        self.assertIn("CURATED_PROVENANCE_COMMIT", diagnostics.render_text())

    def test_stable_reference_must_exist_and_be_maintained(self) -> None:
        self.init_project()
        self.write_concept(
            [{"kind": "discussion", "reference": "docs/design/decision.md"}]
        )

        full = validate_wiki(self.project, mode="full")
        view = validate_wiki(self.project, mode="view")
        self.assertIn("CURATED_PROVENANCE_MISSING", full.render_text())
        self.assertFalse(view.has_errors, view.render_text())
        self.assertIn("CURATED_PROVENANCE_UNAVAILABLE", view.render_text())

        reference = self.project / "docs" / "design" / "decision.md"
        reference.write_text("# Decision\n", encoding="utf-8")
        unmaintained = validate_wiki(self.project, mode="full")
        self.assertIn(
            "CURATED_PROVENANCE_REFERENCE_MAINTENANCE",
            unmaintained.render_text(),
        )

    def test_stable_reference_accepts_a_maintained_record(self) -> None:
        self.init_project()
        write_markdown_atomic(
            self.project / "docs" / "design" / "decision.md",
            {
                "type": "Decision Record",
                "title": "Runtime Decision",
                "whero_maintenance": True,
            },
            "\n# Runtime Decision\n",
        )
        self.write_concept(
            [
                {"kind": "discussion", "reference": "docs/design/decision.md"},
                {"kind": "user-authored", "reference": "docs/design/decision.md"},
            ]
        )

        diagnostics = validate_wiki(self.project, mode="full")

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())

    def test_provenance_symlink_cannot_escape_the_wiki(self) -> None:
        self.init_project()
        outside = self.workspace / "outside.py"
        outside.write_text("outside\n", encoding="utf-8")
        source = self.project / "src" / "runtime.py"
        source.parent.mkdir()
        source.symlink_to(outside)
        self.write_concept(
            [{"kind": "repository-path", "path": "src/runtime.py"}]
        )

        diagnostics = validate_wiki(self.project, mode="full")

        self.assertIn("CURATED_PROVENANCE_PATH", diagnostics.render_text())

    def test_git_rename_reports_both_paths_and_affects_old_reference(self) -> None:
        self.init_project()
        source = self.project / "src" / "old.py"
        source.parent.mkdir()
        source.write_text("value = 1\n", encoding="utf-8")
        self.write_concept(
            [{"kind": "repository-path", "path": "src/old.py"}]
        )
        self.init_git(self.project)
        self.commit_all(self.project, "initial")
        self.git(self.project, "mv", "src/old.py", "src/new.py")

        changed = changed_paths(self.project, "HEAD")
        affected = affected_concepts(self.project, self.project, changed)

        self.assertEqual(
            {path.as_posix() for path in changed},
            {"src/old.py", "src/new.py"},
        )
        self.assertEqual(affected[0].changed_path, "src/old.py")

    def test_remote_sanitization_removes_credentials_query_and_fragment(self) -> None:
        self.assertEqual(
            sanitize_remote_url(
                "https://user:secret@example.com/org/wiki.git?token=abc#branch"
            ),
            "https://example.com/org/wiki.git",
        )
