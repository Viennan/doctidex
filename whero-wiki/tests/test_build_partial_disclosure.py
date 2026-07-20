from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "build_partial_disclosure.py"
)
WIKI_META = """---
type: Whero Wiki
whero_wiki: true
whero_maintenance: true
whero_scope_required: true
format_version: "0.1"
---

# Whero Wiki
"""


def framework_file(title: str) -> str:
    return f"""---
whero_maintenance: true
whero_scope_required: true
---

# {title}
"""


class PartialDisclosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source" / "whero-wiki"
        self.create_wiki(self.source)
        self.target = self.root / "target"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_wiki(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "whero-wiki-meta.md").write_text(WIKI_META, encoding="utf-8")

    def write_source(
        self,
        relative: str,
        content: str = "source\n",
        source: Path | None = None,
    ) -> Path:
        path = (source or self.source) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_builder(
        self,
        *includes: str,
        source: Path | None = None,
        target: Path | None = None,
        cwd: Path | None = None,
        view_name: str | None = None,
        threshold: str | None = "0",
        dry_run: bool = False,
        extra_arguments: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(source or self.source),
            "--target",
            str(target or self.target),
        ]
        for selection in includes:
            command.extend(["--include", selection])
        if view_name is not None:
            command.extend(["--view-name", view_name])
        if threshold is not None:
            command.extend(["--collapse-threshold", threshold])
        if dry_run:
            command.append("--dry-run")
        if extra_arguments:
            command.extend(extra_arguments)
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_succeeded(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_build_includes_scope_framework_and_rebuilds_status(self) -> None:
        self.write_source("index.md", framework_file("Root Index"))
        self.write_source("provider/log.md", framework_file("Log"))
        self.write_source(
            "provider/navigation.md",
            "---\nwhero_maintenance: true\n---\n\n# Navigation\n",
        )
        self.write_source("provider/framework.md", framework_file("Framework"))
        self.write_source("provider/topic/document.md")
        self.write_source("provider/topic/other.md")

        result = self.run_builder("provider/topic/document.md")
        self.assert_succeeded(result)

        output = self.target / "whero-wiki"
        for relative in (
            "whero-wiki-meta.md",
            "index.md",
            "provider/log.md",
            "provider/framework.md",
            "provider/topic/document.md",
        ):
            self.assertTrue((output / relative).is_symlink(), relative)
            self.assertFalse(os.readlink(output / relative).startswith("/"))
        self.assertFalse((output / "provider/navigation.md").exists())

        status = output / "partial-disclosure.md"
        content = status.read_text(encoding="utf-8")
        self.assertIn("collapse_threshold: 0", content)
        self.assertIn("whero_scope_required: true", content)
        self.assertIn("disclosed_symlinks: 5", content)
        self.assertNotIn(str(self.source), content)

        status.write_text(
            content.replace("disclosed_symlinks: 5", "disclosed_symlinks: 99"),
            encoding="utf-8",
        )
        expanded = self.run_builder("provider/topic/other.md")
        self.assert_succeeded(expanded)
        self.assertTrue((output / "provider/topic/other.md").is_symlink())
        self.assertIn(
            "disclosed_symlinks: 6",
            status.read_text(encoding="utf-8"),
        )

        selected_maintained_content = self.run_builder("provider/navigation.md")
        self.assert_succeeded(selected_maintained_content)
        self.assertTrue((output / "provider/navigation.md").is_symlink())
        self.assertIn(
            "disclosed_symlinks: 7",
            status.read_text(encoding="utf-8"),
        )

        repeated = self.run_builder("provider/topic/document.md")
        self.assert_succeeded(repeated)
        self.assertEqual(repeated.stdout, "")

    def test_parent_selection_collapses_existing_child_containers(self) -> None:
        self.write_source("provider/topic/a.md")
        self.write_source("provider/topic/b.md")

        initial = self.run_builder("provider/topic/a.md")
        self.assert_succeeded(initial)
        provider = self.target / "whero-wiki" / "provider"
        self.assertTrue(provider.is_dir())
        self.assertFalse(provider.is_symlink())

        expanded = self.run_builder("provider")
        self.assert_succeeded(expanded)
        self.assertIn("requested parent collapse: provider", expanded.stdout)
        self.assertIn("visible scope expands by 1 file(s)", expanded.stdout)
        self.assertTrue(provider.is_symlink())
        self.assertEqual(provider.resolve(), (self.source / "provider").resolve())
        status = (self.target / "whero-wiki" / "partial-disclosure.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("- `provider`", status)
        self.assertNotIn("provider/topic/a.md`", status)

    def test_parent_collapse_rejects_non_generated_content(self) -> None:
        self.write_source("provider/a.md")
        self.write_source("provider/b.md")
        self.assert_succeeded(self.run_builder("provider/a.md"))

        provider = self.target / "whero-wiki" / "provider"
        unexpected = provider / "local-note.md"
        unexpected.write_text("do not remove\n", encoding="utf-8")
        result = self.run_builder("provider")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-generated content", result.stderr)
        self.assertFalse(provider.is_symlink())
        self.assertEqual(unexpected.read_text(encoding="utf-8"), "do not remove\n")
        self.assertTrue((provider / "a.md").is_symlink())

    def test_adaptive_collapse_uses_default_threshold_and_can_be_disabled(self) -> None:
        for index in range(5):
            self.write_source(f"provider/{index}.md")

        default_target = self.root / "default-target"
        default_result = self.run_builder(
            *(f"provider/{index}.md" for index in range(4)),
            target=default_target,
            threshold=None,
        )
        self.assert_succeeded(default_result)
        self.assertIn("automatic collapse: provider", default_result.stdout)
        self.assertIn("visible scope expands by 1 file(s)", default_result.stdout)
        self.assertTrue((default_target / "whero-wiki" / "provider").is_symlink())

        below_target = self.root / "below-target"
        below_result = self.run_builder(
            *(f"provider/{index}.md" for index in range(3)),
            target=below_target,
            threshold=None,
        )
        self.assert_succeeded(below_result)
        self.assertFalse((below_target / "whero-wiki" / "provider").is_symlink())

        disabled_target = self.root / "disabled-target"
        disabled_result = self.run_builder(
            *(f"provider/{index}.md" for index in range(4)),
            target=disabled_target,
            threshold="0",
        )
        self.assert_succeeded(disabled_result)
        self.assertFalse((disabled_target / "whero-wiki" / "provider").is_symlink())

    def test_threshold_accepts_fraction_and_percent_forms(self) -> None:
        for index in range(5):
            self.write_source(f"provider/{index}.md")

        for label, threshold in (("fraction", "0.8"), ("percent", "80%")):
            with self.subTest(threshold=threshold):
                target = self.root / f"{label}-target"
                result = self.run_builder(
                    *(f"provider/{index}.md" for index in range(4)),
                    target=target,
                    threshold=threshold,
                )
                self.assert_succeeded(result)
                self.assertTrue((target / "whero-wiki" / "provider").is_symlink())

    def test_full_preflight_prevents_earlier_writes_on_late_collision(self) -> None:
        self.write_source("alpha/a.md")
        self.write_source("beta/b.md")
        collision = self.target / "whero-wiki" / "beta" / "b.md"
        collision.parent.mkdir(parents=True)
        collision.write_text("existing\n", encoding="utf-8")

        result = self.run_builder("alpha/a.md", "beta/b.md")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target collision", result.stderr)
        self.assertFalse((self.target / "whero-wiki" / "alpha").exists())
        self.assertEqual(collision.read_text(encoding="utf-8"), "existing\n")
        self.assertFalse(
            (self.target / "whero-wiki" / "partial-disclosure.md").exists()
        )

    def test_dry_run_does_not_create_target(self) -> None:
        self.write_source("provider/a.md")
        result = self.run_builder("provider/a.md", dry_run=True)
        self.assert_succeeded(result)
        self.assertIn("dry-run summary: 2 link/collapse action(s)", result.stdout)
        self.assertNotIn("would link", result.stdout)
        self.assertFalse(self.target.exists())

    def test_selection_accepts_absolute_path(self) -> None:
        selected = self.write_source("provider/a.md")

        result = self.run_builder(str(selected))

        self.assert_succeeded(result)
        output = self.target / "whero-wiki"
        self.assertTrue((output / "provider" / "a.md").is_symlink())
        status = (output / "partial-disclosure.md").read_text(encoding="utf-8")
        self.assertIn("- `provider/a.md`", status)
        self.assertNotIn(str(selected), status)

    def test_selection_accepts_working_directory_relative_path_with_parent(self) -> None:
        selected = self.write_source("provider/a.md")
        working = self.root / "work" / "nested"
        working.mkdir(parents=True)
        relative = os.path.relpath(selected, start=working)

        result = self.run_builder(relative, cwd=working)

        self.assert_succeeded(result)
        self.assertTrue(
            (self.target / "whero-wiki" / "provider" / "a.md").is_symlink()
        )

    def test_selection_accepts_user_home_path(self) -> None:
        home = Path.home().resolve()
        try:
            selected = self.source.resolve().relative_to(home) / "provider" / "a.md"
        except ValueError:
            self.skipTest("test source is not below the current user home")
        self.write_source("provider/a.md")

        result = self.run_builder(f"~/{selected.as_posix()}")

        self.assert_succeeded(result)
        self.assertTrue(
            (self.target / "whero-wiki" / "provider" / "a.md").is_symlink()
        )

    def test_include_from_accepts_paths_relative_to_list_file(self) -> None:
        selected = self.write_source("provider/a.md")
        lists = self.root / "lists" / "nested"
        lists.mkdir(parents=True)
        selection_file = lists / "selections.txt"
        selection_file.write_text(
            os.path.relpath(selected, start=lists) + "\n",
            encoding="utf-8",
        )

        result = self.run_builder(
            extra_arguments=["--include-from", str(selection_file)]
        )

        self.assert_succeeded(result)
        self.assertTrue(
            (self.target / "whero-wiki" / "provider" / "a.md").is_symlink()
        )

    def test_selection_rejects_ambiguous_relative_path(self) -> None:
        self.write_source("topic.md", "source interpretation\n")
        working = self.source / "workspace"
        working.mkdir()
        self.write_source("workspace/topic.md", "cwd interpretation\n")

        result = self.run_builder("topic.md", cwd=working)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ambiguous", result.stderr)
        self.assertIn("use an absolute path", result.stderr)

    def test_selection_rejects_source_root_and_escaping_symlink(self) -> None:
        outside = self.root / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        escaping = self.source / "escaping.md"
        escaping.symlink_to(outside)

        source_root = self.run_builder(str(self.source))
        escaped = self.run_builder(str(escaping))

        self.assertNotEqual(source_root.returncode, 0)
        self.assertIn("item below the source Wiki root", source_root.stderr)
        self.assertNotEqual(escaped.returncode, 0)
        self.assertIn("inside the source Wiki", escaped.stderr)

    def test_arbitrary_wiki_root_name_and_explicit_view_name(self) -> None:
        source = self.root / "source" / "reference-library"
        self.create_wiki(source)
        self.write_source("provider/a.md", source=source)

        default_target = self.root / "default-view"
        default_result = self.run_builder(
            "provider/a.md",
            source=source,
            target=default_target,
        )
        self.assert_succeeded(default_result)
        self.assertEqual(default_result.stdout, "")
        default_output = default_target / "reference-library"
        self.assertTrue((default_output / "whero-wiki-meta.md").is_symlink())
        self.assertTrue((default_output / "provider/a.md").is_symlink())

        named_target = self.root / "named-view"
        named_result = self.run_builder(
            "provider/a.md",
            source=source,
            target=named_target,
            view_name="focused-reference",
        )
        self.assert_succeeded(named_result)
        named_output = named_target / "focused-reference"
        self.assertTrue((named_output / "whero-wiki-meta.md").is_symlink())
        status = (named_output / "partial-disclosure.md").read_text(
            encoding="utf-8"
        )
        self.assertIn('view_name: "focused-reference"', status)

    def test_source_requires_valid_whero_wiki_meta(self) -> None:
        source = self.root / "plain-directory"
        source.mkdir()
        self.write_source("a.md", source=source)

        missing = self.run_builder("a.md", source=source)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("missing regular whero-wiki-meta.md", missing.stderr)

        (source / "whero-wiki-meta.md").write_text(
            "---\nwhero_wiki: true\n---\n",
            encoding="utf-8",
        )
        incomplete = self.run_builder("a.md", source=source)
        self.assertNotEqual(incomplete.returncode, 0)
        self.assertIn("whero_maintenance", incomplete.stderr)
        self.assertIn("whero_scope_required", incomplete.stderr)

    def test_scope_required_file_must_be_whero_maintained(self) -> None:
        self.write_source(
            "provider/framework.md",
            "---\nwhero_scope_required: true\n---\n",
        )
        self.write_source("provider/topic/a.md")

        result = self.run_builder("provider/topic/a.md")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "scope-required file must set whero_maintenance: true",
            result.stderr,
        )

    def test_preserved_descendant_selection_discloses_atomic_root(self) -> None:
        self.write_source(
            "index.md",
            """---
type: Whero Wiki Index
whero_maintenance: true
whero_scope_required: true
whero_preserved_paths:
  - archive
---

# Root Index
""",
        )
        self.write_source("archive/topic/a.md")
        self.write_source("archive/topic/b.md")

        disclosed = self.run_builder("archive/topic/a.md")
        self.assert_succeeded(disclosed)
        self.assertIn(
            "preserved boundary expansion (requested selection)",
            disclosed.stdout,
        )
        self.assertIn("selects whole boundary archive", disclosed.stdout)
        output = self.target / "whero-wiki"
        self.assertTrue((output / "archive").is_symlink())
        self.assertTrue((output / "archive" / "topic" / "a.md").is_file())
        self.assertTrue((output / "archive" / "topic" / "b.md").is_file())
        self.assertTrue((output / "index.md").is_symlink())
        status = (output / "partial-disclosure.md").read_text(encoding="utf-8")
        self.assertIn("- `archive`", status)
        self.assertNotIn("archive/topic/a.md`", status)

    def test_link_into_preserved_content_expands_only_when_target_is_selected(self) -> None:
        self.write_source(
            "index.md",
            """---
type: Whero Wiki Index
whero_maintenance: true
whero_scope_required: true
whero_preserved_paths:
  - archive
---

# Root Index
""",
        )
        self.write_source(
            "guide.md",
            "# Guide\n\n[Preserved source](archive/topic/a.md)\n",
        )
        self.write_source("archive/topic/a.md")
        self.write_source("archive/topic/b.md")

        guide_only = self.run_builder("guide.md")

        self.assert_succeeded(guide_only)
        output = self.target / "whero-wiki"
        self.assertTrue((output / "guide.md").is_symlink())
        self.assertFalse((output / "archive").exists())

        expanded = self.run_builder("archive/topic/a.md")

        self.assert_succeeded(expanded)
        self.assertIn("selects whole boundary archive", expanded.stdout)
        self.assertTrue((output / "archive").is_symlink())
        self.assertTrue((output / "archive" / "topic" / "b.md").is_file())

    def test_adaptive_collapse_does_not_cross_preserved_boundary(self) -> None:
        self.write_source(
            "index.md",
            """---
type: Whero Wiki Index
whero_maintenance: true
whero_scope_required: true
whero_preserved_paths:
  - provider/archive
---

# Root Index
""",
        )
        self.write_source("provider/a.md")
        self.write_source("provider/b.md")
        self.write_source("provider/archive/private.md")

        result = self.run_builder("provider/a.md", threshold="50")

        self.assert_succeeded(result)
        output = self.target / "whero-wiki"
        self.assertTrue((output / "provider" / "a.md").is_symlink())
        self.assertFalse((output / "provider").is_symlink())
        self.assertFalse((output / "provider" / "archive").exists())

        whole_parent = self.run_builder("provider", threshold="50")
        self.assert_succeeded(whole_parent)
        self.assertTrue((output / "provider").is_symlink())
        self.assertTrue((output / "provider" / "archive" / "private.md").is_file())

    def test_new_preserved_declaration_promotes_existing_descendant_view(self) -> None:
        self.write_source("index.md", framework_file("Root Index"))
        self.write_source("archive/a.md")
        self.assert_succeeded(self.run_builder("archive/a.md"))
        self.write_source(
            "index.md",
            """---
type: Whero Wiki Index
whero_maintenance: true
whero_scope_required: true
whero_preserved_paths:
  - archive
---

# Root Index
""",
        )

        result = self.run_builder("index.md")

        self.assert_succeeded(result)
        self.assertIn(
            "preserved boundary expansion (existing view)",
            result.stdout,
        )
        output = self.target / "whero-wiki"
        self.assertTrue((output / "archive").is_symlink())
        self.assertTrue((output / "archive" / "a.md").is_file())
        status = (output / "partial-disclosure.md").read_text(encoding="utf-8")
        self.assertIn("- `archive`", status)
        self.assertNotIn("archive/a.md`", status)

    def test_collected_source_frontmatter_need_not_be_valid_yaml(self) -> None:
        self.write_source(
            "provider/exported.md",
            "---\nupstream: [unclosed\n---\n\n# Exported Source\n",
        )
        self.write_source("provider/topic/a.md")

        result = self.run_builder("provider/topic/a.md")

        self.assert_succeeded(result)
        output = self.target / "whero-wiki"
        self.assertTrue((output / "provider/topic/a.md").is_symlink())
        self.assertFalse((output / "provider/exported.md").exists())

    def test_nested_whero_wiki_uses_delegated_partial_disclosure(self) -> None:
        self.write_source("references/index.md", framework_file("References"))
        nested = self.source / "references" / "vendor"
        self.create_wiki(nested)
        self.write_source("index.md", framework_file("Vendor Index"), source=nested)
        self.write_source("topic/a.md", source=nested)
        self.write_source("topic/b.md", source=nested)

        result = self.run_builder("references/vendor/topic/a.md")

        self.assert_succeeded(result)
        output = self.target / "whero-wiki"
        nested_output = output / "references" / "vendor"
        self.assertTrue((output / "references/index.md").is_symlink())
        self.assertTrue((nested_output / "partial-disclosure.md").is_file())
        self.assertTrue((nested_output / "whero-wiki-meta.md").is_symlink())
        self.assertTrue((nested_output / "index.md").is_symlink())
        self.assertTrue((nested_output / "topic/a.md").is_symlink())
        self.assertFalse((nested_output / "topic/b.md").exists())
        outer_status = (output / "partial-disclosure.md").read_text(encoding="utf-8")
        self.assertIn("delegated_mounts: 1", outer_status)
        self.assertIn("- `references/vendor`", outer_status)

    def test_whero_submodule_update_uses_inner_git_source_changes(self) -> None:
        nested_repository = self.root / "nested-repository"
        self.create_wiki(nested_repository)
        self.write_source(
            "index.md",
            framework_file("Nested Index"),
            source=nested_repository,
        )
        self.write_source(
            "topic/a.md",
            "first\n",
            source=nested_repository,
        )
        self.git(nested_repository, "init", "-q")
        self.git(nested_repository, "config", "user.name", "Test User")
        self.git(nested_repository, "config", "user.email", "test@example.com")
        initial_nested_commit = self.commit_all(nested_repository, "initial")

        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source(
            "references/index.md",
            framework_file("References"),
            source=source,
        )
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        self.git(repository, "add", "whero-wiki")
        self.git(repository, "commit", "-qm", "wiki")
        add_result = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "-q",
                str(nested_repository),
                "whero-wiki/references/vendor",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(add_result.returncode, 0, add_result.stderr)
        self.commit_all(repository, "nested Wiki submodule")

        initial = self.run_builder(
            "references/vendor/topic/a.md",
            source=source,
        )
        self.assert_succeeded(initial)
        inner_status = (
            self.target
            / "whero-wiki"
            / "references"
            / "vendor"
            / "partial-disclosure.md"
        )
        self.assertIn(
            f'source_commit: "{initial_nested_commit}"',
            inner_status.read_text(encoding="utf-8"),
        )

        self.write_source(
            "topic/a.md",
            "second\n",
            source=nested_repository,
        )
        content_commit = self.commit_all(nested_repository, "content update")
        mounted = source / "references" / "vendor"
        self.git(mounted, "fetch", "-q", "origin")
        self.git(mounted, "checkout", "-q", content_commit)
        self.commit_all(repository, "advance nested content")

        content_update = self.run_builder(
            "references/vendor/topic/a.md",
            source=source,
        )
        self.assertNotEqual(content_update.returncode, 0)
        self.assertIn("delegated disclosure failed", content_update.stderr)
        self.assertIn("disclosed content or structure", content_update.stderr)
        self.assertIn("content-changed=1", content_update.stderr)
        self.assertIn(
            f'source_commit: "{initial_nested_commit}"',
            inner_status.read_text(encoding="utf-8"),
        )

        (nested_repository / "topic" / "a.md").rename(
            nested_repository / "topic" / "renamed.md"
        )
        structural_commit = self.commit_all(
            nested_repository,
            "rename selected file",
        )
        self.git(mounted, "fetch", "-q", "origin")
        self.git(mounted, "checkout", "-q", structural_commit)
        self.commit_all(repository, "advance nested structure")

        structural_update = self.run_builder(
            "references/vendor/topic/a.md",
            source=source,
        )

        self.assertNotEqual(structural_update.returncode, 0)
        self.assertIn("delegated disclosure failed", structural_update.stderr)
        self.assertIn(
            "forward Git update changes the disclosed structure",
            structural_update.stderr,
        )
        retained_status = inner_status.read_text(encoding="utf-8")
        self.assertIn(f'source_commit: "{initial_nested_commit}"', retained_status)
        self.assertNotIn(structural_commit, retained_status)

    def test_parent_selection_does_not_implicitly_disclose_mount(self) -> None:
        nested = self.source / "references" / "vendor"
        self.create_wiki(nested)
        self.write_source("topic/a.md", source=nested)
        self.write_source("references/local.md")

        rejected = self.run_builder("references")

        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("mounted repository boundaries", rejected.stderr)
        accepted = self.run_builder(
            "references",
            target=self.root / "accepted",
            extra_arguments=["--allow-mount-parent"],
        )
        self.assert_succeeded(accepted)
        self.assertTrue((self.root / "accepted" / "whero-wiki" / "references").is_symlink())

    def test_plain_submodule_internal_path_requires_opt_in(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        submodule_source = self.root / "plain-submodule"
        submodule_source.mkdir()
        self.git(submodule_source, "init", "-q")
        self.git(submodule_source, "config", "user.name", "Test User")
        self.git(submodule_source, "config", "user.email", "test@example.com")
        self.write_source("guide.md", source=submodule_source)
        self.commit_all(submodule_source, "initial")
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        self.git(repository, "add", "whero-wiki/whero-wiki-meta.md")
        self.git(repository, "commit", "-qm", "wiki")
        result = subprocess.run(
            [
                "git", "-C", str(repository), "-c", "protocol.file.allow=always",
                "submodule", "add", "-q", str(submodule_source),
                "whero-wiki/references/vendor",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.git(repository, "commit", "-qam", "submodule")

        rejected = self.run_builder(
            "references/vendor/guide.md",
            source=source,
        )

        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("non-Whero submodule", rejected.stderr)

    def test_non_git_source_rejects_a_changed_path(self) -> None:
        self.write_source("provider/a.md")
        self.assert_succeeded(self.run_builder("provider/a.md"))

        other_source = self.root / "other" / "whero-wiki"
        self.create_wiki(other_source)
        self.write_source("provider/a.md", source=other_source)
        result = self.run_builder("provider/a.md", source=other_source)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("uses a different source", result.stderr)

    def git(self, repository: Path, *arguments: str) -> None:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def commit_all(self, repository: Path, message: str) -> str:
        self.git(repository, "add", "-A")
        self.git(repository, "commit", "-qm", message)
        result = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def create_git_source_pair(self) -> tuple[Path, Path, Path, Path]:
        first_repository = self.root / "first-repository"
        first_source = first_repository / "whero-wiki"
        self.create_wiki(first_source)
        self.write_source("a.md", source=first_source)
        self.write_source("b.md", source=first_source)
        self.git(first_repository, "init", "-q")
        self.git(first_repository, "config", "user.name", "Test User")
        self.git(first_repository, "config", "user.email", "test@example.com")
        self.git(first_repository, "add", "whero-wiki")
        self.git(first_repository, "commit", "-qm", "initial")

        second_repository = self.root / "second-repository"
        shutil.copytree(first_repository, second_repository, symlinks=True)
        return (
            first_repository,
            first_source,
            second_repository,
            second_repository / "whero-wiki",
        )

    def test_git_relocation_recovers_mixed_old_and_new_links(self) -> None:
        _, first_source, _, second_source = self.create_git_source_pair()
        self.assert_succeeded(
            self.run_builder("a.md", "b.md", source=first_source)
        )

        output = self.target / "whero-wiki"
        migrated_early = output / "a.md"
        migrated_early.unlink()
        migrated_early.symlink_to(
            os.path.relpath(second_source / "a.md", start=migrated_early.parent)
        )

        result = self.run_builder("b.md", source=second_source)
        self.assert_succeeded(result)
        self.assertEqual((output / "a.md").resolve(), (second_source / "a.md").resolve())
        self.assertEqual((output / "b.md").resolve(), (second_source / "b.md").resolve())
        status = (output / "partial-disclosure.md").read_text(encoding="utf-8")
        expected_source = os.path.relpath(second_source, start=output)
        self.assertIn(f'source: "{expected_source}"', status)
        self.assertIn("source_validation: git-commit", status)
        self.assertIn('source_git_path: "whero-wiki"', status)

    def test_git_remote_is_recorded_without_credentials(self) -> None:
        repository = self.root / "remote-repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("a.md", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        self.git(
            repository,
            "remote",
            "add",
            "origin",
            "https://secret-token@github.com/example/wiki.git",
        )
        self.commit_all(repository, "initial")

        result = self.run_builder("a.md", source=source)

        self.assert_succeeded(result)
        status = (self.target / "whero-wiki" / "partial-disclosure.md").read_text(
            encoding="utf-8"
        )
        self.assertIn('source_git_remote_name: "origin"', status)
        self.assertIn(
            'source_git_remote_url: "https://github.com/example/wiki.git"',
            status,
        )
        self.assertIn(
            'source_git_remote_normalized: "github.com/example/wiki"',
            status,
        )
        self.assertNotIn("secret-token", status)

    def test_git_relocation_dry_run_does_not_rewrite_links_or_status(self) -> None:
        _, first_source, _, second_source = self.create_git_source_pair()
        self.assert_succeeded(self.run_builder("a.md", source=first_source))
        output = self.target / "whero-wiki"
        status_path = output / "partial-disclosure.md"
        original_status = status_path.read_text(encoding="utf-8")

        result = self.run_builder("b.md", source=second_source, dry_run=True)

        self.assert_succeeded(result)
        self.assertIn("2 source relink(s)", result.stdout)
        self.assertNotIn("would relink", result.stdout)
        self.assertEqual((output / "a.md").resolve(), (first_source / "a.md").resolve())
        self.assertFalse((output / "b.md").exists())
        self.assertEqual(status_path.read_text(encoding="utf-8"), original_status)

    def test_forward_git_change_outside_disclosure_is_accepted(self) -> None:
        _, first_source, second_repository, second_source = (
            self.create_git_source_pair()
        )
        self.assert_succeeded(self.run_builder("a.md", source=first_source))
        self.write_source("c.md", source=second_source)
        self.git(second_repository, "add", "whero-wiki/c.md")
        self.git(second_repository, "commit", "-qm", "different")

        result = self.run_builder("a.md", source=second_source)

        self.assert_succeeded(result)
        self.assertIn("Git source advanced", result.stdout)
        self.assertIn("outside its roots", result.stdout)
        self.assertEqual(
            (self.target / "whero-wiki" / "a.md").resolve(),
            (second_source / "a.md").resolve(),
        )

    def test_forward_content_change_outside_disclosure_is_accepted(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("selected.md", "selected\n", source=source)
        self.write_source("outside.md", "first\n", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        self.commit_all(repository, "initial")
        self.assert_succeeded(self.run_builder("selected.md", source=source))

        self.write_source("outside.md", "second\n", source=source)
        new_commit = self.commit_all(repository, "outside content")
        result = self.run_builder("selected.md", source=source)

        self.assert_succeeded(result)
        self.assertIn("source change(s) remain outside its roots", result.stdout)
        status = (self.target / "whero-wiki" / "partial-disclosure.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(f'source_commit: "{new_commit}"', status)

    def test_forward_content_change_inside_disclosure_requires_repair(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("a.md", "first\n", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        recorded_commit = self.commit_all(repository, "initial")
        self.assert_succeeded(self.run_builder("a.md", source=source))

        self.write_source("a.md", "second\n", source=source)
        new_commit = self.commit_all(repository, "content only")
        result = self.run_builder("a.md", source=source)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("disclosed content or structure", result.stderr)
        self.assertIn("content-changed=1", result.stderr)
        self.assertIn("possible handling:", result.stderr)
        self.assertIn("repair or rebuild", result.stderr)
        self.assertIn("read-through symlinks may already expose", result.stderr)
        self.assertNotIn("diff --git", result.stdout + result.stderr)
        status = (self.target / "whero-wiki" / "partial-disclosure.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(f'source_commit: "{recorded_commit}"', status)
        self.assertNotIn(f'source_commit: "{new_commit}"', status)

    def test_selected_untracked_file_is_rejected_for_git_identity(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("tracked.md", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        self.commit_all(repository, "initial")
        self.write_source("untracked.md", source=source)

        result = self.run_builder("untracked.md", source=source)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stable disclosure identity", result.stderr)
        self.assertIn("untracked=1", result.stderr)
        self.assertFalse((self.target / "whero-wiki").exists())

    def test_untracked_file_outside_selection_is_allowed(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("selected.md", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        self.commit_all(repository, "initial")
        self.write_source("outside.md", source=source)

        result = self.run_builder("selected.md", source=source)

        self.assert_succeeded(result)
        self.assertTrue((self.target / "whero-wiki" / "selected.md").is_symlink())

    def test_tracked_content_modification_outside_selection_is_allowed(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("selected.md", source=source)
        self.write_source("outside.md", "first\n", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        self.commit_all(repository, "initial")
        self.write_source("outside.md", "second\n", source=source)

        result = self.run_builder("selected.md", source=source)

        self.assert_succeeded(result)
        self.assertTrue((self.target / "whero-wiki" / "selected.md").is_symlink())

    def test_selected_ignored_file_is_rejected_for_git_identity(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("tracked.md", source=source)
        self.write_source(".gitignore", "ignored.md\n", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        self.commit_all(repository, "initial")
        self.write_source("ignored.md", source=source)

        result = self.run_builder("ignored.md", source=source)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stable disclosure identity", result.stderr)
        self.assertIn("ignored=1", result.stderr)

    def test_selected_untracked_empty_directory_is_rejected_for_git_identity(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("tracked.md", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        self.commit_all(repository, "initial")
        (source / "empty").mkdir()

        result = self.run_builder("empty", source=source)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stable disclosure identity", result.stderr)
        self.assertIn("untracked-root=1", result.stderr)

    def test_selected_tracked_content_modification_requires_repair(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("selected.md", "first\n", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        commit = self.commit_all(repository, "initial")
        self.assert_succeeded(self.run_builder("selected.md", source=source))
        status_path = self.target / "whero-wiki" / "partial-disclosure.md"
        previous_status = status_path.read_text(encoding="utf-8")
        self.write_source("selected.md", "second\n", source=source)

        result = self.run_builder("selected.md", source=source)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stable disclosure identity", result.stderr)
        self.assertIn("worktree-content-changed=1", result.stderr)
        self.assertIn("possible handling:", result.stderr)
        self.assertIn("commit the intended source state or restore", result.stderr)
        self.assertIn("read-through symlinks may already expose", result.stderr)
        self.assertEqual(status_path.read_text(encoding="utf-8"), previous_status)
        self.assertIn(f'source_commit: "{commit}"', previous_status)
        self.assertEqual(
            (self.target / "whero-wiki" / "selected.md").read_text(encoding="utf-8"),
            "second\n",
        )

    def test_selected_executable_bit_change_is_allowed(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        selected = self.write_source("selected.md", "content\n", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        self.git(repository, "config", "core.filemode", "true")
        commit = self.commit_all(repository, "initial")
        selected.chmod(selected.stat().st_mode | 0o111)

        result = self.run_builder("selected.md", source=source)

        self.assert_succeeded(result)
        status = (self.target / "whero-wiki" / "partial-disclosure.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(f'source_commit: "{commit}"', status)

    def test_forward_structural_change_inside_directory_root_stops(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("provider/a.md", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        recorded_commit = self.commit_all(repository, "initial")
        self.assert_succeeded(self.run_builder("provider", source=source))
        status_path = self.target / "whero-wiki" / "partial-disclosure.md"
        previous_status = status_path.read_text(encoding="utf-8")

        self.write_source("provider/b.md", source=source)
        new_commit = self.commit_all(repository, "add disclosed child")
        result = self.run_builder("provider", source=source)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forward Git update changes the disclosed structure", result.stderr)
        self.assertIn("disclosed roots [provider]", result.stderr)
        self.assertIn("added=1", result.stderr)
        self.assertIn("possible handling:", result.stderr)
        self.assertIn("git -C", result.stderr)
        self.assertNotIn("diff --git", result.stderr)
        self.assertEqual(status_path.read_text(encoding="utf-8"), previous_status)
        self.assertIn(f'source_commit: "{recorded_commit}"', previous_status)
        self.assertNotIn(new_commit, previous_status)

    def test_non_forward_git_history_stops_before_diff_analysis(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("a.md", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        self.commit_all(repository, "base")
        self.git(repository, "branch", "right")

        self.write_source("left.md", source=source)
        self.commit_all(repository, "left branch")
        self.assert_succeeded(self.run_builder("a.md", source=source))
        previous_status = (
            self.target / "whero-wiki" / "partial-disclosure.md"
        ).read_text(encoding="utf-8")

        self.git(repository, "checkout", "-q", "right")
        self.write_source("right.md", source=source)
        self.commit_all(repository, "right branch")
        result = self.run_builder("a.md", source=source)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not an accepted forward update", result.stderr)
        self.assertIn("structural diff analysis was skipped", result.stderr)
        self.assertIn("no repair plan was generated", result.stderr)
        self.assertNotIn("possible handling:", result.stderr)
        self.assertNotIn("inspect with:", result.stderr)
        self.assertEqual(
            (self.target / "whero-wiki" / "partial-disclosure.md").read_text(
                encoding="utf-8"
            ),
            previous_status,
        )

    def test_backward_git_commit_stops_before_diff_analysis(self) -> None:
        repository = self.root / "repository"
        source = repository / "whero-wiki"
        self.create_wiki(source)
        self.write_source("a.md", source=source)
        self.git(repository, "init", "-q")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")
        old_commit = self.commit_all(repository, "initial")
        self.write_source("later.md", source=source)
        self.commit_all(repository, "later")
        self.assert_succeeded(self.run_builder("a.md", source=source))

        self.git(repository, "checkout", "-q", old_commit)
        result = self.run_builder("a.md", source=source)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not an accepted forward update", result.stderr)
        self.assertIn("structural diff analysis was skipped", result.stderr)
        self.assertNotIn("inspect with:", result.stderr)


if __name__ == "__main__":
    unittest.main()
