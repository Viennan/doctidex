from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from whero.doctidex.errors import DoctidexError
from whero.doctidex.protocol.document import DoctidexDocument
from whero.doctidex.protocol.root import RootContext, discover_roots, is_within
from whero.doctidex.protocol.validation import TreeObservations, tree_observations, validate_protocol
from whero.doctidex.results import envelope, finding, paginate_lists, query_identity

from .runner import git
from .source import (
    ResolvedSource,
    RevisionSelector,
    add_detached_worktree,
    canonical_source,
    ensure_exact_commit_cache,
    ensure_source_cache,
    make_logically_read_only,
    remove_detached_worktree,
    resolve_source,
    source_relation,
    verify_exact_commit,
)
from .storage import RootStorage, git_file_state, source_mutation


class ExternalService:
    def __init__(self, context: RootContext) -> None:
        self.context = context
        self.root = context.root
        self.storage = RootStorage(self.root)
        self.host_repository = _host_repository(self.root)

    def _link_source_preflight(
        self, source_directory: Path, *, operation: str
    ) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
        source_directory = source_directory.absolute()
        if not source_directory.is_dir() or not os.access(source_directory, os.R_OK):
            raise DoctidexError(
                "The external link source must be an existing readable directory.",
                operation=operation,
                affected=[str(source_directory)],
                actions=["Pass a readable directory inside a managed direct install or link."],
                code="path_not_directory",
                domain="external",
                path=str(source_directory),
            )
        runtime = self.storage.read_runtime()
        mapping = _mapping_for_source(self.root, runtime, source_directory)
        if mapping is None:
            raise DoctidexError(
                "The source directory is not inside a complete managed external install or link.",
                operation=operation,
                affected=[str(source_directory)],
                actions=["Install the source first, then pass a directory inside that managed install."],
                code="source_unmanaged",
                domain="external",
                path=str(source_directory),
            )
        install = runtime["installs"].get(mapping["install_id"])
        if not isinstance(install, dict):
            raise _mapping_error(operation, source_directory)
        if install.get("role") != "direct" or install.get("managed_state") != "complete":
            raise DoctidexError(
                "A dependency-only or incomplete install cannot back a durable external link.",
                operation=operation,
                affected=[install["install_id"]],
                actions=["Run external install with the same source and selector without --dependency-of, then retry."],
                code="dependency_not_recoverable",
                domain="external",
            )
        _assert_manifest_trackable(self.host_repository, self.storage.manifest_path, operation=operation)
        manifest = self.storage.read_manifest(required=True)
        if manifest["installs"].get(install["install_id"]) != _portable_install(install):
            raise _mapping_error(operation, source_directory)
        return source_directory, runtime, mapping, install

    def _presentation_preflight(self, target_value: str, *, operation: str) -> dict[str, Any]:
        target_relative = _validate_target_path(target_value, operation=operation)
        target = self.root.joinpath(*target_relative.parts)
        runtime = self.storage.read_runtime()
        link = runtime["links"].get(target_relative.as_posix())
        if not isinstance(link, dict):
            raise DoctidexError(
                "The target path is not a managed external presentation.",
                operation=operation,
                affected=[str(target)],
                actions=["Pass an existing durable external link target, or create one with external link."],
                code="presentation_not_found",
                domain="external",
                path=str(target),
            )
        manifest = self.storage.read_manifest(required=True)
        portable_link = manifest["links"].get(target_relative.as_posix())
        if portable_link != link:
            raise _mapping_error(operation, target)
        install = runtime["installs"].get(link.get("install_id"))
        if (
            not isinstance(install, dict)
            or install.get("role") != "direct"
            or install.get("managed_state") != "complete"
        ):
            raise _mapping_error(operation, target)
        if manifest["installs"].get(install["install_id"]) != _portable_install(install):
            raise _mapping_error(operation, target)
        install_path = self.root.joinpath(*install["install_path"].lstrip("/").split("/"))
        if not install_path.is_dir() or _worktree_head(install_path) != install["resolved_commit"]:
            raise _mapping_error(operation, target)
        repository_relative = link.get("repository_relative_path")
        if not isinstance(repository_relative, str):
            raise _mapping_error(operation, target)
        source = install_path if repository_relative == "." else install_path.joinpath(*repository_relative.split("/"))
        expected_symlink = os.path.relpath(source, target.parent)
        if not target.is_symlink():
            raise _mapping_error(operation, target)
        try:
            if os.readlink(target) != expected_symlink:
                raise _mapping_error(operation, target)
        except OSError as exc:
            raise _mapping_error(operation, target) from exc
        responsible_value = link.get("responsible_index")
        if not isinstance(responsible_value, str):
            raise _mapping_error(operation, target)
        responsible = self.root.joinpath(*responsible_value.split("/"))
        if responsible != _responsible_index(self.root, target.parent):
            raise _mapping_error(operation, target)
        try:
            relative_to_index = target.relative_to(responsible.parent).as_posix()
            _assert_link_frontmatter(responsible, relative_to_index, str(link.get("safe_state")))
            ownership = _frontmatter_ownership_from_record(link)
        except (DoctidexError, ValueError) as exc:
            if isinstance(exc, DoctidexError):
                raise _mapping_error(operation, target) from exc
            raise _mapping_error(operation, target) from exc
        if _git_ignored(self.host_repository, target, operation=operation):
            raise DoctidexError(
                "The external link target is ignored by the host Git repository.",
                operation=operation,
                affected=[str(target)],
                actions=["Adjust the host ignore rules so the presentation remains trackable, then retry."],
                requires_user="git_tracking",
                code="link_target_ignored",
                domain="external",
                path=str(target),
            )
        return {
            "target_relative": target_relative,
            "target": target,
            "runtime": runtime,
            "manifest": manifest,
            "link": link,
            "install": install,
            "install_path": install_path,
            "responsible": responsible,
            "relative_to_index": relative_to_index,
            "ownership": ownership,
        }

    def install(
        self,
        url: str,
        selector: RevisionSelector | None,
        *,
        dependency_of: str | None,
        apply: bool,
        cwd: Path,
    ) -> dict[str, Any]:
        runtime = self.storage.read_runtime()
        _assert_manifest_trackable(self.host_repository, self.storage.manifest_path)
        canonical = canonical_source(url, cwd=cwd)
        existing_match = None
        if selector is None:
            existing_match = next(
                (
                    item
                    for item in runtime["installs"].values()
                    if item.get("canonical_source") == canonical and item.get("requested_default") is True
                ),
                None,
            )
        else:
            normalized_input = selector.value.lower() if selector.kind == "commit" else selector.value
            existing_match = next(
                (
                    item
                    for item in runtime["installs"].values()
                    if item.get("canonical_source") == canonical
                    and item.get("revision_selector") == {"kind": selector.kind, "value": normalized_input}
                ),
                None,
            )
        if existing_match is not None:
            source = _source_from_record(url, existing_match)
        else:
            source = resolve_source(url, selector, cwd=cwd)
        identifier = _install_id(self.root, source.canonical, source.selector)
        internal_path = f"/.doctidex/git/installs/{identifier}"
        filesystem_path = self.storage.install_directory / identifier

        parent = None
        if dependency_of is not None:
            parent = runtime["installs"].get(dependency_of)
            if not isinstance(parent, dict) or parent.get("managed_state", "complete") != "complete":
                raise DoctidexError(
                    "The dependency parent is not a complete install in the selected root.",
                    operation="external_install",
                    affected=[dependency_of],
                    actions=["Pass an install ID returned for this owner root, or omit --dependency-of."],
                    requires_user="install_parent",
                    code="dependency_parent_invalid",
                    domain="external",
                )

        existing = runtime["installs"].get(identifier)
        previous_role = existing.get("role") if isinstance(existing, dict) else None
        role = "direct" if dependency_of is None or previous_role == "direct" else "dependency"
        parents = sorted(set((existing or {}).get("parents", [])) | ({dependency_of} if dependency_of else set()))
        manifest_included = role == "direct"
        frontmatter = _frontmatter_plan(self.context.index)
        planned = _install_planned_paths(self.root, self.host_repository, filesystem_path, manifest_included)

        if not apply:
            return self._install_result(
                source,
                identifier,
                role,
                parents,
                internal_path,
                filesystem_path,
                manifest_included,
                frontmatter,
                applied=False,
                changed=[],
                planned=planned,
                network=source.network,
            )

        with source_mutation(source.canonical):
            if existing_match is not None:
                cache, cache_network = ensure_exact_commit_cache(source.public_url, source.canonical, source.commit)
            else:
                cache, cache_network = ensure_source_cache(source)
            with self.storage.mutation():
                _assert_payload_untracked(self.host_repository, filesystem_path)
                changed, frontmatter = self.storage.ensure_host_layout()
                if filesystem_path.exists():
                    if _worktree_head(filesystem_path) != source.commit:
                        raise DoctidexError(
                            "The stable install path contains a different or damaged checkout.",
                            operation="external_install",
                            affected=[str(filesystem_path)],
                            actions=["Preserve the path and resolve the conflict before retrying."],
                            requires_user="target_path",
                            code="install_damaged",
                            domain="external",
                            path=str(filesystem_path),
                        )
                else:
                    add_detached_worktree(cache, filesystem_path, source.commit, operation="external_install")
                    make_logically_read_only(filesystem_path)
                    changed.append(filesystem_path)

                record = _install_record(
                    source,
                    identifier,
                    internal_path,
                    role,
                    parents,
                    requested_default=selector is None,
                    relation=source_relation(self.root, source.canonical),
                )
                runtime = self.storage.read_runtime()
                runtime["installs"][identifier] = record
                self.storage.update_runtime(lambda value: value["installs"].__setitem__(identifier, record))
                if manifest_included:
                    manifest = self.storage.read_manifest()
                    manifest["installs"][identifier] = _portable_install(record)
                    self.storage.write_manifest(manifest)
                    changed.append(self.storage.manifest_path)
                changed.append(self.storage.runtime_path)

        return self._install_result(
            source,
            identifier,
            role,
            parents,
            internal_path,
            filesystem_path,
            manifest_included,
            frontmatter,
            applied=True,
            changed=_unique_paths(changed),
            planned=planned,
            network=source.network or cache_network,
        )

    def link(self, source_directory: Path, target_value: str, *, apply: bool) -> dict[str, Any]:
        source_directory = source_directory.absolute()
        if not source_directory.is_dir() or not os.access(source_directory, os.R_OK):
            raise DoctidexError(
                "The external link source must be an existing readable directory.",
                operation="external_link",
                affected=[str(source_directory)],
                actions=["Pass a readable directory inside a managed direct install or link."],
                code="path_not_directory",
                domain="external",
                path=str(source_directory),
            )
        runtime = self.storage.read_runtime()
        mapping = _mapping_for_source(self.root, runtime, source_directory)
        if mapping is None:
            raise DoctidexError(
                "The source directory is not inside a complete managed external install or link.",
                operation="external_link",
                affected=[str(source_directory)],
                actions=["Install the source first, then pass a directory inside that managed install."],
                code="source_unmanaged",
                domain="external",
                path=str(source_directory),
            )
        install = runtime["installs"].get(mapping["install_id"])
        if not isinstance(install, dict):
            raise _mapping_error("external_link", source_directory)
        if install.get("role") != "direct":
            raise DoctidexError(
                "A dependency-only install cannot back a durable external link.",
                operation="external_link",
                affected=[install["install_id"]],
                actions=["Run external install with the same source and selector without --dependency-of, then retry."],
                code="dependency_not_recoverable",
                domain="external",
            )
        _assert_manifest_trackable(self.host_repository, self.storage.manifest_path)
        manifest = self.storage.read_manifest(required=True)
        if not isinstance(manifest["installs"].get(install["install_id"]), dict):
            raise _mapping_error("external_link", source_directory)

        target_relative = _validate_target_path(target_value)
        target = self.root.joinpath(*target_relative.parts)
        repository_relative = _join_repository_path(
            mapping["repository_relative_path"], source_directory, mapping["base"]
        )
        safe_state = _safe_state(source_directory)
        responsible = _responsible_index(self.root, target.parent)
        relative_to_index = target.relative_to(responsible.parent).as_posix()
        frontmatter = _link_frontmatter_plan(responsible, relative_to_index, safe_state)
        frontmatter_ownership = _link_frontmatter_ownership(responsible, relative_to_index, safe_state)
        planned = [responsible, target, self.storage.manifest_path, self.storage.runtime_path]
        existing_link = runtime["links"].get(target_relative.as_posix())
        if existing_link is not None and manifest["links"].get(target_relative.as_posix()) != existing_link:
            raise _mapping_error("external_link", target)
        expected_mapping = {
            "target_path": target_relative.as_posix(),
            "install_id": install["install_id"],
            "repository_relative_path": repository_relative,
            "safe_state": safe_state,
            "responsible_index": str(responsible.relative_to(self.root).as_posix()),
            "frontmatter_ownership": frontmatter_ownership,
        }
        relative_source = os.path.relpath(source_directory, target.parent)
        if existing_link is not None and not _same_link_mapping(existing_link, expected_mapping):
            raise DoctidexError(
                "The target path already belongs to a different external mapping.",
                operation="external_link",
                affected=[str(target)],
                actions=["Choose a new target path; this command does not replace mappings."],
                requires_user="target_path",
                code="target_occupied",
                domain="external",
                path=str(target),
            )
        if isinstance(existing_link, dict):
            # A legacy record without ownership remains valid and is never silently claimed.
            expected_mapping = existing_link
        overlaps = [
            existing_target
            for existing_target in runtime["links"]
            if existing_target != target_relative.as_posix()
            and _paths_overlap(PurePosixPath(existing_target), target_relative)
        ]
        if overlaps:
            raise DoctidexError(
                "The external link target overlaps another managed presentation.",
                operation="external_link",
                affected=[str(target), *overlaps],
                actions=["Choose a target outside every existing managed presentation."],
                requires_user="target_path",
                code="presentation_overlap",
                domain="external",
                path=str(target),
            )
        if (target.exists() or target.is_symlink()) and existing_link is None:
            raise DoctidexError(
                "The external link target path is occupied.",
                operation="external_link",
                affected=[str(target)],
                actions=["Choose an unoccupied root-relative target path."],
                requires_user="target_path",
                code="target_occupied",
                domain="external",
                path=str(target),
            )
        if target.is_symlink() and existing_link is not None:
            try:
                actual_target = os.readlink(target)
            except OSError as exc:
                raise _mapping_error("external_link", target) from exc
            if actual_target != relative_source:
                raise _mapping_error("external_link", target)
        if _git_ignored(self.host_repository, target):
            raise DoctidexError(
                "The external link target is ignored by the host Git repository.",
                operation="external_link",
                affected=[str(target)],
                actions=["Choose a trackable target or adjust the host ignore rules."],
                requires_user="git_tracking",
                code="link_target_ignored",
                domain="external",
                path=str(target),
            )

        if not apply:
            changed: list[Path] = []
        else:
            with self.storage.mutation():
                changed = []
                _probe_symlink(target)
                if _apply_link_frontmatter(responsible, relative_to_index, safe_state):
                    changed.append(responsible)
                if not target.is_symlink():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        target.symlink_to(relative_source, target_is_directory=True)
                    except OSError as exc:
                        raise DoctidexError(
                            "The platform or filesystem could not create the required relative symlink.",
                            operation="external_link",
                            affected=[str(target)],
                            actions=["Run on a filesystem and account that permit symbolic links."],
                            code="symlink_unsupported",
                            domain="external",
                            path=str(target),
                        ) from exc
                    changed.append(target)
                self.storage.update_runtime(
                    lambda value: value["links"].__setitem__(target_relative.as_posix(), expected_mapping)
                )
                manifest = self.storage.read_manifest(required=True)
                manifest["links"][target_relative.as_posix()] = expected_mapping
                self.storage.write_manifest(manifest)
                changed.extend([self.storage.runtime_path, self.storage.manifest_path])

        return envelope(
            "external_link",
            result="External link applied." if apply else "External link plan is ready.",
            root=str(self.root),
            changed=[str(path) for path in _unique_paths(changed)],
            source_path=str(source_directory),
            applied=apply,
            install_id=install["install_id"],
            install_path=install["install_path"],
            target_path=target_relative.as_posix(),
            presentation_path=str(target),
            working_path=str(source_directory),
            repository_relative_path=repository_relative,
            source_url=install["source_url"],
            source_relation=install["source_relation"],
            revision_selector=install["revision_selector"],
            default_branch=install.get("default_branch"),
            resolved_commit=install["resolved_commit"],
            safe_state=safe_state,
            symlink_tracking="trackable",
            responsible_index=str(responsible),
            frontmatter_changes=frontmatter,
            recovery_manifest=str(self.storage.manifest_path),
            recovery_manifest_state=git_file_state(self.host_repository, self.storage.manifest_path)
            if apply
            else _file_state_or_planned(self.host_repository, self.storage.manifest_path),
            planned_changes=[str(path) for path in planned],
        )

    def rebind(self, source_directory: Path, target_value: str, *, apply: bool) -> dict[str, Any]:
        previous = self._presentation_preflight(target_value, operation="external_rebind")
        source_directory, _runtime, mapping, install = self._link_source_preflight(
            source_directory, operation="external_rebind"
        )
        target_relative = previous["target_relative"]
        target = previous["target"]
        repository_relative = _join_repository_path(
            mapping["repository_relative_path"], source_directory, mapping["base"]
        )
        safe_state = _safe_state(source_directory)
        relative_source = os.path.relpath(source_directory, target.parent)
        frontmatter, ownership = _rebind_frontmatter_plan(
            previous["responsible"],
            previous["relative_to_index"],
            previous_safe_state=previous["link"]["safe_state"],
            safe_state=safe_state,
            ownership=previous["ownership"],
        )
        expected_mapping = {
            "target_path": target_relative.as_posix(),
            "install_id": install["install_id"],
            "repository_relative_path": repository_relative,
            "safe_state": safe_state,
            "responsible_index": str(previous["responsible"].relative_to(self.root).as_posix()),
            "frontmatter_ownership": ownership,
        }
        unchanged = _same_link_mapping(previous["link"], expected_mapping)
        planned = [previous["responsible"], target, self.storage.manifest_path, self.storage.runtime_path]

        if unchanged or not apply:
            return self._rebind_result(
                previous,
                source_directory=source_directory,
                install=install,
                repository_relative=repository_relative,
                safe_state=safe_state,
                frontmatter=frontmatter,
                state="unchanged" if unchanged else "planned",
                applied=apply,
                changed=[],
                planned=planned,
            )

        temporary: Path | None = None
        with self.storage.mutation():
            current = self._presentation_preflight(target_value, operation="external_rebind")
            source_directory, _runtime, mapping, install = self._link_source_preflight(
                source_directory, operation="external_rebind"
            )
            repository_relative = _join_repository_path(
                mapping["repository_relative_path"], source_directory, mapping["base"]
            )
            safe_state = _safe_state(source_directory)
            if current["link"] != previous["link"]:
                raise _mapping_error("external_rebind", target)
            frontmatter, ownership = _rebind_frontmatter_plan(
                current["responsible"],
                current["relative_to_index"],
                previous_safe_state=current["link"]["safe_state"],
                safe_state=safe_state,
                ownership=current["ownership"],
            )
            expected_mapping = {
                "target_path": target_relative.as_posix(),
                "install_id": install["install_id"],
                "repository_relative_path": repository_relative,
                "safe_state": safe_state,
                "responsible_index": str(current["responsible"].relative_to(self.root).as_posix()),
                "frontmatter_ownership": ownership,
            }
            if _same_link_mapping(current["link"], expected_mapping):
                return self._rebind_result(
                    current,
                    source_directory=source_directory,
                    install=install,
                    repository_relative=repository_relative,
                    safe_state=safe_state,
                    frontmatter=frontmatter,
                    state="unchanged",
                    applied=True,
                    changed=[],
                    planned=planned,
                )
            relative_source = os.path.relpath(source_directory, target.parent)
            temporary = _prepare_replacement_symlink(target, relative_source, operation="external_rebind")
            changed: list[Path] = []
            try:
                if _apply_link_frontmatter(current["responsible"], current["relative_to_index"], safe_state):
                    changed.append(current["responsible"])
                manifest = self.storage.read_manifest(required=True)
                if manifest["links"].get(target_relative.as_posix()) != current["link"]:
                    raise _mapping_error("external_rebind", target)
                manifest["links"][target_relative.as_posix()] = expected_mapping
                self.storage.write_manifest(manifest)
                changed.append(self.storage.manifest_path)

                def replace_runtime(value: dict[str, Any]) -> None:
                    if value["links"].get(target_relative.as_posix()) != current["link"]:
                        raise _mapping_error("external_rebind", target)
                    value["links"][target_relative.as_posix()] = expected_mapping

                self.storage.update_runtime(replace_runtime)
                changed.append(self.storage.runtime_path)
                os.replace(temporary, target)
                temporary = None
                changed.append(target)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)

        return self._rebind_result(
            previous,
            source_directory=source_directory,
            install=install,
            repository_relative=repository_relative,
            safe_state=safe_state,
            frontmatter=frontmatter,
            state="rebound",
            applied=True,
            changed=changed,
            planned=planned,
        )

    def _rebind_result(
        self,
        previous: dict[str, Any],
        *,
        source_directory: Path,
        install: dict[str, Any],
        repository_relative: str,
        safe_state: str,
        frontmatter: dict[str, str],
        state: str,
        applied: bool,
        changed: list[Path],
        planned: list[Path],
    ) -> dict[str, Any]:
        link = previous["link"]
        return envelope(
            "external_rebind",
            result=(
                "The external presentation mapping was replaced."
                if state == "rebound"
                else (
                    "The external presentation already has this mapping."
                    if state == "unchanged"
                    else "External presentation rebinding plan is ready."
                )
            ),
            root=str(self.root),
            changed=[str(path) for path in _unique_paths(changed)],
            applied=applied,
            state=state,
            target_path=previous["target_relative"].as_posix(),
            presentation_path=str(previous["target"]),
            previous_install_id=link["install_id"],
            previous_install_path=previous["install"]["install_path"],
            previous_repository_relative_path=link["repository_relative_path"],
            install_id=install["install_id"],
            install_path=install["install_path"],
            source_path=str(source_directory),
            working_path=str(source_directory),
            repository_relative_path=repository_relative,
            source_url=install["source_url"],
            source_relation=install["source_relation"],
            revision_selector=install["revision_selector"],
            default_branch=install.get("default_branch"),
            resolved_commit=install["resolved_commit"],
            safe_state=safe_state,
            symlink_tracking="trackable",
            responsible_index=str(previous["responsible"]),
            frontmatter_changes=frontmatter,
            recovery_manifest=str(self.storage.manifest_path),
            recovery_manifest_state=(
                git_file_state(self.host_repository, self.storage.manifest_path)
                if applied
                else _file_state_or_planned(self.host_repository, self.storage.manifest_path)
            ),
            planned_changes=[str(path) for path in _unique_paths(planned)],
        )

    def unlink(self, target_value: str, *, apply: bool) -> dict[str, Any]:
        preflight = self._presentation_preflight(target_value, operation="external_unlink")
        references = self._unlink_references(preflight)
        if references:
            return self._unlink_result(preflight, references=references, apply=apply, state="blocked", changed=[])
        if not apply:
            return self._unlink_result(preflight, references=[], apply=False, state="planned", changed=[])

        with self.storage.mutation():
            preflight = self._presentation_preflight(target_value, operation="external_unlink")
            references = self._unlink_references(preflight)
            if references:
                return self._unlink_result(preflight, references=references, apply=True, state="blocked", changed=[])
            changed: list[Path] = []
            if _apply_unlink_frontmatter(
                preflight["responsible"], preflight["relative_to_index"], preflight["ownership"]
            ):
                changed.append(preflight["responsible"])
            manifest = self.storage.read_manifest(required=True)
            target = preflight["target_relative"].as_posix()
            if manifest["links"].get(target) != preflight["link"]:
                raise _mapping_error("external_unlink", preflight["target"])
            del manifest["links"][target]
            self.storage.write_manifest(manifest)
            changed.append(self.storage.manifest_path)

            def remove_runtime(value: dict[str, Any]) -> None:
                if value["links"].get(target) != preflight["link"]:
                    raise _mapping_error("external_unlink", preflight["target"])
                del value["links"][target]

            self.storage.update_runtime(remove_runtime)
            changed.append(self.storage.runtime_path)
            preflight["target"].unlink()
            changed.append(preflight["target"])

        return self._unlink_result(preflight, references=[], apply=True, state="unlinked", changed=changed)

    def _unlink_references(self, preflight: dict[str, Any]) -> list[tuple[str, str]]:
        observations = tree_observations(
            self.context,
            excluded_roots=[self.storage.install_directory],
            excluded_configuration_fields=("boundary-set", "unsafe"),
        )
        target = preflight["target"]
        references: list[tuple[str, str]] = []
        for link in observations.links:
            if (
                link.is_file_link
                and link.target is not None
                and not observations.is_unsafe(link.document)
                and not observations.is_within_boundary(link.document)
                and is_within(link.target, target)
            ):
                references.append(("Markdown navigation link", str(link.document)))
        for path in observations.paths:
            if (
                path == target
                or not path.is_symlink()
                or observations.is_unsafe(path)
                or observations.is_within_boundary(path)
            ):
                continue
            try:
                raw_target = os.readlink(path)
            except OSError:
                continue
            lexical_target = Path(raw_target) if os.path.isabs(raw_target) else path.parent / raw_target
            if is_within(lexical_target, target):
                references.append(("filesystem symlink", str(path)))
        target_key = preflight["target_relative"].as_posix()
        for mapping_target in preflight["runtime"]["links"]:
            if mapping_target == target_key:
                continue
            candidate = self.root.joinpath(*mapping_target.split("/"))
            if is_within(candidate, target):
                references.append(("runtime durable mapping", f"{self.storage.runtime_path}#links/{mapping_target}"))
        for mapping_target in preflight["manifest"]["links"]:
            if mapping_target == target_key:
                continue
            candidate = self.root.joinpath(*mapping_target.split("/"))
            if is_within(candidate, target):
                references.append(("portable durable mapping", f"{self.storage.manifest_path}#links/{mapping_target}"))
        return list(dict.fromkeys(references))

    def _unlink_result(
        self,
        preflight: dict[str, Any],
        *,
        references: list[tuple[str, str]],
        apply: bool,
        state: str,
        changed: list[Path],
    ) -> dict[str, Any]:
        link = preflight["link"]
        frontmatter = _unlink_frontmatter_plan(preflight["ownership"])
        planned = [preflight["target"], self.storage.runtime_path, self.storage.manifest_path]
        if "remove" in frontmatter.values() or "restore" in frontmatter.values():
            planned.append(preflight["responsible"])
        blocked = state == "blocked"
        return envelope(
            "external_unlink",
            status="blocked" if blocked else "ok",
            result=(
                "The external presentation is still referenced."
                if blocked
                else (
                    "External presentation removed."
                    if state == "unlinked"
                    else "External presentation removal plan is ready."
                )
            ),
            root=str(self.root),
            changed=[str(path) for path in _unique_paths(changed)],
            findings=[
                finding(
                    "external",
                    "error",
                    "presentation_referenced",
                    f"The presentation is still referenced by {kind}.",
                    path=evidence,
                    actions=["Remove or redirect this reference with explicit authority, then retry unlink."],
                )
                for kind, evidence in references
            ],
            affected=[evidence for _, evidence in references],
            applied=apply,
            state=state,
            target_path=preflight["target_relative"].as_posix(),
            presentation_path=str(preflight["target"]),
            install_id=link["install_id"],
            install_path=preflight["install"]["install_path"],
            repository_relative_path=link["repository_relative_path"],
            safe_state=link["safe_state"],
            responsible_index=str(preflight["responsible"]),
            frontmatter_changes=frontmatter,
            recovery_manifest=str(self.storage.manifest_path),
            recovery_manifest_state=(
                git_file_state(self.host_repository, self.storage.manifest_path)
                if apply and not blocked
                else _file_state_or_planned(self.host_repository, self.storage.manifest_path)
            ),
            planned_changes=[str(path) for path in _unique_paths(planned)],
        )

    def restore(
        self,
        filters: list[str],
        *,
        apply: bool,
        limit: int,
        cursor: str | None,
    ) -> dict[str, Any]:
        manifest = self.storage.read_manifest(required=True)
        identity_value = self.storage.manifest_identity(manifest)
        normalized_filter = sorted(set(filters))
        identifiers = normalized_filter or sorted(manifest["installs"])
        records: list[dict[str, Any]] = []
        for identifier in identifiers:
            record = manifest["installs"].get(identifier)
            if not isinstance(record, dict):
                records.append({"install_id": identifier, "missing": True})
            else:
                records.append(record)
        query = query_identity(
            "external_restore",
            root=str(self.root),
            manifest=identity_value,
            filters=normalized_filter,
            limit=limit,
            apply=apply,
        )
        try:
            pages, collection = paginate_lists(
                {"items": records}, limit=limit, identity=query, state=identity_value, cursor=cursor
            )
        except ValueError as exc:
            raise DoctidexError(
                "The restore cursor no longer matches the recovery manifest.",
                operation="external_restore",
                affected=[str(self.storage.manifest_path)],
                actions=["Restart restore from the first page."],
                code="cursor_invalid",
                domain="external",
            ) from exc

        items: list[dict[str, Any]] = []
        changed: list[Path] = []
        network = False
        for record in pages["items"]:
            item, item_changed, item_network = self._restore_item(record, apply=apply)
            items.append(item)
            changed.extend(item_changed)
            network = network or item_network
        blocked = any(item["state"] == "blocked" for item in items)
        return envelope(
            "external_restore",
            status="warning" if blocked else "ok",
            result="Restore completed with preserved blocked items." if blocked else "Restore page completed.",
            root=str(self.root),
            changed=[str(path) for path in _unique_paths(changed)],
            network=network,
            collection=collection,
            applied=apply,
            recovery_manifest=str(self.storage.manifest_path),
            recovery_manifest_identity=identity_value,
            install_filter=normalized_filter,
            items=items,
        )

    def _restore_item(self, record: dict[str, Any], *, apply: bool) -> tuple[dict[str, Any], list[Path], bool]:
        identifier = record.get("install_id")
        if record.get("missing") or not isinstance(identifier, str):
            return (
                _restore_blocked(
                    str(identifier), "install_not_found", "The requested install ID is not in the manifest."
                ),
                [],
                False,
            )
        path = self.root.joinpath(*str(record["install_path"]).lstrip("/").split("/"))
        if path.exists():
            if _worktree_head(path) == record["resolved_commit"]:
                return _restore_item_payload(record, "unchanged", []), [], False
            return (
                _restore_blocked(
                    identifier, "install_path_conflict", "The stable install path is occupied by different content."
                ),
                [],
                False,
            )
        if not apply:
            network = verify_exact_commit(
                record["source_url"],
                canonical_source(record["source_url"], cwd=self.root),
                record["resolved_commit"],
                operation="external_restore",
            )
            return _restore_item_payload(record, "planned", []), [], network

        canonical = canonical_source(record["source_url"], cwd=self.root)
        with source_mutation(canonical):
            cache, network = ensure_exact_commit_cache(record["source_url"], canonical, record["resolved_commit"])
            with self.storage.mutation():
                changed, _ = self.storage.ensure_host_layout()
                add_detached_worktree(cache, path, record["resolved_commit"], operation="external_restore")
                make_logically_read_only(path)
                runtime_record = {
                    **record,
                    "canonical_source": canonical,
                    "requested_default": record.get("default_branch") is not None,
                    "role": "direct",
                    "parents": [],
                    "managed_state": "complete",
                }
                manifest = self.storage.read_manifest(required=True)
                self.storage.update_runtime(
                    lambda value: _restore_runtime_mapping(value, identifier, runtime_record, manifest)
                )
                changed.extend([path, self.storage.runtime_path])
        return _restore_item_payload(record, "restored", []), changed, network

    def remove(self, identifier: str, *, apply: bool) -> dict[str, Any]:
        runtime = self.storage.read_runtime()
        record = runtime["installs"].get(identifier)
        if not isinstance(record, dict):
            raise DoctidexError(
                "The install ID is not managed by the selected owner root.",
                operation="external_remove",
                affected=[identifier],
                actions=[
                    "Run external link-parse on a managed path when the install ID is unknown.",
                    "Pass the returned install_id for the selected owner root.",
                ],
                code="install_not_found",
                domain="external",
            )
        if record["role"] == "dependency" and record["managed_state"] == "hidden":
            return envelope(
                "external_remove",
                result="The hidden dependency install was preserved without deletion.",
                root=str(self.root),
                findings=[
                    finding(
                        "external",
                        "info",
                        "hidden_install_preserved",
                        "A hidden dependency is retained until checkout reconciliation can determine it again.",
                        path=str(self.root.joinpath(*record["install_path"].lstrip("/").split("/"))),
                    )
                ],
                applied=False,
                install_id=record["install_id"],
                install_role=record["role"],
                install_path=record["install_path"],
                manifest_included=False,
                state="preserved_hidden",
                planned_changes=[],
            )
        preflight = self._remove_preflight(identifier)
        if preflight["references"]:
            return self._remove_result(preflight, apply=apply, state="blocked", changed=[])
        if not apply:
            return self._remove_result(preflight, apply=False, state="planned", changed=[])

        with source_mutation(preflight["record"]["canonical_source"]):
            with self.storage.mutation():
                preflight = self._remove_preflight(identifier)
                if preflight["references"]:
                    return self._remove_result(preflight, apply=True, state="blocked", changed=[])

                changed: list[Path] = []
                path = preflight["path"]
                if path.exists():
                    remove_detached_worktree(path, operation="external_remove")
                    changed.append(path)

                if preflight["manifest_included"] and identifier in preflight["manifest"]["installs"]:
                    manifest = preflight["manifest"]
                    del manifest["installs"][identifier]
                    self.storage.write_manifest(manifest)
                    changed.append(self.storage.manifest_path)

                self.storage.update_runtime(lambda value: value["installs"].pop(identifier, None))
                changed.append(self.storage.runtime_path)

        return self._remove_result(preflight, apply=True, state="removed", changed=changed)

    def _remove_preflight(self, identifier: str) -> dict[str, Any]:
        try:
            runtime = self.storage.read_runtime()
        except DoctidexError as exc:
            raise _remove_damaged(
                identifier, self.storage.runtime_path, "The managed runtime records are invalid."
            ) from exc
        record = runtime["installs"].get(identifier)
        if not isinstance(record, dict):
            raise DoctidexError(
                "The install ID is not managed by the selected owner root.",
                operation="external_remove",
                affected=[identifier],
                actions=[
                    "Run external link-parse on a managed path when the install ID is unknown.",
                    "Pass the returned install_id for the selected owner root.",
                ],
                code="install_not_found",
                domain="external",
            )

        path = self.root.joinpath(*record["install_path"].lstrip("/").split("/"))
        payload_present = path.exists()
        if payload_present and (_worktree_head(path) != record["resolved_commit"]):
            raise _remove_damaged(identifier, path, "The managed install payload does not match its runtime record.")

        try:
            manifest = self.storage.read_manifest()
        except DoctidexError as exc:
            raise _remove_damaged(
                identifier, self.storage.manifest_path, "The managed external manifest is invalid."
            ) from exc
        manifest_included = record["role"] == "direct"
        manifest_record = manifest["installs"].get(identifier)
        if manifest_included:
            expected = _portable_install(record)
            # A missing portable record is recoverable only after payload deletion was interrupted.
            if manifest_record != expected and (payload_present or manifest_record is not None):
                raise _remove_damaged(
                    identifier, self.storage.manifest_path, "The direct install manifest is inconsistent."
                )
        elif manifest_record is not None:
            raise _remove_damaged(identifier, self.storage.manifest_path, "A dependency install has portable metadata.")

        observations = tree_observations(
            self.context,
            excluded_roots=[self.storage.install_directory],
            excluded_configuration_fields=("boundary-set", "unsafe"),
        )
        references = self._remove_references(identifier, path, runtime, manifest, observations)
        return {
            "record": record,
            "path": path,
            "manifest": manifest,
            "manifest_included": manifest_included,
            "references": references,
        }

    def _remove_references(
        self,
        identifier: str,
        install_path: Path,
        runtime: dict[str, Any],
        manifest: dict[str, Any],
        observations: TreeObservations,
    ) -> list[tuple[str, str]]:
        references: list[tuple[str, str]] = []
        presentations = [
            self.root.joinpath(*target.split("/"))
            for target, link in runtime["links"].items()
            if link.get("install_id") == identifier
        ]
        targets = [install_path, *presentations]

        for link in observations.links:
            if (
                not link.is_file_link
                or link.target is None
                or observations.is_unsafe(link.document)
                or observations.is_within_boundary(link.document)
            ):
                continue
            if any(is_within(link.target, target) for target in targets):
                references.append(("Markdown navigation link", str(link.document)))

        for path in observations.paths:
            if (
                not path.is_symlink()
                or observations.is_unsafe(path)
                or observations.is_within_boundary(path)
            ):
                continue
            try:
                resolved = path.resolve(strict=False)
            except (OSError, RuntimeError):
                continue
            if is_within(resolved, install_path):
                references.append(("filesystem symlink", str(path)))

        for target, link in runtime["links"].items():
            if link.get("install_id") == identifier:
                references.append(("runtime durable mapping", f"{self.storage.runtime_path}#links/{target}"))
        for target, link in manifest["links"].items():
            if link.get("install_id") == identifier:
                references.append(("portable durable mapping", f"{self.storage.manifest_path}#links/{target}"))
        for parent_id, record in runtime["installs"].items():
            if parent_id != identifier and identifier in record.get("parents", []):
                evidence = f"{self.storage.runtime_path}#installs/{parent_id}/parents"
                references.append(("dependency parent edge", evidence))
        return list(dict.fromkeys(references))

    def _remove_result(
        self,
        preflight: dict[str, Any],
        *,
        apply: bool,
        state: str,
        changed: list[Path],
    ) -> dict[str, Any]:
        record = preflight["record"]
        references: list[tuple[str, str]] = preflight["references"]
        planned = [preflight["path"]]
        if preflight["manifest_included"]:
            planned.append(self.storage.manifest_path)
        planned.append(self.storage.runtime_path)
        blocked = state == "blocked"
        return envelope(
            "external_remove",
            status="blocked" if blocked else "ok",
            result=(
                "The managed install is still referenced."
                if blocked
                else ("External install removed." if state == "removed" else "External install removal plan is ready.")
            ),
            root=str(self.root),
            changed=[str(path) for path in _unique_paths(changed)],
            findings=[
                finding(
                    "external",
                    "error",
                    "install_referenced",
                    f"The install is still referenced by {kind}.",
                    path=evidence,
                    actions=["Remove or redirect this reference with explicit authority, then retry remove."],
                )
                for kind, evidence in references
            ],
            affected=[evidence for _, evidence in references],
            applied=apply,
            install_id=record["install_id"],
            install_role=record["role"],
            install_path=record["install_path"],
            manifest_included=preflight["manifest_included"],
            state=state,
            planned_changes=[str(path) for path in _unique_paths(planned)],
        )

    def link_parse(self, path: Path) -> dict[str, Any]:
        path = path.absolute()
        runtime = self.storage.read_runtime()
        mapping = _mapping_for_input(self.root, runtime, path)
        content_roots = discover_roots(path)
        content_root = content_roots[0].root if content_roots else None
        if mapping is not None and mapping["created_by"] == "link":
            return self._current_mapping_result(path, content_root, runtime, mapping)
        portable = _portable_mapping(self.root, runtime, path, content_root)
        if portable is not None:
            return self._portable_mapping_result(path, content_root, runtime, portable)
        if mapping is not None:
            return self._current_mapping_result(path, content_root, runtime, mapping)
        return envelope(
            "external_link_parse",
            result="The path has no managed external mapping in the selected owner root.",
            root=str(self.root),
            managed=False,
            mapping_origin=None,
            created_by=None,
            content_root=str(content_root) if content_root else None,
            input_path=str(path),
            input_kind="symlink" if path.is_symlink() else "directory",
            presentation_path=None,
            install_id=None,
            install_path=None,
            install_role=None,
            dependency_of=_dependency_summary([]),
            dependency_parent_install_id=None,
            target_state="not_applicable",
            source_url=None,
            source_relation=None,
            revision_selector=None,
            default_branch=None,
            resolved_commit=None,
            repository_relative_path=None,
            working_path=None,
            safe_state=None,
            responsible_index=None,
        )

    def _current_mapping_result(
        self,
        path: Path,
        content_root: Path | None,
        runtime: dict[str, Any],
        mapping: dict[str, Any],
    ) -> dict[str, Any]:
        install = runtime["installs"].get(mapping["install_id"])
        if not isinstance(install, dict):
            raise _mapping_error("external_link_parse", path)
        install_fs = self.root.joinpath(*install["install_path"].lstrip("/").split("/"))
        repository_relative = mapping["repository_relative_path"]
        working = install_fs.joinpath(*repository_relative.split("/")) if repository_relative != "." else install_fs
        available = install_fs.is_dir() and working.exists()
        target_state = "available" if available else "owner_install_missing"
        status = "ok" if available else "warning"
        item_findings = (
            []
            if available
            else [
                finding(
                    "external",
                    "warning",
                    "owner_install_missing",
                    "The durable link target install is missing.",
                    path=str(path),
                    actions=["Run external restore for the returned install ID."],
                )
            ]
        )
        return envelope(
            "external_link_parse",
            status=status,
            result="Managed external mapping resolved."
            if available
            else "The managed mapping is preserved but its install is missing.",
            root=str(self.root),
            findings=item_findings,
            managed=True,
            mapping_origin="owner_root",
            created_by=mapping["created_by"],
            content_root=str(content_root) if content_root else str(self.root),
            input_path=str(path),
            input_kind="symlink" if path.is_symlink() else "directory",
            presentation_path=str(mapping["presentation_path"]),
            install_id=install["install_id"],
            install_path=install["install_path"],
            install_role=install["role"],
            dependency_of=_dependency_summary(install.get("parents", [])),
            dependency_parent_install_id=None,
            target_state=target_state,
            source_url=install["source_url"],
            source_relation=install["source_relation"],
            revision_selector=install["revision_selector"],
            default_branch=install.get("default_branch"),
            resolved_commit=install["resolved_commit"],
            repository_relative_path=repository_relative,
            working_path=str(working) if available else None,
            safe_state=mapping.get("safe_state", "unsafe"),
            responsible_index=mapping.get("responsible_index"),
        )

    def _portable_mapping_result(
        self,
        path: Path,
        content_root: Path | None,
        runtime: dict[str, Any],
        portable: dict[str, Any],
    ) -> dict[str, Any]:
        source = portable["source"]
        parent_id = portable["parent_id"]
        match = next(
            (
                item
                for item in runtime["installs"].values()
                if parent_id in item.get("parents", [])
                and item.get("canonical_source") == canonical_source(source["source_url"], cwd=self.root)
                and item.get("resolved_commit") == source["resolved_commit"]
            ),
            None,
        )
        repository_relative = portable["repository_relative_path"]
        if match:
            install_fs = self.root.joinpath(*match["install_path"].lstrip("/").split("/"))
            working = install_fs if repository_relative == "." else install_fs.joinpath(*repository_relative.split("/"))
            state = "available" if working.exists() else "unavailable"
        else:
            working = None
            state = "dependency_not_installed"
        damaged = state == "unavailable"
        return envelope(
            "external_link_parse",
            status="warning" if damaged else "ok",
            result="Portable external mapping resolved."
            if not damaged
            else "The matching dependency install is unavailable.",
            root=str(self.root),
            findings=[
                finding(
                    "external",
                    "warning",
                    "mapping_damaged",
                    "The matching dependency install cannot provide the mapped path.",
                    path=str(path),
                    actions=["Inspect the dependency install and mapping before retrying."],
                )
            ]
            if damaged
            else [],
            managed=True,
            mapping_origin="installed_repository",
            created_by="link",
            content_root=str(content_root) if content_root else None,
            input_path=str(path),
            input_kind="symlink" if path.is_symlink() else "directory",
            presentation_path=str(path),
            install_id=match.get("install_id") if match else None,
            install_path=match.get("install_path") if match else None,
            install_role=match.get("role") if match else None,
            dependency_of=_dependency_summary(match.get("parents", [])) if match else _dependency_summary([]),
            dependency_parent_install_id=parent_id,
            target_state=state,
            source_url=source["source_url"],
            source_relation=source.get("source_relation", "unknown"),
            revision_selector=source["revision_selector"],
            default_branch=source.get("default_branch"),
            resolved_commit=source["resolved_commit"],
            repository_relative_path=repository_relative,
            working_path=str(working) if working and state == "available" else None,
            safe_state=portable["link"].get("safe_state", "unsafe"),
            responsible_index=str(content_root / portable["link"]["responsible_index"]) if content_root else None,
        )

    def _install_result(
        self,
        source: ResolvedSource,
        identifier: str,
        role: str,
        parents: list[str],
        internal_path: str,
        filesystem_path: Path,
        manifest_included: bool,
        frontmatter: dict[str, str],
        *,
        applied: bool,
        changed: list[Path],
        planned: list[Path],
        network: bool,
    ) -> dict[str, Any]:
        return envelope(
            "external_install",
            result="External install applied." if applied else "External install plan is ready.",
            root=str(self.root),
            changed=[str(path) for path in changed],
            network=network,
            applied=applied,
            install_id=identifier,
            install_role=role,
            dependency_of=_dependency_summary(parents),
            manifest_included=manifest_included,
            install_path=internal_path,
            working_path=str(filesystem_path),
            source_url=source.public_url,
            source_relation=source_relation(self.root, source.canonical),
            revision_selector=source.selector.as_dict(),
            default_branch=source.default_branch,
            resolved_commit=source.commit,
            host_repository=str(self.host_repository),
            payload_tracking="ignored_untracked",
            git_exclusion_file=str(self.host_repository / ".gitignore"),
            git_exclusion_state=git_file_state(self.host_repository, self.host_repository / ".gitignore")
            if applied
            else _file_state_or_planned(self.host_repository, self.host_repository / ".gitignore"),
            recovery_manifest=str(self.storage.manifest_path),
            recovery_manifest_state=git_file_state(self.host_repository, self.storage.manifest_path)
            if applied
            else _file_state_or_planned(self.host_repository, self.storage.manifest_path),
            responsible_index=str(self.context.index.path),
            frontmatter_changes=frontmatter,
            planned_changes=[str(path) for path in planned],
        )


