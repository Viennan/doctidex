# Installation Share Store

This document defines the Installation share store for `doctidex-git`. It is authority for the machine-local sharing relation that lets several Installations use one physical detached Git worktree for the same `(git-url, commit-hash)`. The command architecture is defined by [overview.md](overview.md); transactional store behavior is defined by [stores-transactions.md](stores-transactions.md).

## Purpose and scope

An Installation is read-only and is recorded once per revision selector. A branch, a tag, and an explicit commit can all resolve to the same `(git-url, commit-hash)`. Without sharing, each would create its own Git worktree. The share store removes that duplication while keeping branch and tag `install-path` values stable and human-readable.

The share store owns Installation storage only. It does not change the Worktree service or its editable worktrees.

## Domain model

| Object | Meaning |
|---|---|
| **InstallationShare** | One machine-local relation for a Git URL and commit. It owns the shared physical worktree path and the Installation identities that reference it. |
| **InstallationContextReference** | Provenance for one sub-Installation restored from InstallationContext. |

### InstallationShare

An `InstallationShare` is persisted in `runtime.json` under `installation-shares`. It is untracked and never appears in `imports.json`.

Representative persisted shape:

```json
{
  "git-url": "<GIT-URL>",
  "commit-hash": "<HASH>",
  "install-path": "/.doctidex-git/imports/<DOMAIN>/<REPOSITORY>/<HASH>",
  "install-ids": ["<INSTALL-ID>", "<OTHER-INSTALL-ID>"],
  "context-references": [
    {
      "install-id": "<OWNER-SIDE-INSTALL-ID>",
      "owner-install-id": "<PARENT-INSTALLATION-INSTALL-ID>"
    }
  ],
  "branch-refs": ["<BRANCH>"]
}
```

Fields:

- `git-url` and `commit-hash` identify the shared revision.
- `install-path` is the single repository-internal path of the shared detached Git worktree.
- `install-ids` lists every Installation that resolves to this commit.
- `context-references` records which parent Installation produced an InstallationContext sub-Installation.
- `branch-refs` records branch names that have used this share.

The `install-ids` order has no physical meaning. `install-path` is the authority for physical worktree ownership.

## Physical storage

The share creates its real Git worktree at `install-path`. A direct commit Installation uses this exact path as its `install-path`. A branch or tag Installation keeps its selector-derived `install-path` and has a symlink to `share.install-path`.

## Install and restore

Every selector kind follows one sequence:

1. resolve the selector to `(git-url, commit-hash)`;
2. find or create the InstallationShare;
3. create the shared worktree when the share is new;
4. add the Installation `install-id` to the share;
5. make the Installation's physical object a real worktree for a direct commit or a symlink for a branch or tag.

`import restore` uses the same sequence. A tracked Installation is added to its commit share and restored as either the shared worktree or a selector symlink.

## Removal

Removing an Installation removes its `install-id` and physical path. The share and its real worktree survive while any
`install-id`, `context-reference`, or `branch-refs` entry remains. When the last reference disappears, the share and
worktree are deleted together.

There is no physical-owner transfer among Installations and no synthetic backing Installation.

## InstallationContext

`import restore` with `--installation-context <INSTALL-ID>` resolves the parent Installation by its recorded
`install-id`, records or reuses the owner-side Installation under the local `install-id`, and adds that id to the
owner share. The corresponding `InstallationContextReference` preserves which parent produced the sub-Installation.
The query surface reports owner-side restore state through `presentation-path`.

## Validation and repair

Validation checks:

- the share worktree exists and is a detached Git worktree;
- every share `install-id` resolves to a recorded Installation;
- direct commit Installations use `share.install-path`;
- branch and tag Installations symlink to `share.install-path`.

Repair aligns the shared worktree first, then restores selector symlinks and removes unregistered Installation symlinks.

## Implementation responsibilities

| Responsibility | Implementation |
|---|---|
| Share records and state projection | [model.py](../../../src/python/whero/doctidex/model.py) |
| Import install, restore, and removal | [imports.py](../../../src/python/whero/doctidex/imports.py) |
| InstallationContext restore | [installation.py](../../../src/python/whero/doctidex/installation.py) |
| Share validation and repair | [validate.py](../../../src/python/whero/doctidex/validate.py), [repair.py](../../../src/python/whero/doctidex/repair.py) |
