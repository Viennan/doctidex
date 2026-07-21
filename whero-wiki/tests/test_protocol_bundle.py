from __future__ import annotations

import argparse
import importlib
import pkgutil
import unittest
from pathlib import Path

from support import FORMAT_VERSION, SCRIPTS, SKILL_ROOT

from whero_wiki_tools.cli import VALIDATION_MODES, build_parser
from whero_wiki_tools.curated import validate_wiki
from whero_wiki_tools.frontmatter import read_markdown
from whero_wiki_tools.model import CURATED_FORMAT_VERSION
from whero_wiki_tools.view_types import (
    ExistingStatus,
    OperationResult,
    ViewPlan,
    ViewRequest,
)


SPEC_FILES = {
    "conformance.md",
    "external-references.md",
    "links.md",
    "preserved-boundaries.md",
    "terminology.md",
    "views.md",
    "wiki-model.md",
}


def subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    action = next(
        item
        for item in parser._actions
        if isinstance(item, argparse._SubParsersAction)
    )
    return action.choices


class ProtocolBundleTests(unittest.TestCase):
    def test_english_and_chinese_protocol_trees_match(self) -> None:
        english = {
            path.name
            for path in (SKILL_ROOT / "spec").glob("*.md")
        }
        chinese = {
            path.name
            for path in (SKILL_ROOT / "spec" / "CN").glob("*.md")
        }

        self.assertEqual(english, SPEC_FILES)
        self.assertEqual(chinese, SPEC_FILES)

    def test_every_protocol_document_declares_v002(self) -> None:
        english_status = f"Protocol status: **v{FORMAT_VERSION} active**."
        chinese_status = f"协议状态：**v{FORMAT_VERSION} 当前版本**。"

        for name in sorted(SPEC_FILES):
            with self.subTest(language="English", name=name):
                self.assertIn(
                    english_status,
                    (SKILL_ROOT / "spec" / name).read_text(encoding="utf-8"),
                )
            with self.subTest(language="Chinese", name=name):
                self.assertIn(
                    chinese_status,
                    (SKILL_ROOT / "spec" / "CN" / name).read_text(
                        encoding="utf-8"
                    ),
                )

    def test_skill_routes_every_protocol_pair_and_operational_reference(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in sorted(SPEC_FILES):
            self.assertIn(f"spec/{name}", skill)
            self.assertIn(f"spec/CN/{name}", skill)
        for name in (
            "curated-knowledge.md",
            "curated-review-agent-prompt.md",
            "external-references.md",
            "links.md",
            "project-knowledge.md",
            "view-workflows.md",
        ):
            self.assertIn(f"references/{name}", skill)

    def test_runtime_and_curated_formats_share_the_same_version(self) -> None:
        self.assertEqual(FORMAT_VERSION, "0.0.2")
        self.assertEqual(CURATED_FORMAT_VERSION, FORMAT_VERSION)
        self.assertEqual(
            read_markdown(SKILL_ROOT / "whero-wiki-meta.md").fields[
                "format_version"
            ],
            FORMAT_VERSION,
        )

    def test_cli_exposes_only_current_validation_profiles_and_link_commands(self) -> None:
        parser = build_parser()
        commands = subcommands(parser)
        links = subcommands(commands["links"])
        curated_options = {
            option
            for action in commands["init-curated"]._actions
            for option in action.option_strings
        }

        self.assertEqual(VALIDATION_MODES, ("auto", "full", "view"))
        self.assertEqual(set(links), {"list", "broken", "graph", "inbound"})
        self.assertIn("view", commands)
        self.assertIn("restore", commands)
        self.assertIn("--section", curated_options)

    def test_view_api_uses_structured_request_plan_and_result_types(self) -> None:
        self.assertIn("requested_selections", ViewPlan.__dataclass_fields__)
        self.assertIn("effective_roots", ExistingStatus.__dataclass_fields__)
        self.assertIn("relink_plan", ViewPlan.__dataclass_fields__)
        self.assertIn("allow_path_relocation", ViewRequest.__dataclass_fields__)
        self.assertIn("mutated", OperationResult.__dataclass_fields__)

    def test_all_runtime_modules_import_from_the_portable_skill_root(self) -> None:
        package = importlib.import_module("whero_wiki_tools")
        imported = []
        for module in pkgutil.iter_modules(package.__path__):
            imported.append(importlib.import_module(f"whero_wiki_tools.{module.name}"))

        self.assertGreaterEqual(len(imported), 15)
        self.assertTrue((SCRIPTS / "build_view.py").is_file())
        self.assertTrue((SCRIPTS / "whero_wiki.py").is_file())

    def test_self_hosted_product_wiki_validates_in_full_mode(self) -> None:
        diagnostics = validate_wiki(SKILL_ROOT, mode="full")

        self.assertFalse(diagnostics.has_errors, diagnostics.render_text())