def _source_from_record(input_url: str, record: dict[str, Any]) -> ResolvedSource:
    selector = RevisionSelector(record["revision_selector"]["kind"], record["revision_selector"]["value"])
    return ResolvedSource(
        input_url,
        record["source_url"],
        record["canonical_source"],
        selector,
        record.get("default_branch"),
        record["resolved_commit"],
        False,
    )


def _install_id(root: Path, canonical: str, selector: RevisionSelector) -> str:
    value = f"{root.absolute()}\0{canonical}\0{selector.kind}\0{selector.value}"
    return "i-" + hashlib.sha256(value.encode()).hexdigest()[:20]


def _install_record(
    source: ResolvedSource,
    identifier: str,
    internal_path: str,
    role: str,
    parents: list[str],
    *,
    requested_default: bool,
    relation: str,
) -> dict[str, Any]:
    return {
        "install_id": identifier,
        "install_path": internal_path,
        "source_url": source.public_url,
        "canonical_source": source.canonical,
        "source_relation": relation,
        "revision_selector": source.selector.as_dict(),
        "default_branch": source.default_branch,
        "resolved_commit": source.commit,
        "requested_default": requested_default,
        "role": role,
        "parents": parents,
        "managed_state": "complete",
    }


def _portable_install(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in (
            "install_id",
            "install_path",
            "source_url",
            "source_relation",
            "revision_selector",
            "default_branch",
            "resolved_commit",
        )
    }


