from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[3]
_SRC_PYTHON = _ROOT / "src" / "python"


def _module_version(path: Path) -> str:
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__version__":
                value = ast.literal_eval(node.value)
                if isinstance(value, str):
                    return value
    raise AssertionError(f"__version__ not found in {path}")


def _skill_version(path: Path) -> str:
    text = path.read_text()
    parts = text.split("---", 2)
    data = yaml.safe_load(parts[1])
    return data["doctidex"]["version"]


def test_version_projections_agree() -> None:
    pyproject = tomllib.loads((_SRC_PYTHON / "pyproject.toml").read_text())["project"]["version"]
    init = _module_version(_SRC_PYTHON / "whero" / "doctidex" / "__init__.py")
    skill = _skill_version(_ROOT / "skills" / "doctidex-git" / "SKILL.md")

    assert pyproject == init == skill
