from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from whero_wiki_tools.frontmatter import read_markdown, write_markdown_atomic  # noqa: E402
from whero_wiki_tools.git import changed_paths, sanitize_remote_url  # noqa: E402
from whero_wiki_tools.project import init_project_wiki  # noqa: E402
from whero_wiki_tools.provenance import affected_concepts  # noqa: E402
from whero_wiki_tools.curated import validate_wiki  # noqa: E402


class ProjectAndProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "project"
        self.root.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def link_from_root_index(self, destination: str, label: str = "Knowledge") -> None:
        index = self.root / "index.md"
        document = read_markdown(index)
        write_markdown_atomic(
            index,
            document.fields,
            document.body.rstrip() + f"\n\n[{label}]({destination})\n",
            overwrite=True,
        )

    def write_project_concept(
        self,
        provenance: list[dict[str, str]],
        *,
        relative: str = "docs/design/runtime.md",
    ) -> Path:
        concept = self.root / relative
        fields = {
            "type": "Design Model",
            "title": "Runtime",
            "description": "Runtime design model.",
            "whero_maintenance": True,
            "whero_curated": True,
            "curation_mode": "adapted",
            "curation_status": "reviewed",
            "provenance": provenance,
            "timestamp": "2026-07-20",
        }
        write_markdown_atomic(concept, fields, "\n# Runtime\n")
        self.link_from_root_index(relative, "Runtime")
        return concept

    def init_git_repository(self) -> None:
        subprocess.run(
            ["git", "init", "-q", str(self.root)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.name", "Test User"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.email", "test@example.com"],
            check=True,
        )

    def test_init_project_wiki_creates_no_empty_knowledge_directories(self) -> None:
        paths = init_project_wiki(
            self.root,
            "Example Project",
            "Project design and implementation knowledge.",
            agent_guide=Path("AGENTS.whero.md"),
        )

        self.assertEqual(len(paths), 4)
        self.assertTrue((self.root / "whero-wiki-meta.md").is_file())
        self.assertTrue((self.root / "index.md").is_file())
        self.assertTrue((self.root / "log.md").is_file())
        self.assertTrue((self.root / "AGENTS.whero.md").is_file())
        self.assertIn(
            "Keep curated knowledge under root `docs/` by default",
            (self.root / "AGENTS.whero.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "Create curated knowledge under root `docs/` by default",
            (self.root / "index.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "`docs/requirements`",
            (self.root / "index.md").read_text(encoding="utf-8"),
        )
        guide = (self.root / "AGENTS.whero.md").read_text(encoding="utf-8")
        self.assertIn("`docs/requirements`", guide)
        self.assertIn("label superseded, rejected, and version-bound", guide)
        self.assertIn("`whero_preserved_paths`", guide)
        self.assertIn(
            "`whero_preserved_paths`",
            (self.root / "index.md").read_text(encoding="utf-8"),
        )
        for directory in ("user", "requirements", "design", "impl", "references"):
            self.assertFalse((self.root / "docs" / directory).exists())
        diagnostics = validate_wiki(self.root, mode="full")
        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())

    def test_project_agent_guide_must_stay_inside_project_root(self) -> None:
        with self.assertRaisesRegex(ValueError, "inside the project root"):
            init_project_wiki(
                self.root,
                "Example Project",
                "Project knowledge.",
                agent_guide=Path("../outside.md"),
            )

    def test_repository_path_maps_git_change_to_concept(self) -> None:
        init_project_wiki(
            self.root,
            "Example Project",
            "Project design and implementation knowledge.",
        )
        source = self.root / "src" / "runtime.py"
        source.parent.mkdir()
        source.write_text("def run():\n    return 1\n", encoding="utf-8")
        concept = self.root / "docs" / "impl" / "python" / "runtime.md"
        fields = {
            "type": "Implementation Model",
            "title": "Runtime",
            "description": "Runtime implementation map.",
            "whero_maintenance": True,
            "whero_curated": True,
            "curation_mode": "adapted",
            "curation_status": "reviewed",
            "provenance": [
                {"kind": "repository-path", "path": "src/runtime.py"}
            ],
            "timestamp": "2026-07-18",
        }
        write_markdown_atomic(concept, fields, "\n# Runtime\n")
        index_fields = {
            "type": "Whero Wiki Index",
            "title": "Python Implementation",
            "description": "Python implementation concepts.",
            "whero_maintenance": True,
            "whero_scope_required": True,
        }
        write_markdown_atomic(
            self.root / "docs" / "impl" / "python" / "index.md",
            index_fields,
            "\n# Python Implementation\n\n[Runtime](runtime.md)\n",
        )
        self.link_from_root_index("docs/impl/python/", "Python Implementation")

        affected = affected_concepts(
            self.root,
            self.root,
            [PurePosixPath("src/runtime.py")],
        )

        self.assertEqual(len(affected), 1)
        self.assertEqual(affected[0].concept, "docs/impl/python/runtime.md")
        self.assertEqual(affected[0].provenance_kind, "repository-path")

        diagnostics = validate_wiki(self.root, mode="full")
        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertFalse(
            any(item.code == "CURATED_DEPTH" for item in diagnostics.items),
            diagnostics.render_text(),
        )

    def test_project_concept_requires_maintained_index_coverage(self) -> None:
        init_project_wiki(
            self.root,
            "Example Project",
            "Project design and implementation knowledge.",
        )
        source = self.root / "src" / "runtime.py"
        source.parent.mkdir()
        source.write_text("def run():\n    return 1\n", encoding="utf-8")
        fields = {
            "type": "Implementation Model",
            "title": "Runtime",
            "description": "Runtime implementation map.",
            "whero_maintenance": True,
            "whero_curated": True,
            "curation_mode": "adapted",
            "curation_status": "reviewed",
            "provenance": [
                {"kind": "repository-path", "path": "src/runtime.py"}
            ],
            "timestamp": "2026-07-18",
        }
        write_markdown_atomic(
            self.root / "docs" / "impl" / "python" / "runtime.md",
            fields,
            "\n# Runtime\n",
        )

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertTrue(diagnostics.has_errors)
        self.assertIn("CURATED_INDEX_COVERAGE", diagnostics.render_text())

    def test_isolated_nested_index_does_not_provide_project_coverage(self) -> None:
        init_project_wiki(
            self.root,
            "Example Project",
            "Project design and implementation knowledge.",
        )
        source = self.root / "src" / "runtime.py"
        source.parent.mkdir()
        source.write_text("def run():\n    return 1\n", encoding="utf-8")
        concept_fields = {
            "type": "Implementation Model",
            "title": "Runtime",
            "description": "Runtime implementation map.",
            "whero_maintenance": True,
            "whero_curated": True,
            "curation_mode": "adapted",
            "curation_status": "reviewed",
            "provenance": [{"kind": "repository-path", "path": "src/runtime.py"}],
            "timestamp": "2026-07-18",
        }
        write_markdown_atomic(
            self.root / "docs" / "impl" / "python" / "runtime.md",
            concept_fields,
            "\n# Runtime\n",
        )
        index_fields = {
            "type": "Whero Wiki Index",
            "title": "Python Implementation",
            "description": "Python implementation concepts.",
            "whero_maintenance": True,
            "whero_scope_required": True,
        }
        write_markdown_atomic(
            self.root / "docs" / "impl" / "python" / "index.md",
            index_fields,
            "\n# Python Implementation\n\n[Runtime](runtime.md)\n",
        )

        diagnostics = validate_wiki(self.root, mode="full")

        rendered = diagnostics.render_text()
        self.assertIn("INDEX_UNREACHABLE", rendered)
        self.assertIn("CURATED_INDEX_COVERAGE", rendered)

    def test_owned_index_requires_framework_frontmatter(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        nested = self.root / "docs" / "index.md"
        nested.parent.mkdir()
        nested.write_text("# Documentation\n", encoding="utf-8")
        self.link_from_root_index("docs/", "Documentation")

        diagnostics = validate_wiki(self.root, mode="full")

        rendered = diagnostics.render_text()
        self.assertIn("FRAMEWORK_TYPE", rendered)
        self.assertIn("FRAMEWORK_MAINTENANCE", rendered)
        self.assertIn("FRAMEWORK_SCOPE_REQUIRED", rendered)

    def test_framework_heading_in_fenced_code_does_not_count(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        index = self.root / "index.md"
        document = read_markdown(index)
        write_markdown_atomic(
            index,
            document.fields,
            "\n```markdown\n# Example Project\n```\n",
            overwrite=True,
        )

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertIn("FRAMEWORK_HEADING", diagnostics.render_text())

    def test_log_requires_framework_flags(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        log = self.root / "log.md"
        document = read_markdown(log)
        fields = dict(document.fields)
        fields.pop("whero_maintenance")
        write_markdown_atomic(log, fields, document.body, overwrite=True)

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertIn("FRAMEWORK_MAINTENANCE", diagnostics.render_text())

    def test_log_requires_iso_dates_in_newest_first_order(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        log = self.root / "log.md"
        document = read_markdown(log)
        write_markdown_atomic(
            log,
            document.fields,
            "\n# Example Project Knowledge Log\n\n## 2026-07-01\n\n- Older.\n"
            "\n## 2026-07-20\n\n- Newer.\n",
            overwrite=True,
        )

        order_diagnostics = validate_wiki(self.root, mode="full")

        self.assertIn("LOG_DATE_ORDER", order_diagnostics.render_text())

        write_markdown_atomic(
            log,
            document.fields,
            "\n# Example Project Knowledge Log\n\n## July 20, 2026\n\n- Invalid.\n",
            overwrite=True,
        )
        date_diagnostics = validate_wiki(self.root, mode="full")
        self.assertIn("LOG_DATE_HEADING", date_diagnostics.render_text())

    def test_git_revision_requires_a_real_commit(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        self.init_git_repository()
        self.write_project_concept(
            [{"kind": "git-revision", "repository": ".", "commit": "deadbeef"}]
        )

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertIn("CURATED_PROVENANCE_COMMIT", diagnostics.render_text())

    def test_repository_path_git_commit_requires_a_real_commit(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        self.init_git_repository()
        source = self.root / "src" / "runtime.py"
        source.parent.mkdir()
        source.write_text("def run():\n    return 1\n", encoding="utf-8")
        self.write_project_concept(
            [
                {
                    "kind": "repository-path",
                    "path": "src/runtime.py",
                    "git_commit": "deadbeef",
                }
            ]
        )

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertIn("CURATED_PROVENANCE_COMMIT", diagnostics.render_text())

    def test_available_repository_commit_unavailability_is_a_notice(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        source = self.root / "src" / "runtime.py"
        source.parent.mkdir()
        source.write_text("def run():\n    return 1\n", encoding="utf-8")
        self.write_project_concept(
            [
                {
                    "kind": "repository-path",
                    "path": "src/runtime.py",
                    "git_commit": "deadbeef",
                }
            ]
        )

        diagnostics = validate_wiki(self.root, mode="available")

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertIn(
            "CURATED_PROVENANCE_COMMIT_UNAVAILABLE",
            diagnostics.render_text(),
        )

    def test_stable_reference_must_exist_and_be_maintained(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        self.write_project_concept(
            [{"kind": "discussion", "reference": "docs/design/decision.md"}]
        )

        full = validate_wiki(self.root, mode="full")
        available = validate_wiki(self.root, mode="available")

        self.assertIn("CURATED_PROVENANCE_MISSING", full.render_text())
        self.assertFalse(available.has_errors, available.render_text())
        self.assertIn("CURATED_PROVENANCE_UNAVAILABLE", available.render_text())

        reference = self.root / "docs" / "design" / "decision.md"
        reference.write_text("# Decision\n", encoding="utf-8")
        unmaintained = validate_wiki(self.root, mode="full")
        self.assertIn(
            "CURATED_PROVENANCE_REFERENCE_MAINTENANCE",
            unmaintained.render_text(),
        )

    def test_stable_reference_accepts_maintained_record(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        record_fields = {
            "type": "Decision Record",
            "title": "Runtime Decision",
            "whero_maintenance": True,
        }
        write_markdown_atomic(
            self.root / "docs" / "design" / "decision.md",
            record_fields,
            "\n# Runtime Decision\n",
        )
        self.write_project_concept(
            [
                {"kind": "discussion", "reference": "docs/design/decision.md"},
                {"kind": "user-authored", "reference": "docs/design/decision.md"},
            ]
        )

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())

    def test_provenance_symlink_cannot_escape_wiki_root(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        outside = self.root.parent / "outside.py"
        outside.write_text("outside\n", encoding="utf-8")
        source = self.root / "src" / "runtime.py"
        source.parent.mkdir()
        source.symlink_to(outside)
        self.write_project_concept(
            [{"kind": "repository-path", "path": "src/runtime.py"}]
        )

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertIn("CURATED_PROVENANCE_PATH", diagnostics.render_text())

    def test_available_view_accepts_disclosed_provenance_symlinks(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        record_fields = {
            "type": "Decision Record",
            "title": "Runtime Decision",
            "whero_maintenance": True,
        }
        write_markdown_atomic(
            self.root / "docs" / "design" / "decision.md",
            record_fields,
            "\n# Runtime Decision\n",
        )
        self.write_project_concept(
            [{"kind": "discussion", "reference": "docs/design/decision.md"}]
        )
        view = self.root.parent / "partial"
        view.mkdir()
        for name in ("whero-wiki-meta.md", "index.md", "log.md"):
            (view / name).symlink_to(os.path.relpath(self.root / name, start=view))
        (view / "docs").symlink_to(
            os.path.relpath(self.root / "docs", start=view),
            target_is_directory=True,
        )
        (view / "partial-disclosure.md").write_text(
            "---\nwhero_partial_disclosure: true\n---\n",
            encoding="utf-8",
        )

        diagnostics = validate_wiki(view, mode="available")

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())

    def test_changed_paths_and_affected_include_renamed_source_path(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        self.init_git_repository()
        source = self.root / "src" / "old.py"
        source.parent.mkdir()
        source.write_text("value = 1\n", encoding="utf-8")
        self.write_project_concept(
            [{"kind": "repository-path", "path": "src/old.py"}]
        )
        subprocess.run(
            ["git", "-C", str(self.root), "add", "."],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-qm", "initial"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "mv", "src/old.py", "src/new.py"],
            check=True,
        )

        changed = changed_paths(self.root, "HEAD")
        affected = affected_concepts(self.root, self.root, changed)

        self.assertEqual(
            {path.as_posix() for path in changed},
            {"src/old.py", "src/new.py"},
        )
        self.assertEqual(len(affected), 1)
        self.assertEqual(affected[0].changed_path, "src/old.py")

    def test_affected_includes_user_authored_reference(self) -> None:
        init_project_wiki(self.root, "Example Project", "Project knowledge.")
        self.write_project_concept(
            [
                {
                    "kind": "user-authored",
                    "reference": "docs/requirements/runtime.md",
                }
            ]
        )

        affected = affected_concepts(
            self.root,
            self.root,
            [PurePosixPath("docs/requirements/runtime.md")],
        )

        self.assertEqual(len(affected), 1)
        self.assertEqual(affected[0].provenance_kind, "user-authored")

    def test_remote_sanitization_removes_credentials_and_url_metadata(self) -> None:
        self.assertEqual(
            sanitize_remote_url(
                "https://user:secret@example.com/org/wiki.git?token=abc#branch"
            ),
            "https://example.com/org/wiki.git",
        )
        self.assertEqual(
            sanitize_remote_url(
                "ssh://deploy:secret@example.com:2222/org/wiki.git?mode=fetch"
            ),
            "ssh://example.com:2222/org/wiki.git",
        )
        self.assertEqual(
            sanitize_remote_url("git@example.com:org/wiki.git?token=abc#main"),
            "example.com:org/wiki.git",
        )
        self.assertEqual(
            sanitize_remote_url("user:secret@example.com:org/wiki.git"),
            "example.com:org/wiki.git",
        )


if __name__ == "__main__":
    unittest.main()