def _dependency_summary(parents: list[str]) -> dict[str, Any]:
    ordered = sorted(set(parents))
    return {
        "total": len(ordered),
        "returned": min(len(ordered), 100),
        "truncated": len(ordered) > 100,
        "items": ordered[:100],
    }


def _host_repository(root: Path) -> Path:
    result = git(["-C", str(root), "rev-parse", "--show-toplevel"], operation="host_git", check=False)
    if result.returncode != 0:
        raise DoctidexError(
            "The selected root is not inside a Git working tree.",
            operation="external",
            affected=[str(root)],
            actions=["Select a doctidex root in a Git working tree."],
            code="host_git_not_found",
            domain="external",
        )
    return Path(result.stdout.strip()).absolute()


def _assert_payload_untracked(repository: Path, path: Path) -> None:
    relative = os.path.relpath(path, repository)
    result = git(["-C", str(repository), "ls-files", "--", relative], operation="external_install", check=False)
    if result.stdout.strip():
        raise DoctidexError(
            "The managed payload path already contains tracked Git entries.",
            operation="external_install",
            affected=[str(path)],
            actions=["Use native Git to resolve tracked payload entries, then rerun the dry-run."],
            requires_user="git_tracking",
            code="install_payload_tracked",
            domain="external",
            path=str(path),
        )


