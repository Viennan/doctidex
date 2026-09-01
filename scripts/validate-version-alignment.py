"""Verify that the tracked doctidex-git version projections agree."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import tomllib
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC_PYTHON = ROOT / "src" / "python"
PYPROJECT = SRC_PYTHON / "pyproject.toml"
INIT = SRC_PYTHON / "whero" / "doctidex" / "__init__.py"
SKILL = ROOT / "skills" / "doctidex-git" / "SKILL.md"


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
    raise ValueError(f"__version__ not found in {path}")


def _skill_version(path: Path) -> str:
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"YAML frontmatter not found in {path}")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise ValueError(f"YAML frontmatter not found in {path}")
    data = yaml.safe_load(parts[1])
    version = data["doctidex"]["version"]
    if not isinstance(version, str):
        raise TypeError(f"doctidex.version is not a string in {path}")
    return version


def _versions() -> dict[str, str]:
    pyproject = tomllib.loads(PYPROJECT.read_text())
    return {
        "pyproject": pyproject["project"]["version"],
        "__init__": _module_version(INIT),
        "skill": _skill_version(SKILL),
    }


def main() -> int:
    versions = _versions()
    if len(set(versions.values())) == 1:
        return 0
    for name, version in versions.items():
        print(f"{name}: {version}", file=sys.stderr)
    print("doctidex-git version projections disagree", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
