from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

_ROOT = Path(__file__).resolve().parent
_SKILL_SOURCE = _ROOT.parent.parent / "skills" / "doctidex-git"
_SKILL_TARGET = _ROOT / "whero" / "doctidex" / "_skill_data" / "doctidex-git"


def _materialize_skill_data() -> None:
    if _SKILL_TARGET.exists():
        shutil.rmtree(_SKILL_TARGET)
    shutil.copytree(_SKILL_SOURCE, _SKILL_TARGET)


class BuildPy(build_py):
    """Materialize the bundled Twin Skill before building package data."""

    def run(self) -> None:
        _materialize_skill_data()
        super().run()


setup(cmdclass={"build_py": BuildPy})