def _install_planned_paths(root: Path, host: Path, filesystem_path: Path, manifest: bool) -> list[Path]:
    values = [root / "index.md", host / ".gitignore", filesystem_path, RootStorage(root).runtime_path]
    if manifest:
        values.append(RootStorage(root).manifest_path)
    return values


def _frontmatter_plan(document: DoctidexDocument) -> dict[str, str]:
    mapping = document.doctidex or {}
    result = {}
    for field, key in (("boundary-set", "boundary_set"), ("unsafe", "unsafe")):
        entries = mapping.get(field, [])
        exists = isinstance(entries, list) and any(
            isinstance(item, dict) and item.get("path") == ".doctidex/git/installs" for item in entries
        )
        result[key] = "existing" if exists else "add"
    return result


def _mapping_for_source(root: Path, runtime: dict[str, Any], source: Path) -> dict[str, Any] | None:
    resolved_source = source.resolve(strict=False)
    for target, link in runtime["links"].items():
        presentation = root.joinpath(*target.split("/"))
        if presentation.exists() and is_within(resolved_source, presentation.resolve(strict=False)):
            install = runtime["installs"].get(link["install_id"])
            if not install:
                return None
            base = root.joinpath(*install["install_path"].lstrip("/").split("/"))
            return {
                "install_id": link["install_id"],
                "repository_relative_path": link["repository_relative_path"],
                "base": presentation.resolve(strict=False),
            }
    for install in runtime["installs"].values():
        base = root.joinpath(*install["install_path"].lstrip("/").split("/"))
        if is_within(resolved_source, base):
            return {
                "install_id": install["install_id"],
                "repository_relative_path": ".",
                "base": base,
            }
    return None


