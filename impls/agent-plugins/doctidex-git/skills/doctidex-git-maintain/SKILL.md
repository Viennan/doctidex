---
name: doctidex-git-maintain
description: Maintain content within one explicitly selected doctidex root and its Git working tree. Use when updating documents, indexes, or logs while respecting atomic, excluded, protected, and mount boundaries and preserving unrelated user changes.
---

# Doctidex Git Maintain

If the common path, root, CLI, and output model is not already established, load
`$doctidex-git-guide` before continuing.

## Terms

- **Maintenance scope**: exactly one selected doctidex root for this Skill. Use Workspace when a
  task crosses roots.
- **Responsible index**: the nearest valid `index.md` that describes an included path.
- **Applicable log**: the nearest optional `log.md` whose scope may record an important change.
- **Atomic**: index the directory as one unit; do not add index/log files inside it.
- **Excluded**: outside this root's doctidex content and maintenance scope.
- **Protected**: readable, but do not write without explicit user direction.
- **Host mount path**: excluded and read-only from the host; change its source through Workspace.

## Command Contract

| Command | Argument meaning | Use |
|---|---|---|
| `doctidex-git context PATH --json` | PATH is a filesystem file or directory. | Select one root; retry with its exact directory if ambiguous. |
| `doctidex-git inspect PATH --json` | PATH may be the file or directory to change. | Read scope, attributes, responsible index/log, and mount membership. Offline and read-only. |
| `doctidex-git changes ROOT --json` | Pass the root or another Git directory, not an individual file; the command runs Git status at that path. | Capture pre-existing and final changes. It does not return diff content. |
| `doctidex-git check ROOT --json` | Prefer the exact root directory. | Perform offline structure, semantic-candidate, and plugin-readiness checks. |

Use native file and search tools for content and native Git diff tools for line-level changes. CLI
`links`, findings, and candidates are assistance, not a replacement for reading.

## Workflow

1. Select exactly one root and record existing Git changes.
2. Inspect each intended target before writing. If `source: mount`, stop and load
   `$doctidex-git-workspace`. If `host_scope: excluded`, do not maintain it as part of this root. If
   `protected` is present, require explicit user direction.
3. Read the responsible index, target content, and applicable log when history matters. Expand
   native search when those files are insufficient.
4. Edit content using native tools. Author all prose, summaries, index entries, and log entries
   using your own judgment.
5. Update the responsible index only when the real content change requires it. Preserve sufficient
   existing prose instead of mechanically adding every semantic candidate.
6. If an applicable log exists, record only changes important to that log's scope; do not create a
   log solely because the CLI found a Git change.
7. Run check and changes on the exact root, then inspect the actual Git diff.

## Interpret Results

- `path_context.attributes` is a set; atomic/protected may coexist.
- `semantic_candidates` require reading. `index_reference_candidate` means no exact machine-parsed
  link was found, not that prose is missing.
- `git_change_review` means consider index/log follow-up, not that both files must change.
- `protocol_structure: fail` is a deterministic structure problem.
- `plugin_readiness: blocked` concerns Git mount prerequisites and is not automatically a protocol
  failure.

Report changed files, responsible index/log decisions, validation facts, pre-existing changes kept,
and unresolved user actions. Do not commit, push, reset, clean, switch the user's branch, or discard
unrelated work.
