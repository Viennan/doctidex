"""Domain records and tracked/runtime state projections for doctidex-git."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Literal


class ModelFormatError(ValueError):
    """Raised when a persisted model document cannot be reconstructed."""

    def __init__(self, artifact: str, expected_shape: str) -> None:
        super().__init__(f"{artifact} does not match {expected_shape}")
        self.artifact = artifact
        self.expected_shape = expected_shape


def _mapping(value: object, *, artifact: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ModelFormatError(artifact, "an object")
    return value


def _list(value: object, *, artifact: str) -> list[object]:
    if not isinstance(value, list):
        raise ModelFormatError(artifact, "an array")
    return value


def _string(value: Mapping[str, Any], field: str, *, artifact: str, path: bool = False) -> str:
    candidate = value.get(field)
    if not isinstance(candidate, str) or (path and not candidate.startswith("/")):
        expected = f"a string field {field!r}"
        if path:
            expected += " containing a repository-internal absolute path"
        raise ModelFormatError(artifact, expected)
    return candidate


@dataclass(frozen=True, slots=True)
class Installation:
    """An installed external Git revision and its persisted metadata."""

    tracked: bool
    git_url: str
    commit_hash: str
    install_id: str
    install_path: str
    keys: tuple[str, ...]
    branch: str = ""
    tag: str = ""
    import_by_installations: tuple[str, ...] = ()
    presentation_path: str | None = None

    @classmethod
    def from_json(cls, value: object, *, artifact: str) -> Installation:
        record = _mapping(value, artifact=artifact)
        tracked = record.get("tracked")
        keys = record.get("keys")
        if not isinstance(tracked, bool):
            raise ModelFormatError(artifact, "an installation with a boolean tracked field")
        if not isinstance(keys, list) or not all(isinstance(item, str) for item in keys):
            raise ModelFormatError(artifact, "an installation with a string keys array")
        branch = _string(record, "branch", artifact=artifact)
        tag = _string(record, "tag", artifact=artifact)
        if branch and tag:
            raise ModelFormatError(artifact, "an installation with one revision selector")
        return cls(
            tracked=tracked,
            git_url=_string(record, "git-url", artifact=artifact),
            commit_hash=_string(record, "commit-hash", artifact=artifact),
            install_id=_string(record, "install-id", artifact=artifact),
            install_path=_string(record, "install-path", artifact=artifact, path=True),
            keys=tuple(keys),
            branch=branch,
            tag=tag,
            import_by_installations=(),
            presentation_path=None,
        )

    def to_json(self) -> dict[str, object]:
        return {
            "tracked": self.tracked,
            "git-url": self.git_url,
            "commit-hash": self.commit_hash,
            "install-id": self.install_id,
            "install-path": self.install_path,
            "keys": list(self.keys),
            "branch": self.branch,
            "tag": self.tag,
        }


@dataclass(frozen=True, slots=True)
class Ref:
    """A managed symbolic reference into an Installation."""

    install_id: str
    src_sub_dir: str
    target_dir: str

    @classmethod
    def from_json(cls, value: object, *, artifact: str) -> Ref:
        record = _mapping(value, artifact=artifact)
        src_sub_dir = _string(record, "src-sub-dir", artifact=artifact)
        if src_sub_dir and not src_sub_dir.startswith("/"):
            raise ModelFormatError(
                artifact,
                "a ref with an empty or repository-internal absolute src-sub-dir",
            )
        return cls(
            install_id=_string(record, "install-id", artifact=artifact),
            src_sub_dir=src_sub_dir,
            target_dir=_string(record, "target-dir", artifact=artifact, path=True),
        )

    def to_json(self) -> dict[str, str]:
        return {
            "install-id": self.install_id,
            "src-sub-dir": self.src_sub_dir,
            "target-dir": self.target_dir,
        }


BoundaryPointType = Literal["custom", "import", "import-ref", "worktree"]


@dataclass(frozen=True, slots=True)
class BoundaryPoint:
    """A custom or model-derived doctidex boundary point."""

    type: BoundaryPointType
    path: str

    @classmethod
    def from_json(cls, value: object, *, artifact: str) -> BoundaryPoint:
        record = _mapping(value, artifact=artifact)
        kind = _string(record, "type", artifact=artifact)
        if kind not in {"custom", "import", "import-ref", "worktree"}:
            raise ModelFormatError(artifact, "a boundary point with a known type")
        return cls(type=kind, path=_string(record, "path", artifact=artifact, path=True))

    def to_json(self) -> dict[str, str]:
        return {"type": self.type, "path": self.path}


@dataclass(frozen=True, slots=True)
class InlineAnnotation:
    """A valid doctidex structured annotation attached to one Markdown link."""

    cross_boundary_point: str


@dataclass(frozen=True, slots=True)
class Worktree:
    """A managed Git worktree and the external source it represents."""

    url: str
    install_id: str | None
    base_commit_hash: str
    work_path: str

    @classmethod
    def from_json(cls, value: object, *, artifact: str) -> Worktree:
        record = _mapping(value, artifact=artifact)
        install_id = record.get("install-id")
        if install_id is not None and not isinstance(install_id, str):
            raise ModelFormatError(artifact, "a worktree with a string or null install-id")
        return cls(
            url=_string(record, "url", artifact=artifact),
            install_id=install_id,
            base_commit_hash=_string(record, "base-commit-hash", artifact=artifact),
            work_path=_string(record, "work-path", artifact=artifact, path=True),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "url": self.url,
            "install-id": self.install_id,
            "base-commit-hash": self.base_commit_hash,
            "work-path": self.work_path,
        }


class CacheItemStatus(StrEnum):
    """Internal CacheStore publication state."""

    PREPARING = "preparing"
    PUBLISHED = "published"


@dataclass(frozen=True, slots=True)
class CacheItem:
    """An internal CacheStore record for one Git URL."""

    status: CacheItemStatus
    git_url: str
    path: str

    @classmethod
    def from_json(cls, value: object, *, artifact: str) -> CacheItem:
        record = _mapping(value, artifact=artifact)
        return cls(
            git_url=_string(record, "git-url", artifact=artifact),
            path=_string(record, "path", artifact=artifact),
            status=_cache_item_status(record.get("status"), artifact=artifact),
        )

    def to_json(self) -> dict[str, str]:
        return {"status": self.status.value, "git-url": self.git_url, "path": self.path}


def _cache_item_status(value: object, *, artifact: str) -> CacheItemStatus:
    try:
        return CacheItemStatus(value)
    except ValueError as exc:
        raise ModelFormatError(artifact, "a cache item with status preparing or published") from exc


@dataclass(frozen=True, slots=True)
class RuntimeState:
    """The complete in-memory RuntimeStore state reconstructed from its projections."""

    custom_boundary_points: tuple[BoundaryPoint, ...]
    installations: tuple[Installation, ...]
    refs: tuple[Ref, ...]
    worktrees: tuple[Worktree, ...]

    @property
    def boundary_points(self) -> tuple[BoundaryPoint, ...]:
        """Return custom points together with points derived from managed records."""

        return (
            *self.custom_boundary_points,
            *(BoundaryPoint(type="import", path=item.install_path) for item in self.installations),
            *(BoundaryPoint(type="import-ref", path=item.target_dir) for item in self.refs),
            *(BoundaryPoint(type="worktree", path=item.work_path) for item in self.worktrees),
        )

    @classmethod
    def empty(cls) -> RuntimeState:
        return cls(custom_boundary_points=(), installations=(), refs=(), worktrees=())

    @classmethod
    def from_documents(
        cls,
        *,
        boundary_set: object,
        imports: object,
        import_refs: object,
        runtime: object,
    ) -> RuntimeState:
        boundaries = tuple(
            BoundaryPoint.from_json(item, artifact="boundary-set.json")
            for item in _list(boundary_set, artifact="boundary-set.json")
        )
        if any(item.type != "custom" for item in boundaries):
            raise ModelFormatError("boundary-set.json", "an array of custom boundary points")

        tracked = tuple(
            Installation.from_json(item, artifact="imports.json") for item in _list(imports, artifact="imports.json")
        )
        if any(not item.tracked for item in tracked):
            raise ModelFormatError("imports.json", "an array of tracked installations")

        refs = tuple(
            Ref.from_json(item, artifact="import-refs.json") for item in _list(import_refs, artifact="import-refs.json")
        )
        runtime_record = _mapping(runtime, artifact="runtime.json")
        untracked = tuple(
            Installation.from_json(item, artifact="runtime.json")
            for item in _list(runtime_record.get("imports"), artifact="runtime.json")
        )
        if any(item.tracked for item in untracked):
            raise ModelFormatError("runtime.json", "untracked installation records")
        worktrees = tuple(
            Worktree.from_json(item, artifact="runtime.json")
            for item in _list(runtime_record.get("worktrees"), artifact="runtime.json")
        )
        installations = (*tracked, *untracked)
        installations = _with_derived_import_by_installations(installations)
        return cls(
            custom_boundary_points=boundaries,
            installations=installations,
            refs=refs,
            worktrees=worktrees,
        )

    def to_documents(self) -> dict[str, object]:
        return {
            "boundary-set.json": [item.to_json() for item in self.custom_boundary_points],
            "imports.json": [item.to_json() for item in self.installations if item.tracked],
            "import-refs.json": [item.to_json() for item in self.refs],
            "runtime.json": {
                "imports": [item.to_json() for item in self.installations if not item.tracked],
                "worktrees": [item.to_json() for item in self.worktrees],
            },
        }


def _with_derived_import_by_installations(
    installations: tuple[Installation, ...],
) -> tuple[Installation, ...]:
    """Attach the runtime-only import-parent relation to each Installation.

    Stage 1 keeps the relation empty until later phases introduce Installation context and parent
    import declarations. The field must remain absent from ``Installation.to_json``.
    """

    relations = _derived_installation_importers(installations)
    return tuple(replace(item, import_by_installations=relations[item.install_id]) for item in installations)


def _derived_installation_importers(
    installations: tuple[Installation, ...],
) -> dict[str, tuple[str, ...]]:
    """Placeholder for deriving Installation import-parent relationships."""

    return {item.install_id: () for item in installations}