def _mapping_for_input(root: Path, runtime: dict[str, Any], path: Path) -> dict[str, Any] | None:
    for target, link in runtime["links"].items():
        presentation = root.joinpath(*target.split("/"))
        if path == presentation or (
            presentation.exists() and is_within(path.resolve(strict=False), presentation.resolve(strict=False))
        ):
            suffix = (
                Path()
                if path == presentation
                else path.resolve(strict=False).relative_to(presentation.resolve(strict=False))
            )
            return {
                **link,
                "created_by": "link",
                "presentation_path": presentation,
                "repository_relative_path": _posix_join(link["repository_relative_path"], suffix.as_posix()),
            }
    for install in runtime["installs"].values():
        presentation = root.joinpath(*install["install_path"].lstrip("/").split("/"))
        if path == presentation or is_within(path.resolve(strict=False), presentation):
            suffix = path.resolve(strict=False).relative_to(presentation).as_posix()
            return {
                "install_id": install["install_id"],
                "created_by": "install",
                "presentation_path": presentation,
                "repository_relative_path": suffix or ".",
                "safe_state": "unsafe",
                "responsible_index": str(root / "index.md"),
            }
    return None


def _portable_mapping(
    owner_root: Path,
    runtime: dict[str, Any],
    path: Path,
    content_root: Path | None,
) -> dict[str, Any] | None:
    if content_root is None or not path.is_symlink():
        return None
    parent = next(
        (
            item
            for item in runtime["installs"].values()
            if is_within(content_root, owner_root.joinpath(*item["install_path"].lstrip("/").split("/")))
        ),
        None,
    )
    if not parent:
        return None
    try:
        manifest = RootStorage(content_root).read_manifest(required=True)
    except DoctidexError as exc:
        raise _mapping_error("external_link_parse", path) from exc
    relative = path.relative_to(content_root).as_posix()
    link = manifest.get("links", {}).get(relative)
    if not isinstance(link, dict):
        return None
    source = manifest.get("installs", {}).get(link.get("install_id"))
    if not isinstance(source, dict):
        raise _mapping_error("external_link_parse", path)
    expected_path = content_root.joinpath(*source["install_path"].lstrip("/").split("/"))
    repository_relative = link["repository_relative_path"]
    if repository_relative != ".":
        expected_path = expected_path.joinpath(*repository_relative.split("/"))
    try:
        if os.readlink(path) != os.path.relpath(expected_path, path.parent):
            raise _mapping_error("external_link_parse", path)
    except OSError as exc:
        raise _mapping_error("external_link_parse", path) from exc
    return {
        "parent_id": parent["install_id"],
        "link": link,
        "source": source,
        "repository_relative_path": repository_relative,
    }


