from __future__ import annotations

import os
import subprocess
from pathlib import PurePosixPath

from support import WikiTestCase, create_wiki, write_index

from whero_wiki_tools.curated import init_index, validate_wiki
from whero_wiki_tools.errors import WheroToolError
from whero_wiki_tools.mounts import discover_boundaries, discover_mounts, walk_owned_files
from whero_wiki_tools.preserved import discover_preserved_paths
from whero_wiki_tools.restoration import apply_restoration, plan_restoration


class PreservedBoundaryTests(WikiTestCase):
    def test_owned_walk_and_validation_do_not_enter_exact_boundaries(self) -> None:
        write_index(
            self.root / "index.md",
            title="Root",
            whero_preserved_paths=["archive", "frozen.md"],
        )
        self.write("archive/index.md", "---\ninvalid: [\n---\n")
        self.write("archive/broken.md", "[Missing](missing.md)\n")
        self.write("frozen.md", "[Missing](missing.md)\n")

        diagnostics = validate_wiki(self.root, mode="full")
        owned = {
            path.relative_to(self.root).as_posix()
            for path in walk_owned_files(self.root)
        }
        mounts, preserved, problems = discover_boundaries(self.root)

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
        self.assertNotIn("archive/broken.md", owned)
        self.assertNotIn("frozen.md", owned)
        self.assertEqual(mounts, [])
        self.assertEqual(
            [entry.path.as_posix() for entry in preserved],
            ["archive", "frozen.md"],
        )
        self.assertEqual(problems, [])

    def test_patterns_match_direct_children_only_and_allow_no_match(self) -> None:
        write_index(
            self.root / "index.md",
            title="Root",
            whero_preserved_patterns=["^generated-.*$", ".*\\.lock"],
        )
        self.write("generated-cache/a.md")
        self.write("nested/generated-cache/b.md")

        preserved, problems = discover_preserved_paths(self.root)

        self.assertEqual(problems, [])
        self.assertEqual(
            [entry.path for entry in preserved],
            [PurePosixPath("generated-cache")],
        )

    def test_invalid_pattern_and_unsafe_exact_path_are_reported(self) -> None:
        write_index(
            self.root / "index.md",
            title="Root",
            whero_preserved_paths=["../outside"],
            whero_preserved_patterns=["[unterminated"],
        )

        _, problems = discover_preserved_paths(self.root)

        self.assertTrue(any("relative to the Wiki root" in item for item in problems))
        self.assertTrue(any("invalid preserved pattern" in item for item in problems))

    def test_missing_preserved_path_is_error_in_full_and_notice_in_view(self) -> None:
        write_index(
            self.root / "index.md",
            title="Root",
            whero_preserved_paths=["archive"],
        )
        self.write("archive/a.md")
        self.write("guide.md")
        self.build_view("guide.md", view_name="limited")
        view = self.view_parent / "limited"

        full_source = self.root / "archive"
        full_source.rename(self.root / "archive-removed")
        full = validate_wiki(self.root, mode="full")
        limited = validate_wiki(view, mode="view")

        self.assertIn("PRESERVED_MISSING", full.render_text())
        self.assertFalse(limited.has_errors, limited.render_text())
        self.assertIn("PRESERVED_UNAVAILABLE", limited.render_text())

    def test_outer_maintenance_cannot_write_inside_owned_boundaries(self) -> None:
        write_index(
            self.root / "index.md",
            title="Root",
            whero_preserved_paths=["archive"],
        )
        (self.root / "archive" / "docs").mkdir(parents=True)

        with self.assertRaisesRegex(WheroToolError, "preserved boundary"):
            init_index(self.root, "archive/docs", "Archive", "Owner managed.")

        nested = create_wiki(self.root / "nested", title="Nested")
        (nested / "docs").mkdir()
        with self.assertRaisesRegex(WheroToolError, "mounted ownership boundary"):
            init_index(self.root, "nested/docs", "Nested", "Nested-owned.")

    def test_preserved_root_hides_nested_wiki_from_outer_mount_discovery(self) -> None:
        write_index(
            self.root / "index.md",
            title="Root",
            whero_preserved_paths=["vendor"],
        )
        create_wiki(self.root / "vendor", title="Nested")

        mounts, preserved, problems = discover_boundaries(self.root)

        self.assertEqual(mounts, [])
        self.assertEqual([entry.path.as_posix() for entry in preserved], ["vendor"])
        self.assertEqual(problems, [])


