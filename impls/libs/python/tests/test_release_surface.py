from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from whero.doctidex.git.storage import cache_root
from whero.doctidex.protocol.document import DoctidexDocument

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
VERSION_PATTERN = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
PROTOCOL_PATTERN = re.compile(r"^版本：`v(?P<version>[0-9]+\.[0-9]+\.[0-9]+)`$", re.MULTILINE)
SKILL_NAMES = {
    "doctidex-git-overview",
    "doctidex-git-mentions",
    "doctidex-git-read",
    "doctidex-git-maintenance",
}


def _version_parts(version: str) -> tuple[int, int, int]:
    match = VERSION_PATTERN.fullmatch(version)
    assert match is not None
    return tuple(int(value) for value in match.groups())


def _release_facts() -> None:
    protocol_text = (REPOSITORY_ROOT / "spec" / "overview.md").read_text(encoding="utf-8")
    protocol_match = PROTOCOL_PATTERN.search(protocol_text)
    assert protocol_match is not None
    protocol_version = protocol_match.group("version")

    with (REPOSITORY_ROOT / "impls" / "libs" / "python" / "pyproject.toml").open("rb") as handle:
        package = tomllib.load(handle)["project"]
    assert package["name"] == "whero-doctidex"
    package_version = package["version"]

    plugin = json.loads(
        (REPOSITORY_ROOT / "impls" / "agent-plugins" / "doctidex-git" / ".codex-plugin" / "plugin.json").read_text(
            encoding="utf-8"
        )
    )
    assert plugin["name"] == "doctidex-git"
    plugin_version = plugin["version"]

    assert package_version == "1.0.0"
    assert plugin_version == "1.0.0"
    assert _version_parts(protocol_version)[0] == _version_parts(package_version)[0]
    assert _version_parts(protocol_version)[0] == _version_parts(plugin_version)[0]


def test_release_metadata_is_current_and_major_compatible() -> None:
    _release_facts()


def test_published_skills_exclude_release_and_package_installation_guidance() -> None:
    skills_root = REPOSITORY_ROOT / "impls" / "agent-plugins" / "doctidex-git" / "skills"
    skill_paths = sorted(skills_root.glob("*/SKILL.md"))

    assert {path.parent.name for path in skill_paths} == SKILL_NAMES
    for path in skill_paths:
        text = path.read_text(encoding="utf-8")
        assert "## Product Version" not in text
        assert "This Skill uses doctidex protocol" not in text
        assert "Python distribution" not in text
        assert "git+https://github.com/Viennan/doctidex.git@" not in text
        assert "whero-doctidex @ git+" not in text


def test_readmes_keep_the_install_target_parameterized() -> None:
    package_install_command = (
        "whero-doctidex @ git+https://github.com/Viennan/doctidex.git"
        "@v<TARGET_DOCTIDEX_GIT_VERSION>#subdirectory=impls/libs/python"
    )
    bundle_checkout_command = "git clone --depth 1 --branch v<TARGET_DOCTIDEX_GIT_VERSION>"
    bundle_path = "impls/agent-plugins/doctidex-git/skills/"
    english = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (REPOSITORY_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    index = (REPOSITORY_ROOT / "index.md").read_text(encoding="utf-8")

    assert "README.zh-CN.md" in english
    assert "README.md" in chinese
    assert package_install_command in english
    assert package_install_command in chinese
    assert bundle_checkout_command in english
    assert bundle_checkout_command in chinese
    assert bundle_path in english
    assert bundle_path in chinese
    assert ".codex-plugin" in english
    assert ".codex-plugin" in chinese
    assert "doctidex-git-overview" in english
    assert "doctidex-git-overview" in chinese
    assert "not required by other agent hosts" in english
    assert "不是其他 agent host 的前提" in chinese
    assert "README.md" in index
    assert "README.zh-CN.md" in index


def test_root_declares_doctidex_runtime_state_unsafe() -> None:
    document = DoctidexDocument.load(REPOSITORY_ROOT / "index.md")
    unsafe_entries = document.doctidex["unsafe"]
    assert {entry["path"] for entry in unsafe_entries} >= {".doctidex"}


def test_user_cache_override_is_process_local(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DOCTIDEX_GIT_CACHE", raising=False)
    assert cache_root().name == "doctidex-git"

    selected_cache = tmp_path / "selected-cache"
    monkeypatch.setenv("DOCTIDEX_GIT_CACHE", str(selected_cache))
    assert cache_root() == selected_cache.absolute()
