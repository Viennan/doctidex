"""Resolve and install the bundled doctidex-git Twin Skills."""

from __future__ import annotations

import shutil
from importlib.resources import files
from pathlib import Path

from whero.doctidex.errors import CommandFailure

SKILL_NAME = "doctidex-git"
_SOURCE_SKILLS = Path(__file__).resolve().parents[4] / "skills"
_PACKAGED_SKILLS = files("whero.doctidex") / "_skill_data"


def resolve_skill_root() -> Path:
    """Return the directory that contains the bundled Twin Skills."""

    if _has_skill_tree(_SOURCE_SKILLS):
        return _SOURCE_SKILLS

    packaged = Path(str(_PACKAGED_SKILLS))
    if _has_skill_tree(packaged):
        return packaged

    raise _unavailable()


def install_skills(destination: Path) -> tuple[tuple[str, ...], Path]:
    """Install every bundled Twin Skill under ``destination``.

    Return the installed skill names and the normalized destination.
    """

    root = resolve_skill_root()
    destination = destination.expanduser().resolve()
    _prepare_destination(destination)

    installed: list[str] = []
    for skill in sorted(path for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")):
        _replace_skill(skill, destination / skill.name)
        installed.append(skill.name)

    if not installed:
        raise _unavailable()
    return tuple(installed), destination


def _prepare_destination(destination: Path) -> None:
    if destination.exists() and not destination.is_dir():
        raise _target_failure(destination, "target-is-file")
    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise _target_failure(destination, "create-failed") from exc


def _replace_skill(source: Path, target: Path) -> None:
    if target.exists() and not target.is_dir():
        raise _target_failure(target, "target-is-file")
    if target.exists():
        try:
            shutil.rmtree(target)
        except OSError as exc:
            raise _target_failure(target, "replace-failed") from exc
    try:
        shutil.copytree(source, target)
    except OSError as exc:
        raise CommandFailure(
            code="skills.install.unavailable",
            summary="The bundled Twin Skill could not be copied.",
            subject={"kind": "skill", "skill": source.name},
            details={"operation": "copy", "path": str(target)},
        ) from exc


def _unavailable() -> CommandFailure:
    return CommandFailure(
        code="skills.install.unavailable",
        summary="The bundled doctidex-git Twin Skills are unavailable.",
        subject={"kind": "skills"},
        details={},
    )


def _target_failure(path: Path, reason: str) -> CommandFailure:
    return CommandFailure(
        code="skills.install.target.unavailable",
        summary="The skill install destination is not usable.",
        subject={"kind": "skills-path", "path": str(path)},
        details={"reason": reason},
    )


def _has_skill_tree(root: Path) -> bool:
    return (root / SKILL_NAME / "SKILL.md").is_file()


__all__ = ["SKILL_NAME", "install_skills", "resolve_skill_root"]