class ExternalReferenceTests(WikiTestCase):
    def declare_filesystem_mount(self) -> None:
        write_index(
            self.root / "index.md",
            title="Root",
            whero_external_references=[
                {
                    "path": "vendor/docs",
                    "projection": "mount",
                    "content": "ordinary",
                    "locator": {
                        "kind": "filesystem",
                        "path": "../external",
                        "type": "directory",
                    },
                }
            ],
        )

    def test_filesystem_restoration_is_planned_then_applied(self) -> None:
        external = self.workspace / "external"
        external.mkdir()
        (external / "a.md").write_text("# A\n", encoding="utf-8")
        self.declare_filesystem_mount()

        plan = plan_restoration(self.root)

        self.assertEqual(plan.actions[0].state, "missing")
        self.assertEqual(plan.actions[0].operation, "link")
        self.assertFalse((self.root / "vendor" / "docs").exists())

        apply_restoration(plan)
        restored = self.root / "vendor" / "docs"
        self.assertTrue(restored.is_symlink())
        self.assertFalse(os.path.isabs(os.readlink(restored)))
        self.assertEqual(restored.resolve(), external.resolve())
        self.assertEqual(plan_restoration(self.root).actions[0].state, "present-valid")

    def test_selection_inside_mount_is_legal_and_promotes_whole_mount(self) -> None:
        external = self.workspace / "external"
        external.mkdir()
        (external / "a.md").write_text("# A\n", encoding="utf-8")
        (external / "b.md").write_text("# B\n", encoding="utf-8")
        self.declare_filesystem_mount()
        apply_restoration(plan_restoration(self.root))

        self.build_view("vendor/docs/a.md")

        mounted = self.view_parent / "view" / "vendor" / "docs"
        self.assertTrue(mounted.is_symlink())
        self.assertTrue((mounted / "b.md").is_file())

    def test_unrestored_mount_selection_reports_restoration_guidance(self) -> None:
        external = self.workspace / "external"
        external.mkdir()
        self.declare_filesystem_mount()

        with self.assertRaisesRegex(SystemExit, "restore the declared external reference"):
            self.build_view("vendor/docs/a.md")

    def test_restoration_never_replaces_an_existing_invalid_target(self) -> None:
        external = self.workspace / "external"
        external.mkdir()
        self.declare_filesystem_mount()
        invalid = self.root / "vendor" / "docs"
        invalid.mkdir(parents=True)

        plan = plan_restoration(self.root)

        self.assertEqual(plan.actions[0].operation, "error")
        with self.assertRaisesRegex(WheroToolError, "cannot apply restoration"):
            apply_restoration(plan)
        self.assertTrue(invalid.is_dir())
        self.assertFalse(invalid.is_symlink())

    def test_git_submodule_is_detected_as_a_mount(self) -> None:
        source_repository = self.workspace / "submodule-source"
        source_repository.mkdir()
        self.init_git(source_repository)
        (source_repository / "source.md").write_text("# Source\n", encoding="utf-8")
        self.commit_all(source_repository, "initial")

        repository = self.workspace / "repository"
        create_wiki(repository, title="Repository")
        self.init_git(repository)
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
        self.commit_all(repository, "add submodule")

        mounts = discover_mounts(repository)

        self.assertEqual(len(mounts), 1)
        self.assertEqual(mounts[0].kind, "submodule")
        self.assertTrue(mounts[0].submodule)
        self.assertEqual(mounts[0].path, PurePosixPath("vendor"))
        self.assertIsNotNone(mounts[0].git_commit)

    def test_mounts_cli_lists_preserved_and_external_boundaries(self) -> None:
        external = self.workspace / "external"
        external.mkdir()
        self.declare_filesystem_mount()
        apply_restoration(plan_restoration(self.root))

        result = self.run_cli("mounts", "--wiki", str(self.root))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("declared-mount: vendor/docs", result.stdout)
