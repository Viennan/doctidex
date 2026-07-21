from __future__ import annotations

import os
import shutil
from pathlib import Path, PurePosixPath

from support import (
    FORMAT_VERSION,
    WikiTestCase,
    create_wiki,
    read_markdown,
    write_index,
    write_markdown_atomic,
)

from whero_wiki_tools.model import is_view_root
from whero_wiki_tools.view_selection import (
    load_selections,
    parse_collapse_threshold,
)
from whero_wiki_tools.view_service import execute_view, plan_view
from whero_wiki_tools.view_types import ViewRequest


class ViewSelectionTests(WikiTestCase):
    def test_builder_records_v002_requested_and_effective_roots(self) -> None:
        selected = self.write("docs/topic.md", "# Topic\n")

        result = self.build_view(str(selected), view_name="task")

        view = self.view_parent / "task"
        status = read_markdown(view / "whero-wiki-view.md").fields
        self.assertTrue(result.mutated)
        self.assertTrue(is_view_root(view))
        self.assertEqual(status["format_version"], FORMAT_VERSION)
        self.assertEqual(status["requested_selections"], ["docs/topic.md"])
        self.assertIn("docs/topic.md", status["effective_roots"])
        self.assertTrue((view / "docs" / "topic.md").is_symlink())
        self.assertEqual((view / "docs" / "topic.md").resolve(), selected.resolve())

    def test_source_can_be_inferred_from_an_absolute_selection(self) -> None:
        selected = self.write("docs/topic.md")
        request = ViewRequest(
            source=None,
            target=self.view_parent,
            view_name="inferred",
            includes=(str(selected),),
            include_files=(),
            collapse_threshold=0,
        )

        plan = plan_view(request)
        execute_view(request)

        self.assertEqual(plan.source, self.root)
        self.assertEqual(plan.requested_selections, (PurePosixPath("docs/topic.md"),))
        self.assertTrue((self.view_parent / "inferred" / "docs" / "topic.md").is_symlink())

    def test_selection_list_paths_are_relative_to_the_list_file(self) -> None:
        selected = self.write("docs/topic.md")
        lists = self.workspace / "requests"
        lists.mkdir()
        selection_file = lists / "selection.txt"
        selection_file.write_text("../wiki/docs/topic.md\n", encoding="utf-8")

        selections = load_selections(self.root, (), (selection_file,))

        self.assertEqual(selections, [PurePosixPath("docs/topic.md")])
        self.assertTrue(selected.is_file())

    def test_selection_rejects_the_source_root(self) -> None:
        with self.assertRaisesRegex(SystemExit, "below the source Wiki root"):
            self.build_view(str(self.root))

        self.assertFalse((self.view_parent / "view").exists())

    def test_collapse_threshold_accepts_fraction_percent_and_integer_forms(self) -> None:
        self.assertEqual(parse_collapse_threshold("0.8"), 80)
        self.assertEqual(parse_collapse_threshold("80%"), 80)
        self.assertEqual(parse_collapse_threshold("80"), 80)

    def test_dry_run_does_not_create_the_view(self) -> None:
        self.write("docs/topic.md")

        result = self.build_view("docs/topic.md", dry_run=True)

        self.assertFalse(result.mutated)
        self.assertIn("dry-run summary", "\n".join(result.messages))
        self.assertFalse((self.view_parent / "view").exists())

    def test_preflight_collision_prevents_any_generated_write(self) -> None:
        self.write("a.md")
        self.write("b.md")
        output = self.view_parent / "collision"
        output.mkdir()
        (output / "b.md").write_text("user data\n", encoding="utf-8")

        with self.assertRaisesRegex(SystemExit, "non-generated content"):
            self.build_view("a.md", "b.md", view_name="collision")

        self.assertFalse((output / "a.md").exists())
        self.assertFalse((output / "whero-wiki-view.md").exists())

    def test_expansion_preserves_requested_intent_and_collapses_parent(self) -> None:
        self.write("docs/a.md")
        self.write("docs/b.md")
        self.build_view("docs/a.md", view_name="expanding")

        self.build_view("docs", view_name="expanding")

        view = self.view_parent / "expanding"
        status = read_markdown(view / "whero-wiki-view.md").fields
        self.assertTrue((view / "docs").is_symlink())
        self.assertEqual(status["requested_selections"], ["docs"])
        self.assertIn("docs", status["effective_roots"])

    def test_adaptive_collapse_can_be_enabled_or_disabled(self) -> None:
        for name in ("a.md", "b.md", "c.md", "d.md", "e.md"):
            self.write(f"docs/{name}")

        self.build_view(
            "docs/a.md",
            "docs/b.md",
            "docs/c.md",
            "docs/d.md",
            view_name="adaptive",
            collapse_threshold=80,
        )
        self.build_view(
            "docs/a.md",
            "docs/b.md",
            "docs/c.md",
            "docs/d.md",
            view_name="explicit",
            collapse_threshold=0,
        )

        self.assertTrue((self.view_parent / "adaptive" / "docs").is_symlink())
        self.assertTrue((self.view_parent / "explicit" / "docs").is_dir())
        self.assertFalse((self.view_parent / "explicit" / "docs").is_symlink())

    def test_view_required_ancestor_document_is_added(self) -> None:
        self.write("provider/topic.md")
        write_index(
            self.root / "provider" / "index.md",
            title="Provider",
            body="\n# Provider\n\n[Topic](topic.md)\n",
        )

        self.build_view("provider/topic.md")

        view = self.view_parent / "view"
        self.assertTrue((view / "provider" / "index.md").is_symlink())

    def test_view_required_document_must_be_maintained(self) -> None:
        self.write("provider/topic.md")
        write_markdown_atomic(
            self.root / "provider" / "index.md",
            {
                "type": "Whero Wiki Index",
                "title": "Provider",
                "whero_view_required": True,
            },
            "\n# Provider\n",
        )

        with self.assertRaisesRegex(SystemExit, "must set whero_maintenance"):
            self.build_view("provider/topic.md")


