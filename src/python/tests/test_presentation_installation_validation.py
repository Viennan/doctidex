from __future__ import annotations

import hashlib

from whero.doctidex.model import InstallationContextReference, InstallationShare, RuntimeState
from whero.doctidex.validate import _context_reference_violations


def _share(
    *,
    commit_hash: str,
    install_path: str,
    context_references: tuple[InstallationContextReference, ...] = (),
) -> InstallationShare:
    return InstallationShare(
        git_url="https://example.test/repository.git",
        commit_hash=commit_hash,
        install_path=install_path,
        install_ids=(),
        context_references=context_references,
        branch_refs=("main",),
    )


def test_context_reference_owner_may_be_derived_presentation_installation() -> None:
    owner_share = _share(
        commit_hash="owner",
        install_path="/.doctidex-git/imports/example/commit/owner",
    )
    owner_install_id = hashlib.sha256(owner_share.install_path.encode("utf-8")).hexdigest()[:16]
    targeted_share = _share(
        commit_hash="targeted",
        install_path="/.doctidex-git/imports/example/commit/targeted",
        context_references=(
            InstallationContextReference(install_id="child", owner_install_id=owner_install_id),
        ),
    )
    state = RuntimeState(
        custom_boundary_points=(),
        installations=(),
        refs=(),
        worktrees=(),
        installation_shares=(owner_share, targeted_share),
        branch_snapshots={},
    )

    violations = _context_reference_violations(state)

    assert all(item["code"] != "installation.context-reference.owner.missing" for item in violations)
