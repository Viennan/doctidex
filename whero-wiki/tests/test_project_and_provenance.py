from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from whero_wiki_tools.frontmatter import write_markdown_atomic  # noqa: E402
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
        for directory in ("user", "design", "impl", "references"):
            self.assertFalse((self.root / directory).exists())
        diagnostics = validate_wiki(self.root, mode="full")
        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())

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


if __name__ == "__main__":
    unittest.main()
