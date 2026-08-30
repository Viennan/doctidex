"""Effective doctidex-git configuration for one CLI invocation."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from whero.doctidex.errors import CommandFailure
from whero.doctidex.store.files import atomic_write_bytes

_DEFAULT_HOME = Path.home() / ".doctidex-git"
_CACHE_PATH_KEY = "cache-path"
_DEFAULT_CACHE_PATH = "cache"


@dataclass(frozen=True, slots=True)
class Config:
    """One invocation's resolved home and merged configuration options."""

    home: Path
    options: Mapping[str, object]
    sources: Mapping[str, str]
    repository_config_dir: Path | None

    @property
    def cache_path(self) -> Path:
        """Return the resolved cache data root from the merged options."""

        value = self.options.get(_CACHE_PATH_KEY, _DEFAULT_CACHE_PATH)
        base = self.home
        if self.sources.get(_CACHE_PATH_KEY) == "repository" and self.repository_config_dir is not None:
            base = self.repository_config_dir
        return _resolve_cache_path(base, value)

    def __post_init__(self) -> None:
        _ = self.cache_path

    @classmethod
    def from_environment(cls, git_root: Path | None = None) -> Config:
        """Read and merge global and repository config, auto-creating the global file."""

        home = _resolve_home()
        _ensure_global_config(home)
        global_document = _read_config(home / "config.toml", source="global")
        repository_path = _repository_config_path(git_root)
        repository_document = (
            _read_config(repository_path, source="repository")
            if repository_path is not None and repository_path.is_file()
            else {}
        )
        options = {**global_document, **repository_document}
        sources = {
            **_source_map(global_document, "global"),
            **_source_map(repository_document, "repository"),
        }
        return cls(
            home=home,
            options=MappingProxyType(options),
            sources=MappingProxyType(sources),
            repository_config_dir=repository_path.parent if repository_path is not None else None,
        )


def _resolve_home() -> Path:
    return Path(os.environ.get("DOCTIDEX-GIT-HOME", str(_DEFAULT_HOME))).expanduser()


def _ensure_global_config(home: Path) -> None:
    config_path = home / "config.toml"
    if config_path.exists():
        return
    atomic_write_bytes(config_path, b"", store="config", phase="initialize")


def _repository_config_path(git_root: Path | None) -> Path | None:
    if git_root is None:
        return None
    return git_root / ".doctidex-git" / "config.toml"


def _source_map(document: dict[str, object], source: str) -> dict[str, str]:
    return {key: source for key in document}


def _read_config(path: Path, *, source: str) -> dict[str, object]:
    try:
        text = path.read_text()
    except OSError as exc:
        raise _config_failure(source, "read") from exc
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise _config_failure(source, "parse") from exc
    if not isinstance(document, dict):
        raise _config_failure(source, "shape")
    return document


def _resolve_cache_path(base: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise CommandFailure(
            code="config.invalid",
            summary="The doctidex-git configuration does not contain a usable cache path.",
            subject={"kind": "config"},
            details={"key": _CACHE_PATH_KEY},
        )
    candidate = Path(value).expanduser()
    return candidate if candidate.is_absolute() else base / candidate


def _config_failure(source: str, phase: str) -> CommandFailure:
    return CommandFailure(
        code="config.invalid",
        summary="The doctidex-git configuration could not be read.",
        subject={"kind": "config"},
        details={"source": source, "phase": phase},
    )


__all__ = ["Config"]