class ViewBoundaryTests(WikiTestCase):
    def test_preserved_descendant_promotes_the_whole_boundary(self) -> None:
        write_index(
            self.root / "index.md",
            title="Root",
            whero_preserved_paths=["archive"],
        )
        self.write("archive/a.md")
        self.write("archive/b.md")

        self.build_view("archive/a.md")

        archive = self.view_parent / "view" / "archive"
        status = read_markdown(self.view_parent / "view" / "whero-wiki-view.md").fields
        self.assertTrue(archive.is_symlink())
        self.assertTrue((archive / "b.md").is_file())
        self.assertIn("archive", status["effective_roots"])
        self.assertEqual(status["requested_selections"], ["archive/a.md"])

    def test_nested_wiki_descendant_promotes_the_mount_root(self) -> None:
        nested = create_wiki(self.root / "vendor", title="Nested")
        self.write("guide.md", root=nested)

        self.build_view("vendor/guide.md")

        mounted = self.view_parent / "view" / "vendor"
        self.assertTrue(mounted.is_symlink())
        self.assertTrue((mounted / "whero-wiki-meta.md").is_file())

    def test_source_symlink_descendant_promotes_the_symlink(self) -> None:
        external = self.workspace / "external"
        external.mkdir()
        (external / "a.md").write_text("# A\n", encoding="utf-8")
        (external / "b.md").write_text("# B\n", encoding="utf-8")
        (self.root / "linked").symlink_to(
            os.path.relpath(external, start=self.root),
            target_is_directory=True,
        )

        self.build_view("linked/a.md")

        linked = self.view_parent / "view" / "linked"
        self.assertTrue(linked.is_symlink())
        self.assertTrue((linked / "b.md").is_file())

    def test_view_of_view_links_to_the_immediate_source(self) -> None:
        self.write("a.md")
        self.write("b.md")
        self.build_view("a.md", view_name="parent")
        parent = self.view_parent / "parent"
        child_parent = self.workspace / "child-views"
        child_parent.mkdir()

        self.build_view(
            "a.md",
            source=parent,
            target=child_parent,
            view_name="child",
        )

        child_link = child_parent / "child" / "a.md"
        logical_target = Path(os.path.abspath(child_link.parent / os.readlink(child_link)))
        self.assertEqual(logical_target, parent / "a.md")
        self.assertEqual(child_link.resolve(), (self.root / "a.md").resolve())

        with self.assertRaisesRegex(SystemExit, "unavailable from the immediate source"):
            self.build_view(
                "b.md",
                source=parent,
                target=child_parent,
                view_name="child",
            )

    def test_path_source_relocation_requires_approval_and_relinks(self) -> None:
        self.write("a.md")
        self.build_view("a.md", view_name="relocated")
        old_source = self.root
        new_source = self.workspace / "moved-wiki"
        shutil.copytree(old_source, new_source, symlinks=True)

        with self.assertRaisesRegex(SystemExit, "uses a different source"):
            self.build_view("a.md", source=new_source, view_name="relocated")

        self.build_view(
            "a.md",
            source=new_source,
            view_name="relocated",
            allow_path_relocation=True,
        )

        link = self.view_parent / "relocated" / "a.md"
        status = read_markdown(self.view_parent / "relocated" / "whero-wiki-view.md").fields
        self.assertEqual(link.resolve(), (new_source / "a.md").resolve())
        self.assertEqual(
            (self.view_parent / "relocated" / status["source"]).resolve(),
            new_source.resolve(),
        )


