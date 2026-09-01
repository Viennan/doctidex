from __future__ import annotations

from whero.doctidex.hooks import _merge_share_membership
from whero.doctidex.model import InstallationContextReference, InstallationShare


def _share(
    *,
    commit_hash: str,
    install_ids: tuple[str, ...],
    context_references: tuple[InstallationContextReference, ...] = (),
    branch_refs: tuple[str, ...] = ("main",),
) -> InstallationShare:
    return InstallationShare(
        git_url="https://example.test/repository.git",
        commit_hash=commit_hash,
        install_path=f"/.doctidex-git/imports/example/commit/{commit_hash}",
        install_ids=install_ids,
        context_references=context_references,
        branch_refs=branch_refs,
    )


def test_merge_replaces_membership_but_preserves_current_branch_refs() -> None:
    current = _share(commit_hash="current", install_ids=("old",), branch_refs=("main", "feature"))
    target = _share(
        commit_hash="current",
        install_ids=("new",),
        context_references=(
            InstallationContextReference(install_id="child", owner_install_id="owner"),
        ),
        branch_refs=("feature",),
    )

    merged = _merge_share_membership([current.to_json()], (target,))

    assert merged == (
        _share(
            commit_hash="current",
            install_ids=("new",),
            context_references=(
                InstallationContextReference(install_id="child", owner_install_id="owner"),
            ),
            branch_refs=("main", "feature"),
        ),
    )


def test_merge_does_not_import_target_only_share() -> None:
    current = _share(commit_hash="current", install_ids=("old",))
    target_only = _share(commit_hash="target-only", install_ids=("target",))

    merged = _merge_share_membership([current.to_json()], (target_only,))

    assert _share_key(merged[0]) == ("https://example.test/repository.git", "current")
    assert all(share.commit_hash != "target-only" for share in merged)


def test_merge_keeps_current_only_share_with_empty_membership() -> None:
    current_only = _share(commit_hash="current-only", install_ids=("old",), branch_refs=("main", "feature"))

    merged = _merge_share_membership([current_only.to_json()], ())

    assert merged == (
        _share(commit_hash="current-only", install_ids=(), branch_refs=("main", "feature")),
    )


def _share_key(share: InstallationShare) -> tuple[str, str]:
    return (share.git_url, share.commit_hash)
