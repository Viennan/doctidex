from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from whero_wiki_tools.curated import init_index, validate_wiki  # noqa: E402
from whero_wiki_tools.errors import WheroToolError  # noqa: E402
from whero_wiki_tools.frontmatter import write_markdown_atomic  # noqa: E402
from whero_wiki_tools.mounts import discover_boundaries, walk_owned_files  # noqa: E402


WIKI_META = """---
type: Whero Wiki
whero_wiki: true
whero_maintenance: true
whero_scope_required: true
---

# Wiki
"""


class PreservedPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "wiki"
        self.root.mkdir()
        (self.root / "whero-wiki-meta.md").write_text(WIKI_META, encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_root_index(self, paths: list[str]) -> None:
        write_markdown_atomic(
            self.root / "index.md",
            {
                "type": "Whero Wiki Index",
                "title": "Wiki",
                "description": "Wiki routes and preserved boundaries.",
                "whero_maintenance": True,
                "whero_scope_required": True,
                "whero_preserved_paths": paths,
            },
            "\n# Wiki\n",
        )

    def test_validation_and_owned_walk_do_not_enter_preserved_paths(self) -> None:
        self.write_root_index(["archive", "frozen.md"])
        archive = self.root / "archive"
        archive.mkdir()
        (archive / "index.md").write_text(
            "---\nwhero_curated_path: [invalid\n---\n",
            encoding="utf-8",
        )
        (archive / "broken.md").write_text(
            "---\nupstream: [invalid\n---\n\n[Missing](missing.md)\n",
            encoding="utf-8",
        )
        (self.root / "frozen.md").write_text("[Missing](missing.md)\n", encoding="utf-8")

        diagnostics = validate_wiki(self.root, mode="full")
        owned = {path.relative_to(self.root).as_posix() for path in walk_owned_files(self.root)}
        mounts, preserved, problems = discover_boundaries(self.root)

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertNotIn("archive/broken.md", owned)
        self.assertNotIn("frozen.md", owned)
        self.assertEqual(mounts, [])
        self.assertEqual([entry.path.as_posix() for entry in preserved], ["archive", "frozen.md"])
        self.assertEqual(problems, [])

    def test_owned_document_can_link_into_preserved_directory(self) -> None:
        self.write_root_index(["archive"])
        archive = self.root / "archive"
        archive.mkdir()
        (archive / "source.md").write_text("# Preserved Source\n", encoding="utf-8")
        write_markdown_atomic(
            self.root / "guide.md",
            {
                "type": "Guide",
                "title": "Guide",
                "whero_maintenance": True,
            },
            "\n# Guide\n\n[Preserved source](archive/source.md#preserved-source)\n",
        )

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())

    def test_validator_rejects_invalid_or_missing_preserved_paths(self) -> None:
        self.write_root_index(["missing", "../outside"])

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertTrue(diagnostics.has_errors)
        rendered = diagnostics.render_text()
        self.assertIn("PRESERVED_DECLARATION", rendered)
        self.assertIn("PRESERVED_MISSING", rendered)

    def test_available_mode_treats_undisclosed_preserved_path_as_unavailable(self) -> None:
        self.write_root_index(["archive"])
        (self.root / "partial-disclosure.md").write_text(
            "---\nwhero_partial_disclosure: true\n---\n",
            encoding="utf-8",
        )

        diagnostics = validate_wiki(self.root, mode="available")

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertTrue(any(item.code == "PRESERVED_UNAVAILABLE" for item in diagnostics.items))

    def test_partial_directory_symlink_discovers_nested_preserved_index(self) -> None:
        source = self.root.parent / "source"
        source.mkdir()
        (source / "whero-wiki-meta.md").write_text(WIKI_META, encoding="utf-8")
        provider = source / "provider"
        provider.mkdir()
        write_markdown_atomic(
            provider / "index.md",
            {
                "type": "Whero Wiki Index",
                "title": "Provider",
                "description": "Provider boundary.",
                "whero_maintenance": True,
                "whero_scope_required": True,
                "whero_preserved_paths": ["archive"],
            },
            "\n# Provider\n",
        )
        (provider / "archive").mkdir()
        (provider / "archive" / "broken.md").write_text(
            "[Missing](missing.md)\n",
            encoding="utf-8",
        )

        view = self.root.parent / "partial"
        view.mkdir()
        (view / "whero-wiki-meta.md").symlink_to(
            os.path.relpath(source / "whero-wiki-meta.md", start=view)
        )
        (view / "provider").symlink_to(
            os.path.relpath(provider, start=view),
            target_is_directory=True,
        )
        (view / "partial-disclosure.md").write_text(
            "---\nwhero_partial_disclosure: true\n---\n",
            encoding="utf-8",
        )

        diagnostics = validate_wiki(view, mode="available")
        _, preserved, problems = discover_boundaries(view)
        owned = {path.relative_to(view).as_posix() for path in walk_owned_files(view)}

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertEqual([entry.path.as_posix() for entry in preserved], ["provider/archive"])
        self.assertEqual(problems, [])
        self.assertNotIn("provider/archive/broken.md", owned)

    def test_maintenance_cannot_write_inside_preserved_or_mounted_roots(self) -> None:
        self.write_root_index(["archive"])
        (self.root / "archive" / "docs").mkdir(parents=True)

        with self.assertRaisesRegex(WheroToolError, "preserved boundary"):
            init_index(self.root, "archive/docs", "Archive", "Must remain untouched.")

        nested = self.root / "nested"
        (nested / "docs").mkdir(parents=True)
        (nested / "whero-wiki-meta.md").write_text(WIKI_META, encoding="utf-8")
        with self.assertRaisesRegex(WheroToolError, "mounted ownership boundary"):
            init_index(self.root, "nested/docs", "Nested", "Owned by the nested Wiki.")

    def test_preserved_root_hides_nested_mounts_from_outer_ownership(self) -> None:
        self.write_root_index(["vendor"])
        vendor = self.root / "vendor"
        vendor.mkdir()
        (vendor / "whero-wiki-meta.md").write_text(WIKI_META, encoding="utf-8")

        mounts, preserved, problems = discover_boundaries(self.root)

        self.assertEqual(mounts, [])
        self.assertEqual([entry.path.as_posix() for entry in preserved], ["vendor"])
        self.assertEqual(problems, [])

    def test_mounts_cli_lists_preserved_boundary(self) -> None:
        self.write_root_index(["archive"])
        (self.root / "archive").mkdir()
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "whero_wiki.py"),
                "mounts",
                "--wiki",
                str(self.root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("preserved: archive", result.stdout)


if __name__ == "__main__":
    unittest.main()
