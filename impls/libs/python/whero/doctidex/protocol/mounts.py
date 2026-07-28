from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ruamel.yaml.comments import CommentedMap

from whero.doctidex.errors import DoctidexError

from .document import DoctidexDocument
from .paths import validate_mount_path


@dataclass(frozen=True, slots=True)
class MountDeclaration:
    type: str
    url: str
    mount_path: str
    raw: CommentedMap


def read_mounts(document: DoctidexDocument) -> list[MountDeclaration]:
    doctidex = document.doctidex
    if not doctidex:
        return []
    raw_mounts = doctidex.get("mounts", [])
    if raw_mounts is None:
        return []
    if not isinstance(raw_mounts, list):
        raise DoctidexError(
            "doctidex.mounts must be a YAML list.",
            operation="validate_mount",
            affected=[str(document.path)],
            actions=["Replace doctidex.mounts with a list of mount mappings."],
            code="mounts_not_list",
        )
    if raw_mounts and not document.is_root:
        raise DoctidexError(
            "doctidex.mounts is only allowed in a root index.md.",
            operation="validate_mount",
            affected=[str(document.path)],
            actions=["Move the mount declarations to the root index.md."],
            code="mounts_on_non_root",
        )

    mounts: list[MountDeclaration] = []
    for position, raw in enumerate(raw_mounts):
        if not isinstance(raw, CommentedMap):
            raise DoctidexError(
                f"Mount declaration {position} must be a YAML mapping.",
                operation="validate_mount",
                affected=[str(document.path)],
                actions=["Replace the declaration with type, url, and mount_path fields."],
                code="mount_not_mapping",
            )
        values: dict[str, Any] = {}
        for key in ("type", "url", "mount_path"):
            value = raw.get(key)
            if not isinstance(value, str) or not value:
                raise DoctidexError(
                    f"Mount declaration {position} has an invalid {key} field.",
                    operation="validate_mount",
                    affected=[str(document.path)],
                    actions=[f"Set {key} to a non-empty string."],
                    code="mount_field_invalid",
                )
            values[key] = value
        mount_path = validate_mount_path(values["mount_path"])
        mounts.append(MountDeclaration(values["type"], values["url"], mount_path, raw))

    paths = sorted(mount.mount_path for mount in mounts)
    for index, path in enumerate(paths):
        for other in paths[index + 1 :]:
            if other == path or other.startswith(path + "/"):
                raise DoctidexError(
                    f"Mount paths overlap: {path} and {other}.",
                    operation="validate_mount",
                    affected=[path, other],
                    actions=["Choose distinct mount paths that are not ancestors of one another."],
                    code="mount_paths_overlap",
                )
    return mounts