def _safe_state(source: Path) -> str:
    roots = [context for context in discover_roots(source) if context.root == source]
    if not roots:
        return "unsafe"
    result = validate_protocol(roots[0], limit=1000)
    return "safe" if result["protocol_structure"] == "pass" and result["scan_complete"] else "unsafe"


def _responsible_index(root: Path, target_parent: Path) -> Path:
    current = target_parent
    while is_within(current, root):
        candidate = current / "index.md"
        if candidate.is_file():
            try:
                document = DoctidexDocument.load(candidate)
                if document.doctidex and document.doctidex.get("type") == "index":
                    return candidate
            except DoctidexError:
                pass
        if current == root:
            break
        current = current.parent
    return root / "index.md"


def _link_frontmatter_plan(index_path: Path, relative: str, safe_state: str) -> dict[str, str]:
    document = DoctidexDocument.load(index_path)
    mapping = document.doctidex or {}
    boundary = _contains_entry(mapping.get("boundary-set"), relative)
    unsafe = _contains_entry(mapping.get("unsafe"), relative)
    return {
        "boundary_set": "existing" if boundary else "add",
        "unsafe": "remove"
        if safe_state == "safe" and unsafe
        else ("not_required" if safe_state == "safe" else ("existing" if unsafe else "add")),
    }


