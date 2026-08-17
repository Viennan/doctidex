---
name: doctidex-git-overview
description: Establish the installed doctidex-git mental model, shared CLI grammar, root and path semantics, result handling, safety boundaries, and workflow routing. Use at the first doctidex-git task in a conversation, when product terms or output contracts are unfamiliar, or when choosing a reading, mention-resolution, or maintenance workflow; do not use it as a substitute for the selected specialist.
---

# Use doctidex-git

Current product metadata: `doctidex-git` Skill version `1.0.0`; doctidex protocol version `v1.1.0`.

Read this Skill once for a task, then load only the selected specialist. Do not reopen this Skill
when a specialist refers back to shared terms.

## Select a Python Runtime

The `doctidex-git` CLI requires a compatible Python environment with the `whero-doctidex` package
installed; use the `doctidex-git` command from that environment.

## Install the CLI from GitHub

```text
python -m pip install --no-input \
  "whero-doctidex @ git+https://github.com/Viennan/doctidex.git@v1.0.0#subdirectory=impls/libs/python"
```

## Choose the User Cache Location

The user may set the optional `DOCTIDEX_GIT_CACHE` environment variable to an absolute, writable
shared cache path before starting CLI, automation, or host Git processes. Recommend that the user
configure it and ensure every process that must share the cache inherits it. Do not write shell
profiles, project settings, or other persistent environment configuration for the user. If it is
unset, the current variant chooses its platform default. This setting does not route `cache clean`;
that command remains a human/program operator surface.

## Choose a Workflow

- Load `$doctidex-git-read` to navigate indexes and links, search content with native tools, diagnose
  an inaccessible symlink, or continue native reading after mention resolution.
- Load `$doctidex-git-mentions` to resolve a repository-path, optional host/revision, complete
  external-link, or partial external-link mention to managed candidates or diagnostics.
- Load `$doctidex-git-maintenance` to validate structure, install or restore external Git content,
  create/rebind/unlink a durable external presentation, or open/list/close an optional isolated worktree.
- When a task crosses that boundary, load the second specialist once and resume there. Do not form a
  reading loop between Skills.

The managed external and worktree workflows are optional product choices. Continue to use native
file, search, shell, editing, and Git tools whenever they suit the task. The CLI adds deterministic
doctidex/Git facts; it does not author prose, judge semantic quality, grant write authority, or
perform Git delivery.

When authorized to install a checkout hook, identify the current owner root and register it only in
that root's host Git repository:

```text
doctidex-git hook --install --root OWNER_ROOT --json
```

Never run `hook --install` from, or pass as `--root`, a Git repository installed beneath
`OWNER_ROOT`. Its content root and checkout are not a hook target for the owner root: installing a
hook for one owner root never recursively installs hooks in its managed repositories.

After `doctidex-git hook --install` has been installed for a root, its Git checkouts automatically
reconcile managed external dependency state. Do not repeat equivalent manual reconciliation after an
ordinary checkout. If Git reports a `post-checkout` hook failure or warning, inspect its result and
resolve any issue that is within the current authority. Then rerun reconciliation directly for the
exact affected owner root:

```text
doctidex-git hook --run --root ROOT --json
```

Read the new result before proceeding. If it remains blocked or requests a user decision, preserve
the reported state and stop. Do not create an otherwise unneeded `git checkout` merely to trigger
the hook again.

## Shared Terms

- A **doctidex root** is the exact directory whose `index.md` declares `doctidex.root: true`.
- A **root-absolute path** such as `/docs/api` is relative to that doctidex root, never the host
  filesystem root. Other CLI filesystem paths may be absolute or cwd-relative as their command
  contract states.
- A **revision selector** is exactly one full commit object ID, tag name, or branch name. A resolved
  or base commit is the immutable full commit used by an install or worktree. A returned default
  branch or explicit branch/tag is provenance, not a moving selector to re-resolve for an existing
  local install or for restore. A newly authorized `external install` uses its supplied selector to
  establish or update a snapshot; `external restore` instead recovers the current manifest's exact
  commit.
- A **direct install** has portable recovery information. A **dependency install** is attached to a
  parent install for the current owner root and is not independently recoverable until promoted by
  repeating the same install without `--dependency-of`.
- The **owner root** owns managed external and worktree paths. An installed repository can contain a
  different **content root**; never create nested managed state inside that read-only content root.

## Invoke the CLI

Use `doctidex-git ... --json` for agent decisions. Put `--json` once at the end. JSON results use
`schema_version: "1.0"`; unknown major schemas require a compatible product version rather than
guessing fields.

For commands with `--limit N`, `N` is 1 through 1000 and defaults to 100 for each top-level list.
Read `collection.lists`, `truncated`, and `next_cursor`. Pass an opaque cursor unchanged with the
same operation, root, normalized filters/scopes, limit, and mode. On `cursor_invalid`, restart from
the first page. Do not raise the limit merely to avoid pagination.

Commands that accept `--dry-run | --apply` default to dry-run. The options are mutually exclusive.
Review the plan and obtain any needed user authority before adding `--apply`. Dry-run may use the
network only where the specialist contract says so, but it does not write persistent product or
root state.

## Select Roots Deliberately

When a command accepts a root, pass the exact root whenever nested roots are possible. Omitting it
selects the unique containing root specified by that command; zero matches block with
`root_not_found`, and multiple matches block with `root_ambiguous`. A mismatched explicit root blocks
with `root_mismatch`; use the affected owner candidate rather than choosing the nearest root.

Managed install and worktree payloads are placed flat beneath the owner root's `/.doctidex` area.
They are ignored by the host Git repository. Portable recovery information and durable relative
symlinks remain trackable; the CLI does not stage, commit, push, merge, or run `git rm --cached`.

## Read Every Result Domain

Every JSON envelope contains `operation`, `status`, `result`, `root`, `changed`, `network`,
`findings`, `next_actions`, `affected`, `requires_user`, and `collection` in addition to the
operation fields. Empty and unavailable values use empty arrays or `null` rather than omitted keys
for the common envelope.

- `status: ok` means the operation completed normally.
- `status: warning` means it completed with preserved state or follow-up; inspect all independent
  fields instead of treating warning as failure.
- `status: blocked` means the requested operation did not complete. Read the stable finding `code`,
  affected object, preserved `result`, ordered `actions`, and `requires_user`.
- Exit 0 is ok or a completed warning without protocol failure; exit 1 is a completed validation
  with `protocol_structure: fail`; exit 2 is blocked or invalid syntax; exit 130 preserves effects
  completed before interruption.

Never expose credentials from input URLs. Stop for user decisions indicated by `requires_user`,
especially root selection, network/repository access, revision choice, target occupancy, parent
install choice, Git tracking, recovery information, or Git delivery. Retry an unexpected failure at
most once, then report its diagnostic ID and the preserved state.

Before changing a reviewed dry-run to `--apply`, require all of: the result is not blocked,
`requires_user` is null, no error Finding remains, the fixed commit/owner/planned paths still match
the intended task, and the user has granted the needed write/network authority. A warning is not an
automatic approval or rejection; read its Finding and preserved result before deciding.
