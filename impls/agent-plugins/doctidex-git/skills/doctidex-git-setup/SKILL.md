---
name: doctidex-git-setup
description: Create or adopt a doctidex root inside a Git working tree. Use when asked to initialize doctidex, repair required root markers, add the mount exclusion and root Git ignore rule, or assess an existing directory before adoption.
---

# Doctidex Git Setup

If the common path, root, CLI, and output model is not already established, load
`$doctidex-git-guide` before continuing.

## Terms

- **Requested path**: the filesystem directory the user wants to initialize.
- **Selected root**: an existing containing doctidex root, or the requested path when no root
  exists. Nested matches require an exact choice.
- **Planned changes**: files `init --dry-run` says need deterministic structure updates.
- **Semantic candidate**: an existing child that may need recognizable root-index prose or a link;
  inspect the prose before changing it.
- **Plugin readiness**: whether the Git ignore state supports later mount operations; it is separate
  from protocol structure.

## Command Contract

### Discover context

```bash
doctidex-git context PATH --json
```

`PATH` is a filesystem file or directory. No root produces `status: warning`, not a blocked error;
that is the normal pre-init state. More than one containing root requires retrying with an exact
root path.

### Preview and initialize

```bash
doctidex-git init PATH --dry-run --json
doctidex-git init PATH --apply --json
```

`init` requires PATH to be inside a Git working tree. If PATH is already inside one existing
doctidex root, that root is selected; use the exact intended directory to avoid adopting the wrong
scope. Dry-run is offline and returns `planned_changes` without writing. Apply may update only root
`index.md` structure and the root `.gitignore`; it does not write index prose, create `log.md`, add
mounts, commit, or access a remote.

### Check the result

```bash
doctidex-git check ROOT --json
```

Pass the exact selected root. Interpret `protocol_structure`, `semantic_review`, and
`plugin_readiness` independently.

## Workflow

1. Discover context and select exactly one root.
2. Run init dry-run. Explain `root`, `planned_changes`, `network: false`, and that no commit occurs.
3. Inspect existing `index.md`, `.gitignore`, root children, and unrelated Git changes with native
   tools. Preserve body text and unknown frontmatter.
4. Obtain write authorization, then run init apply.
5. Review each `semantic_candidate`. Keep sufficient prose; otherwise author the description and
   appropriate link yourself.
6. Run check on the exact root and inspect the actual Git diff.

## Result and Failures

Use `applied` to distinguish preview from apply. In dry-run, `changed` is empty while
`planned_changes` names files; after apply, `changed` names files the operation wrote.

If `git_worktree_required`, ask for a Git-managed target. If `root_ambiguous`, ask for or select the
exact root. If semantic review remains required, report the undecided entries rather than claiming
setup is complete. Never commit, reset, clean, or remove tracked content automatically.