def _link_frontmatter_ownership(index_path: Path, relative: str, safe_state: str) -> dict[str, str]:
    document = DoctidexDocument.load(index_path)
    mapping = document.doctidex or {}
    boundary = _contains_entry(mapping.get("boundary-set"), relative)
    unsafe = _contains_entry(mapping.get("unsafe"), relative)
    return {
        "boundary_set": "preserved" if boundary else "managed",
        "unsafe": (
            "removed"
            if safe_state == "safe" and unsafe
            else ("absent" if safe_state == "safe" else ("preserved" if unsafe else "managed"))
        ),
    }


def _frontmatter_ownership_from_record(record: dict[str, Any]) -> dict[str, str] | None:
    ownership = record.get("frontmatter_ownership")
    if ownership is None:
        return None
    if not isinstance(ownership, dict):
        raise ValueError("frontmatter ownership must be an object")
    boundary = ownership.get("boundary_set")
    unsafe = ownership.get("unsafe")
    if boundary not in {"managed", "preserved"} or unsafe not in {
        "managed",
        "preserved",
        "removed",
        "absent",
    }:
        raise ValueError("frontmatter ownership values are invalid")
    return {"boundary_set": str(boundary), "unsafe": str(unsafe)}


def _assert_link_frontmatter(index_path: Path, relative: str, safe_state: str) -> None:
    if safe_state not in {"safe", "unsafe"}:
        raise ValueError("safe state is invalid")
    document = DoctidexDocument.load(index_path)
    mapping = document.doctidex or {}
    if not _contains_entry(mapping.get("boundary-set"), relative):
        raise ValueError("boundary declaration is missing")
    unsafe = _contains_entry(mapping.get("unsafe"), relative)
    if (safe_state == "unsafe" and not unsafe) or (safe_state == "safe" and unsafe):
        raise ValueError("unsafe declaration does not match mapping")


def _rebind_frontmatter_plan(
    index_path: Path,
    relative: str,
    *,
    previous_safe_state: str,
    safe_state: str,
    ownership: dict[str, str] | None,
) -> tuple[dict[str, str], dict[str, str]]:
    _assert_link_frontmatter(index_path, relative, previous_safe_state)
    document = DoctidexDocument.load(index_path)
    mapping = document.doctidex or {}
    unsafe_present = _contains_entry(mapping.get("unsafe"), relative)
    previous = ownership or {"boundary_set": "preserved", "unsafe": "preserved"}
    updated = {"boundary_set": previous["boundary_set"], "unsafe": previous["unsafe"]}
    if safe_state == "unsafe":
        if unsafe_present:
            if previous_safe_state == "safe":
                updated["unsafe"] = "preserved"
            return {"boundary_set": "existing", "unsafe": "existing"}, updated
        updated["unsafe"] = "managed"
        return {"boundary_set": "existing", "unsafe": "add"}, updated
    if unsafe_present:
        updated["unsafe"] = "absent" if previous["unsafe"] == "managed" else "removed"
        return {"boundary_set": "existing", "unsafe": "remove"}, updated
    if previous_safe_state == "safe" and previous["unsafe"] == "removed":
        updated["unsafe"] = "removed"
    else:
        updated["unsafe"] = "absent"
    return {"boundary_set": "existing", "unsafe": "not_required"}, updated


