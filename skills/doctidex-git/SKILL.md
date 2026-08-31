---
name: doctidex-git
description: Use doctidex-git to make Git repositories interoperable knowledge nodes by initializing a workspace, installing fixed external revisions, creating Refs, writing annotated cross-boundary links, creating editable Worktrees, and validating or repairing managed state.
---

# doctidex-git

This is a guide, not a script. The files under `references/` are the authoritative, detailed reference;
[overview.md](references/overview.md) is required reading before any command.

## Before you start

- Work from inside a Git repository, or pass `--repos-path <REPOSITORY-ROOT>`.
- Confirm `doctidex-git` is on `PATH`.
- Have `rg` available when possible; the CLI falls back to a slower Python scan when it is missing.
- Read [overview.md](references/overview.md) to establish the shared mental model: Git root, Installation, Ref,
  Worktree, BoundaryPoint, and StructuredLinkAnnotation.

## When to use it

Reach for `doctidex-git` when a repository needs to:

- reference another Git repository at one fixed revision without vendoring it;
- expose a stable, read-only path into that revision through a Ref;
- make a temporary editable copy of an installed revision without changing the Installation;
- keep cross-boundary Markdown links and the repository's boundary rules consistent.

It does not replace Git, and it does not rewrite commit history.

## Common working scenarios

### Bootstrap a repository

For a repository that does not yet have `.doctidex-git/`, initialize and verify:

```bash
doctidex-git init
doctidex-git validate --model-structure
```

`init` creates the workspace and installs the supported Git hooks.

For a fresh clone, `.doctidex-git/` already exists but the local Git hooks do not. Reinstall hooks and verify:

```bash
doctidex-git hook install
doctidex-git validate --model-structure
```

See [init.md](references/init.md), [hook.md](references/hook.md), and [validate.md](references/validate.md).

### Install and reference a fixed external revision

When a document needs content from another repository at a known commit, install that revision and expose it with a
Ref:

```bash
doctidex-git import install \
  --tracked \
  --url <GIT-URL> \
  --branch <BRANCH>

doctidex-git import ref \
  --install-id <INSTALL-ID> \
  [--src-sub-dir /<INSTALL-REPOSITORY-PATH>] \
  --target-dir /external/<NAME>
```

`import install` stores the revision under the managed `/.doctidex-git/imports/` path. A Ref exposes that content at a
short repository path such as `/external/<NAME>`, so related documents can sit nearby. Prefer a Ref over linking
directly into the managed install path; use `--src-sub-dir` to link only a relevant subdirectory of the Installation.

Use `--tracked` for references that must persist across clones; use `--untracked` for temporary references that do not
need persistent tracking. A branch or tag resolves once to a commit, so re-run `import install` only when the revision
should change.

In a fresh clone, a tracked Installation is metadata-only until restored. Before accessing it, run:

```bash
doctidex-git import restore --install-id <INSTALL-ID>
```

See [import.md](references/import.md) for selector, Ref, and removal rules.

### Link across a boundary

After creating a Ref, write the link relative to the Git root and follow it with the StructuredLinkAnnotation that
names the first crossed BoundaryPoint:

```markdown
[External](/external/<NAME>/path/to/doc.md)
<!-- doctidex: {cross-boundary-point: /external/<NAME>} -->
```

Paths beginning with `/` are rooted at the Git root; other paths are relative to the source document. Prefer relative
links when they express the same target. See [overview.md](references/overview.md) and [common.md](references/common.md).

### Modify external content safely

An Installation is read-only. When the work needs to edit, branch, or commit from that revision, create an editable
Worktree instead:

```bash
doctidex-git worktree create \
  --install-id <INSTALL-ID> \
  --work-path /projects/<NAME>
```

The Worktree starts from the Installation's recorded commit and may branch, modify, and commit freely. See
[worktree.md](references/worktree.md).

### Add a custom boundary

When an ordinary vendored or local directory should also stop the link scan, declare it as a custom BoundaryPoint:

```bash
doctidex-git boundary-set add --path /vendor/<NAME>
doctidex-git boundary-set parse --path /vendor/<NAME>/readme.md
```

See [boundary-set.md](references/boundary-set.md).

### Check and repair state

After changing links or boundaries, validate before repairing:

```bash
doctidex-git validate
doctidex-git repair
```

`validate` is read-only. `repair` aligns recoverable physical state; it does not rewrite Markdown links or roll back Git
history. See [validate.md](references/validate.md) and [repair.md](references/repair.md).

## Rules you must follow

- Never edit the state JSON under `.doctidex-git/` by hand.
- Treat Installation directories as read-only; create a Worktree when a revision must be modified.
- Never remove or rename managed Installation, Worktree, Ref, or boundary paths by hand.
- Always place a `doctidex` StructuredLinkAnnotation immediately after a Markdown link that crosses a BoundaryPoint.
- Run `validate` after changing links or boundaries; run `repair` only to recover physical state, not to rewrite
  document content.

For shared result envelopes, structured errors, and Installation-context behavior, use
[common.md](references/common.md).
