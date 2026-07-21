from __future__ import annotations

import json

from support import WikiTestCase, create_wiki, write_index, write_markdown_atomic

from whero_wiki_tools.curated import validate_wiki
from whero_wiki_tools.links import (
    inbound_links,
    inspect_document_links,
    inspect_wiki_links,
    markdown_destinations,
)
from whero_wiki_tools.mounts import discover_mounts, walk_owned_files


class MarkdownLinkParsingTests(WikiTestCase):
    def test_parser_skips_code_and_supports_reference_links(self) -> None:
        body = (
            "[Inline](a.md) and [Reference][ref].\n\n"
            "`[Code](ignored-inline.md)`\n\n"
            "```markdown\n[Code](ignored-fenced.md)\n```\n\n"
            "[ref]: b.md\n"
        )

        self.assertEqual(markdown_destinations(body), ["a.md", "b.md"])

    def test_external_hosts_and_uri_schemes_are_not_local_paths(self) -> None:
        source = self.write(
            "source.md",
            "[Host](docs.example.tech/guide)\n"
            "[HTTPS](https://example.com/guide)\n"
            "[Mail](mailto:team@example.com)\n"
            "[Markdown](local.md)\n"
            "[Python](module.py)\n",
        )
        self.write("local.md")
        self.write("module.py", "value = 1\n")

        references = inspect_document_links(self.root, source)

        self.assertEqual(
            [item.status for item in references],
            ["external", "external", "external", "resolved", "resolved"],
        )

    def test_query_is_not_part_of_target_and_fragment_is_validated(self) -> None:
        self.write("target.md", "# Details\n")
        source = self.write("source.md", "[Target](target.md?mode=compact#details)\n")

        reference = inspect_document_links(self.root, source)[0]

        self.assertEqual(reference.target, "target.md")
        self.assertEqual(reference.anchor, "details")
        self.assertEqual(reference.status, "resolved")

    def test_heading_and_explicit_html_anchors_are_supported(self) -> None:
        self.write(
            "target.md",
            "# Repeat\n\n# Repeat\n\n<a id=\"explicit\"></a>\n"
            "<a name=\"named\"></a>\n\n```markdown\n# Fenced\n```\n",
        )
        source = self.write(
            "source.md",
            "[Second](target.md#repeat-1)\n"
            "[Explicit](target.md#explicit)\n"
            "[Named](target.md#named)\n"
            "[Fenced](target.md#fenced)\n",
        )

        references = inspect_document_links(self.root, source)

        self.assertEqual(
            [item.status for item in references],
            ["resolved", "resolved", "resolved", "anchor-missing"],
        )

    def test_frontmatter_links_and_headings_are_ignored(self) -> None:
        self.write("target.md", "---\ntitle: Metadata\n---\n\n# Actual\n")
        source = self.write(
            "source.md",
            "---\ndescription: '[Ignored](missing.md)'\n---\n\n"
            "[Actual](target.md#actual)\n"
            "[Metadata](target.md#title-metadata)\n",
        )

        references = inspect_document_links(self.root, source)

        self.assertEqual(len(references), 2)
        self.assertEqual(references[0].status, "resolved")
        self.assertEqual(references[1].status, "anchor-missing")

    def test_parent_escape_and_root_absolute_destinations_are_invalid(self) -> None:
        source = self.write(
            "docs/source.md",
            "[Escape](../../outside.md)\n[Absolute](/target.md)\n",
        )
        references = inspect_document_links(self.root, source)

        self.assertEqual([item.status for item in references], ["invalid", "invalid"])
        self.assertEqual(
            [item.kind for item in references],
            ["cross-boundary", "root-absolute"],
        )


class LinkGraphTests(WikiTestCase):
    def test_relative_link_and_inbound_query_share_the_same_target(self) -> None:
        self.write("concepts/model.md", "# Model\n")
        source = self.write(
            "deep/a/b/source.md",
            "[Model](../../../concepts/model.md)\n",
        )

        references = inspect_document_links(self.root, source)
        inbound = inbound_links(self.root, "concepts/model.md")

        self.assertEqual(references[0].status, "resolved")
        self.assertEqual(references[0].kind, "relative")
        self.assertEqual(references[0].target, "concepts/model.md")
        self.assertEqual([item.source for item in inbound], ["deep/a/b/source.md"])

    def test_full_and_view_modes_distinguish_missing_from_unavailable(self) -> None:
        source = self.write("source.md", "[Target](target.md)\n")

        full = inspect_document_links(self.root, source)
        view = inspect_document_links(self.root, source, available=True)

        self.assertEqual(full[0].status, "missing")
        self.assertEqual(view[0].status, "unavailable")

    def test_directory_symlink_in_a_view_keeps_logical_targets(self) -> None:
        self.write("docs/source.md", "[Target](target.md)\n")
        self.write("docs/target.md", "# Target\n")
        self.build_view("docs", view_name="linked-docs")
        view = self.view_parent / "linked-docs"

        references = inspect_wiki_links(view, available=True)

        link = next(item for item in references if item.source == "docs/source.md")
        self.assertEqual(link.target, "docs/target.md")
        self.assertEqual(link.status, "resolved")

    def test_nested_wiki_is_an_ownership_boundary(self) -> None:
        self.write("outer.md")
        nested = create_wiki(self.root / "references" / "nested", title="Nested")
        self.write("inner.md", root=nested)

        mounts = discover_mounts(self.root)
        owned = {
            path.relative_to(self.root).as_posix()
            for path in walk_owned_files(self.root)
        }

        self.assertEqual(
            [(mount.kind, mount.path.as_posix()) for mount in mounts],
            [("whero-wiki", "references/nested")],
        )
        self.assertIn("outer.md", owned)
        self.assertNotIn("references/nested/inner.md", owned)

    def test_relative_link_inside_nested_wiki_uses_nested_ownership_root(self) -> None:
        nested = create_wiki(self.root / "references" / "nested", title="Nested")
        self.write("target.md", "# Target\n", root=nested)
        source = self.write("docs/source.md", "[Target](../target.md)\n", root=nested)

        reference = inspect_document_links(
            self.root,
            source,
            mounts=discover_mounts(self.root),
        )[0]

        self.assertEqual(reference.status, "resolved")
        self.assertEqual(reference.target, "references/nested/target.md")
        self.assertEqual(reference.wiki_root, str(nested))

    def test_cli_emits_json_graph_and_auto_detects_a_view(self) -> None:
        self.write("target.md", "# Target\n")
        self.write("source.md", "[Target](target.md)\n")
        self.build_view("source.md", view_name="graph")
        view = self.view_parent / "graph"

        result = self.run_cli(
            "links",
            "graph",
            "--wiki",
            str(view),
            "--format",
            "json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        graph = json.loads(result.stdout)
        edge = next(item for item in graph if item["source"] == "source.md")
        self.assertEqual(edge["target"], "target.md")
        self.assertEqual(edge["status"], "unavailable")

    def test_validator_reports_non_relative_maintained_link(self) -> None:
        write_index(
            self.root / "index.md",
            title="Root",
            body="\n# Root\n\n[Target](/target.md)\n",
        )
        self.write("target.md")

        diagnostics = validate_wiki(self.root, mode="full")

        self.assertIn("LOCAL_LINK_INVALID", diagnostics.render_text())
