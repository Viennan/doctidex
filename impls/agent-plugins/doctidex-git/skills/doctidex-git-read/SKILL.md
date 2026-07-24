---
name: doctidex-git-read
description: Navigate and investigate doctidex directory trees in Git repositories while retaining unrestricted use of native agent file, search, and shell tools. Use for reading, locating design knowledge, resolving doctidex links, understanding index or log scope, or restoring a required lazy Git mount whose path is absent.
---

# Doctidex Git Read

## Prepare the CLI

Before using `doctidex-git`, verify that the `whero-doctidex` distribution is installed. In this
repository run `.venv/bin/python -m pip install -e impls/libs/python`; otherwise install
`whero-doctidex` into the active Python environment. If installation is blocked by network or
permissions, ask the user for access.

## Read Freely

Use the agent's native file reader, directory browser, editor, search tools, and shell commands.
Doctidex is a navigation aid, not a file gateway, and no CLI call is required before ordinary file
access.

Start with the root or nearest responsible `index.md` when useful. Use local indexes to narrow the
search, optional `log.md` files for change background, and native global search whenever the index
is insufficient. Atomic entries are whole indexing units but their files remain readable.
Excluded and protected files may be inspected for repository context; their maintenance semantics
still apply.

Use optional objective assistance when it saves work:

```bash
doctidex-git context PATH --json
doctidex-git inspect PATH --json
doctidex-git resolve /.doctidex/mounts/source/path --json
```

Do not treat `semantic_candidates` as confirmed gaps. Judge existing prose and task relevance
yourself.

## Restore a Required Mount

When a native tool cannot find a path that the task must read:

1. Use `resolve` or `mount list` to determine whether the path belongs to a declared mount.
2. If its state is `not_prepared`, run
   `doctidex-git mount prepare /.doctidex/mounts/<name> --json` and retry the original native tool.
3. If it is `ready` and still absent, investigate it as a real missing source path.
4. If preparation reports missing network, credentials, URL, or revision, present the supplied
   action to the user. Do not expose or manipulate internal checkout, cache, or mapping paths.

Ordinary reading never synchronizes a branch or tag. Only an explicit mount sync changes the
effective commit.
