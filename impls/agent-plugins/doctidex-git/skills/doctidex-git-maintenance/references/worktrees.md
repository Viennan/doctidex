# Use Optional Writable Worktrees

Use the current authorized host working tree directly when it already represents the desired
commit. Choose a managed worktree only for isolation, a different source/revision, or an explicit
request. Managed worktrees are flat siblings below the selected owner root and do not enter the
external recovery manifest.

## Open

```text
DOCTIDEX_GIT worktree open SOURCE [--root ROOT]
  (--commit COMMIT | --tag TAG | --branch BRANCH) --json
```

One selector is required. SOURCE classification is: existing managed presentation path, existing
Git working tree or bare gitdir, existing gitfile pointer, then Git URL. For a managed path, ROOT
must be its outer owner or is recovered from SOURCE; for other source kinds, ROOT is explicit or
defaults from cwd. A managed subdirectory preserves its repository-relative suffix. URL sources may
use the network; other kinds are offline.

Open immediately creates a new detached writable worktree; it has no dry-run/apply and never reuses
an existing path automatically. Read `worktree` plus `reuse_candidate_count`. The WorktreeItem
contains `source_kind`, `owner_root`, sanitized or null `source_url`, selector, full `base_commit`,
root-internal and filesystem worktree paths, repository-relative path, `working_path`, objective
`clean|changed|unavailable` state, and item findings. A reuse candidate produces a completed warning
but the new independent worktree exists.

## List

```text
DOCTIDEX_GIT worktree list [--root ROOT]
  [--source SOURCE | --worktree WORKTREE]
  [--limit N] [--cursor TOKEN] --json
```

ROOT is exact or defaults from cwd. Filters are mutually exclusive; source uses open's canonical
identity and worktree is an exact managed path. Omission lists the root's first page. The command is
offline and read-only. Read `items` and `collection`; unavailable items make the completed result a
warning without hiding other items. Use native Git for detailed status/diff. Resume with the opaque
cursor under the same root, filter, and limit; restart on `cursor_invalid`.

## Close

```text
DOCTIDEX_GIT worktree close WORKTREE --json
```

Pass the exact `worktree_path` returned by open/list. Close accepts no root and recovers the unique
owner. It removes only a provably managed, Git-clean worktree and its managed ownership record. It
does not remove external presentations, manual worktrees, or subdirectories.

On success, `worktree` describes the pre-close item and `changed` contains the removed path.
`worktree_changed`, `worktree_unavailable`, or `worktree_unmanaged` is blocked: `changed` is empty,
the path is preserved, and the recognized item is returned when available. Inspect with native Git;
deliver, restore, repair, or deliberately retain it based on user authority before retrying.
