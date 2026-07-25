---
name: doctidex-git-review
description: Review doctidex-aware Git changes for one or multiple roots before delivery. Use when checking content changes, index or log follow-up, filtering and protection boundaries, mount revision impact, and unresolved Git actions without modifying the working tree.
---

# Doctidex Git Review

If the common path, root, CLI, and output model is not already established, load
`$doctidex-git-guide` before continuing.

## Terms

- **Independent root**: one host or maintenance root with its own base revision and Git result.
- **Scope violation**: a change outside the intended root, through a host mount, inside excluded
  content, or across an unauthorized protected boundary.
- **Semantic follow-up**: an agent decision about index prose, links, or an important log entry.
- **Selector impact**: whether delivering a mounted-source result also requires commit/push/merge
  and a later host selector update or sync.
- **Handoff**: the CLI's preserved facts for one maintenance root; it is not approval to deliver.

## Command Contract

| Command | Parameter and output |
|---|---|
| `doctidex-git changes ROOT --json` | ROOT must be a Git directory, not a file. Returns porcelain status entries only; inspect the actual diff with native Git tools. |
| `doctidex-git check ROOT --json` | Performs offline structure, semantic-candidate, and plugin-readiness checks. It does not prepare mounts. |
| `doctidex-git maintenance handoff MAINTENANCE_ROOT --json` | Use the exact path returned by open. Returns base commit, target branch hint, changes, findings, candidates, and next actions. |

Run host-root commands from or against the exact intended root. Maintenance commands still select
the host registry from the current working directory, so run handoff from the same host root used
to open the maintenance context.

## Review Workflow

For each independent root:

1. Capture structured changes and validation. For mounted-source work, also run exact handoff.
2. Check `collection` and retrieve any missing pages before claiming a complete review.
3. Inspect the native Git diff. The CLI does not return file contents or line-level patches.
4. Confirm that changes remain inside the intended write root and do not write through a host
   mount, excluded path, or unauthorized protected boundary.
5. Judge content accuracy, responsible-index sufficiency, important log follow-up, and overall
   reasonableness yourself. Treat semantic candidates as prompts, not findings.
6. Compare each mounted result with its `base_commit` and `target_branch` hint. Identify separate
   commit, push, merge, host selector update, or sync decisions.
7. Report findings by severity, then summarize each root's changed files, validation domains,
   semantic decisions, selector impact, and remaining user actions.

## Read-Only Boundary

Do not fix files, prepare or synchronize mounts, close a context, submit Git changes, or discard
work during review. If one root fails validation or cannot be read, preserve and report the results
for all other roots independently. Ask the user before any delivery or destructive Git action.
