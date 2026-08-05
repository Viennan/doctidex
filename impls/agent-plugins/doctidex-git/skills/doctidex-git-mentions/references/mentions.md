# Resolve Mention Facts

Use this reference after `$doctidex-git-overview` and before either command below. Both commands are
offline and read-only. They return facts for a caller to report or hand off; neither authorizes a later
write.

## Discover Current Managed Installs

```text
doctidex-git external list [--root ROOT]
  [--repository REPOSITORY_PATH] [--host HOST]
  [--commit COMMIT | --tag TAG | --branch BRANCH]
  [--role direct | --role dependency]
  [--limit N] [--cursor TOKEN] --json
```

`ROOT` is the exact selected owner root or defaults from cwd. This command reads only its current managed
install/link records. It does not access a remote, payload, manifest, cache, symlink, ordinary Git
repository, worktree, unmanaged clone, another root, or unexpanded portable dependency.

`REPOSITORY_PATH` is the readable source path, such as `Viennan/wiki` from
`git@github.com:Viennan/wiki.git`; it is not a URL, filesystem path, credential, or install ID. Optional
host, tag, branch, full commit, and repeated role filters intersect recorded facts. Branch/tag provenance
is not re-resolved. Read the normalized `query`, `items`, and `collection`; each item has a sanitized
source URL, host/path, selector, fixed commit, role, state, presentation paths, and opaque exact ID.
Empty and multi-item results are successful queries that require the agent to report candidates rather
than choose one. Same paths from different hosts are different candidates. Reuse a cursor unchanged with
the same root, filters, and limit; restart from the first page on `cursor_invalid`.

## Interpret an Exact External Link

```text
doctidex-git external link-parse PATH [--root ROOT] --json
```

`PATH` is one existing readable directory or symlink; a broken symlink itself is valid, but a nonexistent
path or ordinary file is rejected. The command is single-result, offline, read-only, and has no dry-run,
apply, limit, or cursor. With no `--root`, it recovers the unique outer owner; an explicit root must be
that outer owner, not an installed repository's content root.

Read `managed`, `mapping_origin`, `target_state`, `root`, `content_root`, `presentation_path`, source/
selector/fixed-commit facts, current install fields, and `working_path`. For `available`, continue native
reading at `working_path`. `owner_install_missing` preserves the durable link and can later be restored
by Maintenance. `dependency_not_installed` exposes exact source, full commit, and dependency parent for
an optional later Maintenance action; do not re-resolve branch/tag provenance. `not_applicable` returns
to native diagnosis. `unavailable` preserves mapping-damage evidence. Do not treat an unmanaged path or
portable unexpanded dependency as a current managed install.
