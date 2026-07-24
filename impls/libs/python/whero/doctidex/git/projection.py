from __future__ import annotations

import os
import shutil
import stat
import tempfile
from pathlib import Path

from whero.doctidex.errors import DoctidexError

from .state import StateStore, file_lock, stable_key


def build_projection(root: Path, mount_path: str, source: Path, commit: str) -> Path:
    store = StateStore(root)
    projections = store.directory / "projections"
    projections.mkdir(parents=True, exist_ok=True)
    key = stable_key(f"{mount_path}\0{commit}")
    target = projections / key
    with file_lock(projections / f".{key}.lock"):
        if target.is_dir():
            return target
        temporary = Path(tempfile.mkdtemp(prefix=".projection.", dir=projections))
        namespace = root / ".doctidex" / "mounts"
        namespace.mkdir(parents=True, exist_ok=True)
        try:
            _mirror_directory(source, temporary, namespace, inject_namespace=True)
            _make_projection_read_only(temporary)
            try:
                os.replace(temporary, target)
            except FileExistsError:
                shutil.rmtree(temporary)
            return target
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise


def present_projection(root: Path, mount_path: str, projection: Path, *, replace_managed: bool) -> Path:
    destination = root.joinpath(*mount_path.lstrip("/").split("/"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    occupied = destination.is_symlink() or destination.exists()
    if occupied and not replace_managed:
        raise DoctidexError(
            f"The mount path already contains files: {mount_path}",
            operation="mount_prepare",
            affected=[mount_path],
            actions=["Move unrelated content out of the declared mount path and retry."],
            requires_user="mount_path",
            code="mount_path_occupied",
        )
    if destination.exists() and not destination.is_symlink():
        raise DoctidexError(
            "The existing managed mount presentation is not safely replaceable.",
            operation="mount_prepare",
            affected=[mount_path],
            actions=["Retry after checking that no files were placed directly in the mount path."],
            code="mount_path_occupied",
        )
    temporary_link = destination.parent / f".{destination.name}.next-{os.getpid()}"
    temporary_link.unlink(missing_ok=True)
    try:
        temporary_link.symlink_to(projection, target_is_directory=True)
        os.replace(temporary_link, destination)
    except OSError:
        temporary_link.unlink(missing_ok=True)
        temporary_directory = Path(tempfile.mkdtemp(prefix=f".{destination.name}.next-", dir=destination.parent))
        try:
            shutil.rmtree(temporary_directory)
            shutil.copytree(projection, temporary_directory, symlinks=True, copy_function=os.link)
            os.replace(temporary_directory, destination)
        except OSError as fallback:
            shutil.rmtree(temporary_directory, ignore_errors=True)
            raise DoctidexError(
                "The external directory tree could not be made readable in the working environment.",
                operation="mount_prepare",
                affected=[mount_path],
                actions=["Retry in a working directory that permits normal directory presentation."],
                code="mount_unreadable",
            ) from fallback
    return destination


def remove_presentation(root: Path, mount_path: str, *, managed: bool) -> None:
    destination = root.joinpath(*mount_path.lstrip("/").split("/"))
    if destination.is_symlink() and managed:
        destination.unlink()
    elif destination.exists() and managed:
        shutil.rmtree(destination)


def _mirror_directory(source: Path, target: Path, namespace: Path, *, inject_namespace: bool) -> None:
    target.mkdir(parents=True, exist_ok=True)
    source_doctidex: Path | None = None
    for entry in sorted(source.iterdir(), key=lambda item: item.name):
        if entry.name == ".git":
            continue
        destination = target / entry.name
        if entry.name == ".doctidex" and entry.is_dir() and not entry.is_symlink():
            source_doctidex = entry
            continue
        if entry.is_dir() and not entry.is_symlink():
            _mirror_directory(entry, destination, namespace, inject_namespace=True)
        elif entry.is_symlink():
            destination.symlink_to(entry.resolve(strict=False), target_is_directory=entry.is_dir())
        else:
            os.link(entry, destination)

    if not inject_namespace:
        return
    projected_doctidex = target / ".doctidex"
    projected_doctidex.mkdir(exist_ok=True)
    if source_doctidex:
        _mirror_doctidex(source_doctidex, projected_doctidex, namespace)
    mount_link = projected_doctidex / "mounts"
    if mount_link.exists() or mount_link.is_symlink():
        if mount_link.is_dir() and not mount_link.is_symlink():
            shutil.rmtree(mount_link)
        else:
            mount_link.unlink()
    mount_link.symlink_to(namespace, target_is_directory=True)


def _mirror_doctidex(source: Path, target: Path, namespace: Path) -> None:
    for entry in sorted(source.iterdir(), key=lambda item: item.name):
        if entry.name == "mounts":
            continue
        destination = target / entry.name
        if entry.is_dir() and not entry.is_symlink():
            _mirror_directory(entry, destination, namespace, inject_namespace=False)
        elif entry.is_symlink():
            destination.symlink_to(entry.resolve(strict=False), target_is_directory=entry.is_dir())
        else:
            os.link(entry, destination)


def _make_projection_read_only(root: Path) -> None:
    directories: list[Path] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        directories.append(current)
        for filename in filenames:
            path = current / filename
            if path.is_symlink():
                continue
            path.chmod(path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        dirnames[:] = [name for name in dirnames if not (current / name).is_symlink()]
    for directory in reversed(directories):
        directory.chmod(directory.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
