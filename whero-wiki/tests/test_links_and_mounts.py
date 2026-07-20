from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from whero_wiki_tools.links import (  # noqa: E402
    inbound_links,
    inspect_document_links,
    inspect_wiki_links,
    markdown_destinations,
    normalization_suggestions,
)
from whero_wiki_tools.mounts import discover_mounts, walk_owned_files  # noqa: E402


WIKI_META = """---
type: Whero Wiki
whero_wiki: true
whero_maintenance: true
whero_scope_required: true
---

# Wiki
"""


class LinkAndMountTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "wiki"
        self.root.mkdir()
        (self.root / "whero-wiki-meta.md").write_text(WIKI_META, encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_markdown_parser_skips_code_and_supports_reference_links(self) -> None:
        body = """[inline](a.md)

[reference][target]

```markdown
[not a link](ignored.md)
```

`[also ignored](code.md)`

[target]: b.md
"""

        self.assertEqual(markdown_destinations(body), ["a.md", "b.md"])

    def test_clear_hostname_with_path_is_external(self) -> None:
        source = self.write("source.md", "[Guide](docs.example.com/guide)\n")

        references = inspect_document_links(self.root, source)

        self.assertEqual(references[0].status, "external")
        self.assertEqual(references[0].kind, "external")

    def test_arbitrary_hostname_tld_is_external_but_markdown_file_is_local(self) -> None:
        source = self.write(
            "source.md",
            "[Guide](docs.example.tech/guide)\n"
            "[Markdown](foo.md)\n"
            "[Python](module.py)\n"
            "[Config](config.yaml)\n",
        )
        self.write("foo.md", "# Local\n")
        self.write("module.py", "value = 1\n")
        self.write("config.yaml", "value: 1\n")

        references = inspect_document_links(self.root, source)

        self.assertEqual(references[0].status, "external")
        self.assertEqual(
            [reference.status for reference in references[1:]],
            ["resolved", "resolved", "resolved"],
        )
        self.assertEqual(
            [reference.target for reference in references[1:]],
            ["foo.md", "module.py", "config.yaml"],
        )

    def test_query_is_not_part_of_local_target_path(self) -> None:
        self.write("target.md", "# Details\n")
        source = self.write(
            "source.md",
            "[Target](target.md?view=compact#details)\n",
        )

        references = inspect_document_links(self.root, source)

        self.assertEqual(references[0].status, "resolved")
        self.assertEqual(references[0].target, "target.md")
        self.assertEqual(references[0].anchor, "details")

    def test_self_link_does_not_define_its_own_anchor(self) -> None:
        source = self.write("source.md", "[Broken](#missing)\n")

        references = inspect_document_links(self.root, source)

        self.assertEqual(references[0].status, "anchor-missing")

    def test_html_anchor_is_resolved(self) -> None:
        target = self.write(
            "target.md",
            '<a id="explicit"></a>\n<a name="legacy"></a>\n',
        )
        source = self.write(
            "source.md",
            "[Explicit](target.md#explicit)\n[Legacy](target.md#legacy)\n",
        )

        references = inspect_document_links(self.root, source)

        self.assertTrue(target.is_file())
        self.assertEqual([item.status for item in references], ["resolved", "resolved"])

    def test_fenced_heading_does_not_define_anchor_and_duplicates_are_numbered(self) -> None:
        self.write(
            "target.md",
            "# Repeat\n\n# Repeat\n\n```markdown\n# Fenced\n```\n",
        )
        source = self.write(
            "source.md",
            "[Second](target.md#repeat-1)\n[Fenced](target.md#fenced)\n",
        )

        references = inspect_document_links(self.root, source)

        self.assertEqual(references[0].status, "resolved")
        self.assertEqual(references[1].status, "anchor-missing")

    def test_frontmatter_does_not_define_links_or_anchors(self) -> None:
        self.write(
            "target.md",
            "---\ntitle: Metadata\n---\n\n# Actual\n",
        )
        source = self.write(
            "source.md",
            "---\ndescription: '[Metadata](ignored.md)'\n---\n\n"
            "[Actual](target.md#actual)\n"
            "[Metadata](target.md#title-metadata)\n",
        )

        references = inspect_document_links(self.root, source)

        self.assertEqual(len(references), 2)
        self.assertEqual(references[0].status, "resolved")
        self.assertEqual(references[1].status, "anchor-missing")

    def test_leading_horizontal_rules_are_not_treated_as_frontmatter(self) -> None:
        self.write("target.md", "# Target\n")
        source = self.write(
            "source.md",
            "---\nordinary prose\n---\n\n[Target](target.md)\n",
        )

        references = inspect_document_links(self.root, source)

        self.assertEqual(len(references), 1)
        self.assertEqual(references[0].status, "resolved")

    def test_whero_rooted_link_and_inbound_query(self) -> None:
        target = self.write("concepts/model.md", "# Model\n")
        source = self.write(
            "deep/a/b/c/d/source.md",
            "[Model](whero-wiki:/concepts/model.md)\n",
        )

        references = inspect_document_links(self.root, source)
        inbound = inbound_links(self.root, "concepts/model.md")

        self.assertEqual(references[0].status, "resolved")
        self.assertEqual(references[0].kind, "whero-rooted")
        self.assertEqual(references[0].target, "concepts/model.md")
        self.assertEqual([item.source for item in inbound], [source.relative_to(self.root).as_posix()])

    def test_deep_relative_link_gets_normalization_suggestion(self) -> None:
        self.write("model.md", "# Model\n")
        self.write(
            "a/b/c/d/source.md",
            "[Model](../../../../model.md)\n",
        )

        suggestions = normalization_suggestions(self.root)

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["replacement"], "whero-wiki:/model.md")

    def test_nested_wiki_is_an_ownership_boundary(self) -> None:
        self.write("outer.md", "# Outer\n")
        nested = self.root / "references" / "nested"
        nested.mkdir(parents=True)
        (nested / "whero-wiki-meta.md").write_text(WIKI_META, encoding="utf-8")
        (nested / "inner.md").write_text("# Inner\n", encoding="utf-8")

        mounts = discover_mounts(self.root)
        owned = {path.relative_to(self.root).as_posix() for path in walk_owned_files(self.root)}

        self.assertEqual([(mount.kind, mount.path.as_posix()) for mount in mounts], [("whero-wiki", "references/nested")])
        self.assertIn("outer.md", owned)
        self.assertNotIn("references/nested/inner.md", owned)

    def test_whero_rooted_link_inside_nested_wiki_uses_nested_root(self) -> None:
        nested = self.root / "references" / "nested"
        nested.mkdir(parents=True)
        (nested / "whero-wiki-meta.md").write_text(WIKI_META, encoding="utf-8")
        (nested / "target.md").write_text("# Nested Target\n", encoding="utf-8")
        source = nested / "docs" / "source.md"
        source.parent.mkdir()
        source.write_text("[Target](whero-wiki:/target.md)\n", encoding="utf-8")

        references = inspect_document_links(self.root, source, mounts=discover_mounts(self.root))

        self.assertEqual(references[0].status, "resolved")
        self.assertEqual(references[0].target, "references/nested/target.md")

    def test_partial_missing_target_is_unavailable(self) -> None:
        source = self.write("source.md", "[Missing](missing.md)\n")

        references = inspect_document_links(self.root, source, available=True)

        self.assertEqual(references[0].status, "unavailable")

    def test_partial_directory_symlink_uses_preserved_logical_paths(self) -> None:
        self.write("docs/source.md", "[Target](target.md)\n")
        self.write("docs/target.md", "# Target\n")
        view = self.root.parent / "partial"
        view.mkdir()
        (view / "whero-wiki-meta.md").symlink_to(
            os.path.relpath(self.root / "whero-wiki-meta.md", start=view)
        )
        (view / "docs").symlink_to(
            os.path.relpath(self.root / "docs", start=view),
            target_is_directory=True,
        )
        (view / "partial-disclosure.md").write_text(
            """---
whero_maintenance: true
whero_scope_required: true
whero_partial_disclosure: true
---
""",
            encoding="utf-8",
        )

        references = inspect_wiki_links(view, available=True)

        link = next(item for item in references if item.source == "docs/source.md")
        self.assertEqual(link.target, "docs/target.md")
        self.assertEqual(link.status, "resolved")

    def test_link_and_mount_cli_auto_detect_partial_disclosure(self) -> None:
        view = self.root.parent / "partial-cli"
        view.mkdir()
        (view / "whero-wiki-meta.md").symlink_to(
            os.path.relpath(self.root / "whero-wiki-meta.md", start=view)
        )
        (view / "partial-disclosure.md").write_text(
            "---\nwhero_partial_disclosure: true\n---\n",
            encoding="utf-8",
        )
        script = SCRIPTS / "whero_wiki.py"

        links = subprocess.run(
            [sys.executable, str(script), "links", "list", "--wiki", str(view)],
            capture_output=True,
            text=True,
            check=False,
        )
        mounts = subprocess.run(
            [sys.executable, str(script), "mounts", "--wiki", str(view)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(links.returncode, 0, links.stderr)
        self.assertEqual(mounts.returncode, 0, mounts.stderr)

    def test_git_submodule_is_a_mount_even_without_whero_meta(self) -> None:
        repository = self.root.parent / "repository"
        repository.mkdir()
        source_repository = self.root.parent / "submodule-source"
        source_repository.mkdir()
        self.git(source_repository, "init", "-q")
        self.git(source_repository, "config", "user.name", "Test User")
        self.git(source_repository, "config", "user.email", "test@example.com")
        (source_repository / "source.md").write_text("# Source\n", encoding="utf-8")
        self.git(source_repository, "add", "source.md")
        self.git(source_repository, "commit", "-qm", "initial")
        self.git(repository, "init", "-q")
        self.git(repository, "config", "protocol.file.allow", "always")
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "-q",
                str(source_repository),
                "vendor",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        (repository / "whero-wiki-meta.md").write_text(WIKI_META, encoding="utf-8")
        self.git(repository, "add", ".")
        self.git(repository, "commit", "-qm", "add submodule")

        mounts = discover_mounts(repository)

        self.assertEqual(len(mounts), 1)
        self.assertEqual(mounts[0].kind, "submodule")
        self.assertTrue(mounts[0].submodule)
        self.assertEqual(mounts[0].path.as_posix(), "vendor")
        self.assertIsNotNone(mounts[0].git_commit)

    def test_link_cli_returns_json_graph(self) -> None:
        self.write("target.md", "# Target\n")
        self.write("source.md", "[Target](target.md)\n")
        script = SCRIPTS / "whero_wiki.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "links",
                "graph",
                "--wiki",
                str(self.root),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        graph = json.loads(result.stdout)
        edge = next(item for item in graph if item["source"] == "source.md")
        self.assertEqual(edge["target"], "target.md")
        self.assertEqual(edge["status"], "resolved")

    def git(self, directory: Path, *arguments: str) -> None:
        result = subprocess.run(
            ["git", "-C", str(directory), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
