# Issue Note: Add commit selector prefix to Installation share paths

Status: implemented

## Problem

Installation storage encodes the revision selector kind in branch and tag paths:

```text
/.doctidex-git/imports/<domain>/<repository>/branch/<value>
/.doctidex-git/imports/<domain>/<repository>/tag/<value>
```

The direct commit path omitted the kind:

```text
/.doctidex-git/imports/<domain>/<repository>/<commit-hash>
```

`_selector_install_path` in [imports.py](../../../../../src/python/whero/doctidex/imports.py) added the selector-kind
component only for branch and tag. A direct commit Installation and the `InstallationShare` that owns its worktree
therefore used a bare commit-hash directory. This broke the selector-kind-aware path convention and made the path
ambiguous with repository names and selector values. The project is in an unstable state, so this change does not
migrate records created with the old path.

## Decision

### Selector path convention

Every revision selector path includes its kind segment:

```text
/.doctidex-git/imports/<domain>/<repository>/branch/<value>
/.doctidex-git/imports/<domain>/<repository>/tag/<value>
/.doctidex-git/imports/<domain>/<repository>/commit/<commit-hash>
```

The kind segment is part of the selector-derived path and therefore part of `install-id`, because `install-id` is the
first 16 hex characters of `sha256(selector-install-path)`. Branch and tag identities are unchanged; direct commit
identities use the commit-prefixed path.

The path derivation in [imports.py](../../../../../src/python/whero/doctidex/imports.py) appends the selector kind
for every selector:

```python
def _selector_install_path(git_url: str, selector_kind: str, selector_value: str) -> str:
    domain, repository_name = repository_location(git_url)
    components = [".doctidex-git", "imports", domain, *repository_name]
    components.append(selector_kind)
    components.extend(selector_value.split("/"))
    ...
```

`commit_install_path` is the public commit-specific wrapper used by validation to derive the expected share path.

### Physical share and direct commit path

An `InstallationShare` owns its real worktree at
`/.doctidex-git/imports/<domain>/<repository>/commit/<commit-hash>`. A direct commit Installation uses
`share.install-path` directly. Branch and tag Installations keep their selector-derived paths and symlink to
`share.install-path`. The share remains the single authority for the physical worktree.

### Unified install resolution

All three selectors use one `_install_resolved` workflow. The selector-kind-specific inputs are
`(selector-kind, selector-value, branch, tag)`. The workflow:

1. uses `commit-hash` as the selector value for `commit`;
2. derives `install-path` with `_selector_install_path(git_url, selector-kind, selector-value)`;
3. derives `install-id` from that path;
4. looks up the existing Installation and rejects an id/path collision;
5. returns an existing Installation that already records the resolved commit, after ensuring its share;
6. leaves an existing Installation's old share before replacement when a branch or tag re-resolves;
7. creates or replaces the Installation with the selector's `branch`/`tag` fields and the resolved commit;
8. ensures the Installation in its commit share.

The physical distinction between a direct commit worktree and a branch/tag symlink belongs to
`_ensure_installation_in_share`.

### Validation and repair

Validation requires each `InstallationShare.install-path` to equal the selector-derived commit path for its
`(git-url, commit-hash)`, reports a mismatch as `installation.share.commit-path.invalid`, and continues to require
direct commit Installations to use `share.install-path` and branch/tag Installations to symlink to it.

Repair aligns the physical worktree at `share.install-path` and rebuilds branch and tag symlinks. It does not migrate
old bare-hash records.

## Consequences

Direct commit `install-path` values, `install-id` values, and the physical share path now include `commit/`. Branch and
tag paths and identities are unchanged.

The change removes the historical split between branch/tag and direct commit install resolution. Existing direct
commit records created with the old bare-hash path are not migrated; they may be removed and recreated under the new
convention.

## Alternatives considered

**Keep the bare commit-hash path and add a separate selector-kind field to `InstallationShare`.**
Rejected: the selector kind is already a component of branch and tag paths, and `install-id` is intentionally derived
from the path. A parallel field duplicates identity information without fixing the path convention.

**Give the share a `commit/<hash>` path but keep the direct commit Installation at the bare hash path with a symlink.**
Rejected: direct commit Installations are the share owner and should use the share path directly. Introducing a
symlink for commit selectors would remove the current direct-path distinction from branch and tag.

**Leave commit paths unchanged and treat a leading all-hex segment as a commit.**
Rejected: the distinction would depend on value shape rather than an explicit kind segment. Branch and tag names may
also be all-hex, and shape-based inference is not a durable path contract.

## Related

- [Shared commit-hash Installation storage](2026-08-26-shared-commit-hash-installation-storage.md)
- [Restore deterministic install-id from git-url and selector](2026-08-28-restore-deterministic-install-id-from-git-url-and-selector.md)
- [Remove duplicated Installation workflow branches](../simplification/2026-08-27-remove-duplicated-installation-workflow-branches.md)
