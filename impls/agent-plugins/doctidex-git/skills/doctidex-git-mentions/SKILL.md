---
name: doctidex-git-mentions
description: Resolve repository-path and external-link mentions to current doctidex managed installs. Use when a user or agent refers to a repository by source path such as `Viennan/wiki`, optional host/revision, or a complete or partial external-link path, and needs candidate facts before reading or maintenance; do not use to discover ordinary Git repositories or execute lifecycle changes.
---

# Resolve doctidex Git Mentions

If `$doctidex-git-overview` has not already been read for this task, read it once and return here.
This Skill is the dedicated, read-only interaction boundary for mentions. It returns candidates or
diagnostics; it never installs, restores, removes, links, edits, creates aliases, or grants authority.

Read [mentions.md](references/mentions.md) before invoking `external list` or `external link-parse`.

## Establish the Scope

Use the owner root selected for the task. A repository path, source URL, presentation path, or opaque
install ID cannot identify an install across roots. Treat a user phrase as context, not CLI syntax: do
not infer an exact target from a recent install, current directory, partial URL, or remembered ID.

This Skill applies only to current doctidex managed external records. Use native filesystem/Git tools for
ordinary repositories, worktrees, submodules, and unmanaged clones.

## Resolve a Repository Mention

For a source repository path such as `Viennan/wiki`, use `external list` with the selected owner root.
Add `--host`, tag, branch, full commit, or role filters only when the user/context supplies those facts.
The command returns direct, dependency, and hidden managed candidates without reading a remote or payload.

Compare the normalized query and each candidate's source host/path, selector, fixed commit, role, state,
and presentation paths. Same paths from different hosts or fixed revisions remain distinct. Report an
empty or multi-item collection and request clarification. Only a unique or user-confirmed candidate may
provide its opaque ID to the caller's later exact command.

`external list` does not prove that a recorded presentation path is currently readable. When native
reading must start from a repository candidate, use only one existing presentation path returned by that
candidate and treat it as an exact external-link mention below. Do not infer a payload path. If there is
no relevant presentation path, or several paths leave the intended link unclear, report that limitation
or ask the user before proceeding.

## Resolve an External-Link Mention

For a complete existing presentation path, symlink itself, or directory inside one, use native reading
first. Run `external link-parse` only when mapping, source, revision, install, or target-state facts are
needed. Read its managed identity and target state before handing the result back; an unmanaged path or
unexpanded portable dependency is not a current managed install.

For a partial spelling, inspect only task-relevant files and link targets, nearby responsible `index.md`,
prior conversation, and presentation paths already returned by `external list`. Establish one existing
path before parsing. Report none, several, or conflicting candidates; do not scan unrelated directories,
guess a suffix, or create a mapping/install.

## Hand Off the Result

Return an originally readable path or `working_path` from a successful parse to `$doctidex-git-read` for
native reading. Return a confirmed managed install ID, a missing owner install, or an optional portable
dependency to `$doctidex-git-maintenance` only when the task calls for its workflow. Preserve
blocked/warning evidence and obtain any required user decision before a later write or network action.
