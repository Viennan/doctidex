---
name: doctidex-git-maintain
description: Build or execute one maintenance plan within an explicitly selected doctidex root and its Git working tree. Use when updating documents, indexes, or logs in one write scope, including a scope selected by the Workspace workflow, while respecting atomic, excluded, protected, and mount boundaries and preserving unrelated user changes.
---

# Doctidex Git Maintain

If the common path, root, CLI, and output model is not already established, load
`$doctidex-git-guide` before continuing.

## Terms

- **Maintenance scope**: exactly one selected doctidex root and write boundary for this Skill. Use
  Workspace to coordinate a task that has or may require multiple scopes.
- **Maintenance plan**: the agent-owned plan for this scope: objective, covered targets, selected
  root and base commit when known, authority, satisfied dependencies, index/log decisions,
  validation, and expected Git delivery. The CLI does not store the plan.
- **Current-root maintenance**: the selected local doctidex root is already its own writable host
  scope. It does not need `maintenance open`, even if a mount also references it.
- **Responsible index**: the nearest valid `index.md` that describes an included path.
- **Progressive disclosure**: give enough concise context to locate and choose the next relevant
  document, then delegate detail to child indexes and source documents.
- **Applicable log**: the nearest optional `log.md` whose scope may record an important change.
- **Atomic**: index the directory as one unit; do not add index/log files inside it. Other content
  and links inside the unit are opaque to recursive protocol conformance; use native tools and the
  task's own requirements when working with them.
- **Excluded**: outside this root's doctidex content and maintenance scope.
- **Protected**: readable and protected from default maintenance. Do not write unless the user
  explicitly authorizes the exact target or authorizes changing its protection configuration.
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

For a small targeted change, stay in the current directory and pass explicit filesystem paths as
needed. When maintenance within this one root is substantial or has many steps, prefer changing the
current directory to the exact root before working. This makes omitted paths and relative native
tool arguments select the intended tree while avoiding repeated root arguments. Continue to use
explicit paths when coordinating multiple roots or when the current directory would be ambiguous.

## Index Content and Filter Choices

Treat each `index.md` as a concise retrieval map, not merely a list of filenames and not a copy of
the indexed documents. By default:

- briefly identify the knowledge covered by its directory and provide enough distinguishing
  context, relationships, and links for an agent or human to search effectively and choose what to
  read next;
- give every included direct child a recognizable entry. Recursively cover descendants that do
  not have their own index; when a child has an index, keep the parent entry compact and delegate
  detailed navigation to that child;
- organize related entries into useful layers when the scope is large. Keep summaries and labels
  precise, avoid repeating child-index or document content, and retain enough context for
  progressive reading after removing repetition;
- use Markdown links to provide usable entry points. Do not impose a fixed section or list format
  when another concise structure retrieves the content equally well.

Use filter attributes only when their real semantics fit and retrieval remains effective:

- use `atomic_entries` for a cohesive directory that should be indexed as one unit. Keep a useful
  parent entry and selective internal pointers when they materially improve retrieval; do not put
  `index.md` or `log.md` inside an atomic directory;
- use `protected` for content that remains part of the tree and should remain discoverable but is
  outside the current tree's maintenance authority. Protection does not excuse weak indexing;
- do not add, remove, or broaden an `excludes` condition without explicit user authorization or a
  user instruction that makes the content outside this doctidex tree. Protocol-required exclusions
  are handled by the standard workflow and do not require a separate user decision.

Never use atomic, protected, or excluded solely to suppress a semantic candidate, reduce indexing
work, or make validation appear clear.

## Execute One Maintenance Plan

1. Establish the plan before writing. For a direct single-root task, formulate the one plan here.
   When arriving from Workspace, use the corresponding per-scope plan. Confirm its objective,
   intended targets, selected root, known base commit, authority, dependencies, validation, and
   delivery intent. If the work requires another root or no single write boundary is yet clear,
   load `$doctidex-git-workspace` and coordinate the plans first.
2. Select the plan's exact root and record existing Git changes. Confirm that every intended write
   target is under this root; paths used only to read a mount snapshot are not write targets.
3. Inspect each intended write target before editing. If `source: mount`, stop before writing and
   return to Workspace planning. If `host_scope: excluded`, do not maintain it in this plan. If
   `protected` is present, require explicit user direction and record that decision in the plan.
4. Read the responsible index, target content, and applicable log when history matters. Expand
   native search when those files are insufficient. Reading may cross boundaries; writing may not.
5. Edit content using native tools. Author all prose, summaries, index entries, and log entries
   using your own judgment. Keep changes within the plan's objective and selected root.
6. Update the responsible index only when the real content change requires it. Apply the index and
   filter defaults above, and preserve sufficient existing prose instead of mechanically adding
   every semantic candidate.
7. If an applicable log exists, record only changes important to that log's scope; do not create a
   log solely because the CLI found a Git change.
8. When new work is discovered, decide whether it is another target in this same root and objective
   or a change to the coordinated scope plan. Update this plan for the former. For a mount target,
   another root, an unmet cross-scope dependency, or an unclear boundary, preserve current changes
   and return to Workspace to rerun scope and revise the affected plans before writing that target.
9. Run check and changes on the exact root, inspect the actual Git diff, and compare the result with
   the maintenance plan. Record completed targets, index/log decisions, validation, preserved
   pre-existing changes, and unresolved delivery actions for Workspace or user handoff. Mark the
   plan result as completed with changes, completed with no content changes, or blocked with the
   current result preserved; these are agent planning descriptions rather than CLI statuses.

When Workspace planning places a same-commit self-reference in the current-root plan, use the
translated writable targets recorded by that plan and keep all compatible changes in this scope.
Continue reading through the mount path when evidence must reflect the mount snapshot; only the
write location is consolidated, and the mount path remains read-only.

## Interpret Results

- `path_context.attributes` is a set; atomic/protected may coexist.
- `semantic_candidates` require reading. `index_reference_candidate` means no exact machine-parsed
  link was found, not that prose is missing.
- `git_change_review` means consider index/log follow-up, not that both files must change.
- `protocol_structure: fail` is a deterministic structure problem.
- `plugin_readiness: blocked` concerns Git mount prerequisites and is not automatically a protocol
  failure.

Report the plan's completed and unresolved targets, changed files, responsible index/log decisions,
validation facts, pre-existing changes kept, and unresolved user actions. Do not commit, push,
reset, clean, switch the user's branch, or discard unrelated work.