def _unlink_frontmatter_plan(ownership: dict[str, str] | None) -> dict[str, str]:
    if ownership is None:
        return {"boundary_set": "preserved", "unsafe": "preserved"}
    return {
        "boundary_set": "remove" if ownership["boundary_set"] == "managed" else "preserved",
        "unsafe": (
            "remove"
            if ownership["unsafe"] == "managed"
            else ("restore" if ownership["unsafe"] == "removed" else "preserved")
        ),
    }


def _apply_link_frontmatter(index_path: Path, relative: str, safe_state: str) -> bool:
    document = DoctidexDocument.load(index_path)
    mapping = document.doctidex
    if mapping is None:
        mapping = CommentedMap({"type": "index"})
        document.data["doctidex"] = mapping
    changed = _ensure_entry(mapping, "boundary-set", relative)
    if safe_state == "unsafe":
        changed = _ensure_entry(mapping, "unsafe", relative) or changed
    else:
        changed = _remove_entry(mapping, "unsafe", relative) or changed
    if changed:
        document.write()
    return changed


def _apply_unlink_frontmatter(index_path: Path, relative: str, ownership: dict[str, str] | None) -> bool:
    if ownership is None:
        return False
    document = DoctidexDocument.load(index_path)
    mapping = document.doctidex
    if mapping is None:
        raise ValueError("link configuration is missing")
    changed = False
    if ownership["boundary_set"] == "managed":
        changed = _remove_entry(mapping, "boundary-set", relative)
    if ownership["unsafe"] == "managed":
        changed = _remove_entry(mapping, "unsafe", relative) or changed
    elif ownership["unsafe"] == "removed":
        changed = _ensure_entry(mapping, "unsafe", relative) or changed
    if changed:
        document.write()
    return changed


def _ensure_entry(mapping: CommentedMap, field: str, relative: str) -> bool:
    values = mapping.get(field)
    if not isinstance(values, list):
        values = CommentedSeq()
        mapping[field] = values
    if _contains_entry(values, relative):
        return False
    values.append(CommentedMap({"path": relative}))
    return True


def _remove_entry(mapping: CommentedMap, field: str, relative: str) -> bool:
    values = mapping.get(field)
    if not isinstance(values, list):
        return False
    original = len(values)
    values[:] = [item for item in values if not (isinstance(item, dict) and item.get("path") == relative)]
    return len(values) != original


def _contains_entry(values: object, relative: str) -> bool:
    return isinstance(values, list) and any(isinstance(item, dict) and item.get("path") == relative for item in values)


def _validate_target_path(value: str, *, operation: str = "external_link") -> PurePosixPath:
    path = PurePosixPath(value)
    if value.startswith("/") or not value or any(part in {"", ".", ".."} for part in path.parts):
        raise DoctidexError(
            "The external link target must be a non-empty normalized root-relative POSIX path.",
            operation=operation,
            affected=[value],
            actions=["Pass a path such as external/design."],
            requires_user="target_path",
            code="path_invalid",
            domain="external",
        )
    return path


def _join_repository_path(base: str, source: Path, install_base: Path) -> str:
    suffix = source.resolve(strict=False).relative_to(install_base.resolve(strict=False)).as_posix()
    return _posix_join(base, suffix)


def _posix_join(base: str, suffix: str) -> str:
    values = [value for value in (base, suffix) if value not in {"", "."}]
    return "/".join(values) if values else "."


def _git_ignored(repository: Path, path: Path, *, operation: str = "external_link") -> bool:
    result = git(
        ["-C", str(repository), "check-ignore", "--quiet", "--", str(path)], operation=operation, check=False
    )
    return result.returncode == 0


def _probe_symlink(target: Path) -> None:
    parent = target.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    temporary = Path(tempfile.mkdtemp(prefix=".doctidex-symlink-", dir=parent))
    try:
        probe = temporary / "link"
        probe.symlink_to("target", target_is_directory=True)
    except OSError as exc:
        raise DoctidexError(
            "The platform or filesystem could not create the required relative symlink.",
            operation="external_link",
            affected=[str(target)],
            actions=["Run on a filesystem and account that permit symbolic links."],
            code="symlink_unsupported",
            domain="external",
            path=str(target),
        ) from exc
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def _assert_manifest_trackable(repository: Path, manifest: Path, *, operation: str = "external_install") -> None:
    if not _git_ignored(repository, manifest, operation=operation):
        return
    raise DoctidexError(
        "The host Git ignore rules would hide the external recovery manifest.",
        operation=operation,
        affected=[str(manifest)],
        actions=["Adjust the host ignore rules so the manifest remains trackable, then rerun the dry-run."],
        requires_user="git_tracking",
        code="git_exclusion_conflict",
        domain="external",
        path=str(manifest),
    )


def _worktree_head(path: Path) -> str | None:
    result = git(["-C", str(path), "rev-parse", "HEAD"], operation="worktree_state", check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _file_state_or_planned(repository: Path, path: Path) -> str:
    return git_file_state(repository, path) if path.exists() else "absent"


def _paths_overlap(first: PurePosixPath, second: PurePosixPath) -> bool:
    return first == second or first in second.parents or second in first.parents


def _same_link_mapping(first: object, second: object) -> bool:
    if not isinstance(first, dict) or not isinstance(second, dict):
        return False
    keys = (
        "target_path",
        "install_id",
        "repository_relative_path",
        "safe_state",
        "responsible_index",
    )
    return all(first.get(key) == second.get(key) for key in keys)


def _prepare_replacement_symlink(target: Path, relative_source: str, *, operation: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.rebind-", dir=target.parent)
    temporary = Path(name)
    try:
        os.close(descriptor)
        temporary.unlink()
        temporary.symlink_to(relative_source, target_is_directory=True)
        return temporary
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise DoctidexError(
            "The platform or filesystem could not prepare the required relative symlink.",
            operation=operation,
            affected=[str(target)],
            actions=["Run on a filesystem and account that permit symbolic links."],
            code="symlink_unsupported",
            domain="external",
            path=str(target),
        ) from exc


def _restore_item_payload(record: dict[str, Any], state: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "install_id": record["install_id"],
        "install_path": record["install_path"],
        "source_url": record["source_url"],
        "revision_selector": record["revision_selector"],
        "default_branch": record.get("default_branch"),
        "resolved_commit": record["resolved_commit"],
        "state": state,
        "findings": findings,
    }


def _restore_runtime_mapping(
    runtime: dict[str, Any],
    identifier: str,
    record: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    runtime["installs"][identifier] = record
    for target, link in manifest["links"].items():
        if isinstance(link, dict) and link.get("install_id") == identifier:
            runtime["links"][target] = link


def _restore_blocked(identifier: str, code: str, message: str) -> dict[str, Any]:
    return {
        "install_id": identifier,
        "install_path": None,
        "source_url": None,
        "revision_selector": None,
        "default_branch": None,
        "resolved_commit": None,
        "state": "blocked",
        "findings": [finding("external", "error", code, message, actions=["Correct the item and retry restore."])],
    }


def _mapping_error(operation: str, path: Path) -> DoctidexError:
    return DoctidexError(
        "The managed external mapping is internally inconsistent.",
        operation=operation,
        affected=[str(path)],
        actions=["Preserve the path and repair or recreate the exact mapping."],
        code="mapping_damaged",
        domain="external",
        path=str(path),
    )


def _remove_damaged(identifier: str, path: Path, message: str) -> DoctidexError:
    return DoctidexError(
        message,
        operation="external_remove",
        affected=[identifier, str(path)],
        actions=["Preserve the managed state and repair the exact install before retrying remove."],
        code="mapping_damaged",
        domain="external",
        path=str(path),
    )


def _unique_paths(values: list[Path]) -> list[Path]:
    return list(dict.fromkeys(values))