class ViewGitIdentityTests(WikiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.write("selected.md", "first\n")
        self.write("outside.md", "first\n")
        self.init_git(self.root)
        self.initial_commit = self.commit_all(self.root, "initial")

    def test_git_view_records_commit_and_sanitized_remote(self) -> None:
        self.git(
            self.root,
            "remote",
            "add",
            "origin",
            "https://user:secret@example.com/org/wiki.git?token=value#branch",
        )

        self.build_view("selected.md")

        fields = read_markdown(self.view_parent / "view" / "whero-wiki-view.md").fields
        self.assertEqual(fields["source_commit"], self.initial_commit)
        self.assertEqual(fields["source_git_remote_url"], "https://example.com/org/wiki.git")
        self.assertNotIn("secret", str(fields))
        self.assertNotIn("token", str(fields))

    def test_selected_untracked_or_modified_content_is_rejected_preflight(self) -> None:
        self.write("untracked.md")
        with self.assertRaisesRegex(SystemExit, "untracked=1"):
            self.build_view("untracked.md", view_name="untracked")
        self.assertFalse((self.view_parent / "untracked").exists())

        self.write("selected.md", "modified\n")
        with self.assertRaisesRegex(SystemExit, "worktree-content-changed=1"):
            self.build_view("selected.md", view_name="modified")
        self.assertFalse((self.view_parent / "modified").exists())

    def test_dirty_or_untracked_content_outside_selection_is_allowed(self) -> None:
        self.write("outside.md", "modified\n")
        self.write("new-outside.md")

        self.build_view("selected.md")

        self.assertTrue((self.view_parent / "view" / "selected.md").is_symlink())

    def test_forward_change_outside_effective_roots_advances_identity(self) -> None:
        self.build_view("selected.md")
        self.write("outside.md", "second\n")
        next_commit = self.commit_all(self.root, "outside change")

        result = self.build_view("selected.md")

        status = read_markdown(self.view_parent / "view" / "whero-wiki-view.md").fields
        self.assertIn("outside its roots", "\n".join(result.messages))
        self.assertEqual(status["source_commit"], next_commit)

    def test_forward_change_inside_effective_roots_preserves_recorded_identity(self) -> None:
        self.build_view("selected.md")
        status_path = self.view_parent / "view" / "whero-wiki-view.md"
        previous = status_path.read_text(encoding="utf-8")
        self.write("selected.md", "second\n")
        self.commit_all(self.root, "selected change")

        with self.assertRaisesRegex(SystemExit, "disclosed content or structure"):
            self.build_view("selected.md")

        self.assertEqual(status_path.read_text(encoding="utf-8"), previous)
