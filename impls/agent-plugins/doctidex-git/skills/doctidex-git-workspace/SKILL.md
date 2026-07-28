---
name: doctidex-git-workspace
description: Plan and coordinate multi-root doctidex workspace maintenance. Use when a task spans a host and mounted Git sources, spans multiple doctidex roots, changes a mounted source, or involves a root self-reference; divide the work into per-scope plans, reuse or isolate writable roots, and orchestrate sequential or multi-agent execution with independent validation and delivery results.
---

# Doctidex Git Workspace

If the common path, root, CLI, and output model is not already established, load
`$doctidex-git-guide` before continuing.

## Terms

- **Independent root**: a host or source root with its own base commit, write boundary, diff,
  validation, and Git delivery actions.
- **Base commit**: the commit from which a maintenance result started; it can be null before a mount
  is prepared.
- **Read-only path**: the host mount path used for reading the current effective commit.
- **Maintenance root**: the filesystem path returned by `maintenance open`; this is where source
  edits belong.
- **Target branch**: an informational branch name when the mount selector is a branch. It does not
  mean the maintenance root has switched to that branch.
- **Handoff**: a read-only summary of changes, validation, semantic candidates, and remaining Git
  decisions for one maintenance root.
- **Root relation**: `source: same_repository` confirms a mount points to the current checkout root;
  `revision` then says `same_commit`, `different_commit`, or `unknown`. An unknown source relation
  must not be guessed.
- **Maintenance reuse**: the CLI's bounded recommendation for a compatible existing write scope.
  The agent still checks write authority and delivery-target compatibility.
- **Scope item**: a host root or mounted source observed by the current `maintenance scope` call.
  It has no pending, assigned, or completed state and may already appear in the agent's plan.
- **Selected write scope**: the host root or maintenance root the agent chooses for one coherent
  result. All edits, index/log decisions, validation, diff review, and delivery actions for that
  result stay within this root.
- **Maintenance plan**: the agent-owned plan for one selected write scope. It states the intended
  changes, covered targets, write root and base commit, required authority, dependencies, validation,
  and expected Git delivery. The CLI neither stores this plan nor assigns items to it.
- **Compatible scope**: a candidate for the same non-null source commit that the user has
  authorized the agent to modify and that can be delivered as one coherent Git result to the
  intended branch or integration target. Equal source/commit is necessary but does not override
  authorization or conflicting delivery intent.

`maintenance scope` and `maintenance open` select their host root from the current working
directory. Run them from the exact host root; a `PATH` passed to `scope` classifies work but does
not select a different host. After `open`, pass the returned exact `MAINTENANCE_ROOT` to
`status`, `handoff`, and `close`; those explicit calls work from another current directory. When
the path is omitted, these commands again select the host from the current directory.

## Command Contract

| Command | Parameter behavior | Result or limit |
|---|---|---|
| `doctidex-git maintenance scope [PATH ...] --json` | PATH values are filesystem targets in the current host. Omit them to observe the host root. Rerun for a mount or other-root target, changed reuse facts, or an unclear boundary; an ordinary local addition clearly within the selected scope does not require it. | Deduplicates the host and each mount into current `items`; reports selector, source/base commit, target-branch hints, root relation, reuse guidance, and write action without opening a root or recording the agent's plan. |
| `doctidex-git maintenance open MOUNT_PATH --json` | Pass the exact declared mount path, not a file below it. Mount must already have an effective commit. Calling open explicitly requests an isolated root. | Returns one new `maintenance_root`, relation/reuse facts observed before open, boundaries, and next actions. Status is `warning` when a compatible scope already existed, but the new root is still ready. |
| `doctidex-git maintenance status [MAINTENANCE_ROOT] --json` | Omit the path to list all open contexts for the current host; pass an exact returned path to select its owning host and filter one. | Each item includes `maintenance_root`, `source`, `base_commit`, nullable `target_branch`, state, and bounded Git-status entries. No match returns an empty list, not an error; `changes` are not a diff. |
| `doctidex-git maintenance handoff [MAINTENANCE_ROOT] --json` | Pass the exact returned path from any cwd. Omit only from its host when exactly one context is open. | Returns one root's changes and three validation domains; does not commit or push. |
| `doctidex-git maintenance close [MAINTENANCE_ROOT] --json` | Use the same exact-selection rule as handoff. No dry-run flag. | Removes only a Git-clean context; any change blocks close and preserves the root. |

If scope reports `maintenance_reuse.reason: source_not_prepared`, or open reports
`maintenance_source_not_prepared`, load `$doctidex-git-mount`, run
`doctidex-git mount prepare MOUNT_PATH --json` with the item's exact `mount_path`, then rerun scope.
Open itself does not fetch or synchronize.

## Coordinated Maintenance Workflow

The agent owns the overall maintenance plan. Build it as a set of per-scope maintenance plans, then
coordinate their order and dependencies. `maintenance scope` supplies current facts for this work;
it does not create, save, or replace any plan.

### 1. Observe the Known Targets

Run scope for all task paths currently known. A `host_root` item is directly writable; a
`mounted_source` item's `read_only_path` is never writable. Treat each item as an observation that
may already be covered by a plan. Rerunning scope refreshes the facts; it does not create duplicate
work or reset planning decisions.

### 2. Build or Revise the Per-Scope Plans

Group items that may share one selected write scope before opening anything. The same non-null
`source` and `base_commit` identify mounts from the same declared source revision, but merge them
only when write authority and the intended Git delivery are also compatible. Commit equality alone
does not prove source identity; `root_relation.source: unknown` must not be guessed, and different
effective commits remain separate scopes.

For each selected write scope, make one maintenance plan that records at least:

- the objective and covered task targets, including each mounted target's source-relative path;
- the selected write root and base commit, or the exact action needed to obtain that root;
- applicable write authorization, protected-content decisions, and intended branch or integration
  target;
- dependencies on other scope plans and the planned execution order;
- expected index/log decisions, validation, diff review, handoff, and Git delivery actions.

Use the CLI facts to choose each plan's write root:

- `recommended`: compare the scope item's `target_branch` with
  `maintenance_reuse.target_branch`, then use the exact `write_path`. When both branches are known,
  the CLI recommends the root only if they match. A `host_root` recommendation means a compatible
  same-commit self-reference belongs in the current-root maintenance plan. If either branch is
  null, use the task's delivery intent and ask the user or isolate when compatibility cannot be
  established;
- `selection_required`: run `doctidex-git maintenance status --json`, filter its items to the scope
  item's exact `source` and non-null `base_commit`, and compare each `target_branch` hint with the
  intended delivery. Select one authorized root; if multiple roots remain equally valid and the
  task provides no preference, ask the user;
- `not_available`: follow `reason`. Prepare `source_not_prepared`, keep
  `current_root_different_commit` in a separate plan, and treat `delivery_target_conflict` as a
  separate result unless the user explicitly chooses a common integration target. With that
  explicit choice, rediscover the candidate rather than treating the conflict as an automatic
  write permission: for a same-repository/same-commit self-reference, scope `.` and consider its
  host `write_path`; for an existing mounted-source root, run maintenance status and filter by the
  exact `source` and `base_commit`. Choose an authorized root that fits the common delivery result,
  and ask the user if more than one remains. Otherwise, plan to open one representative mount only
  when no compatible write root exists.

Build the dependency graph from actual content and delivery relationships. The CLI does not choose
an execution strategy. Independent plans may run concurrently; plans whose inputs or delivery
decisions depend on other results must wait for those prerequisites.

### 3. Prepare the Planned Write Roots

Reuse every compatible root selected by the plans. Run `maintenance open` only for a plan that has
no compatible root or intentionally requires isolation. Bind the returned exact
`maintenance_root` to that plan. If open returns `warning`, review the plan because an earlier scope
was compatible; keep the new root only when isolation is intentional, otherwise leave it clean and
close it.

### 4. Execute Scope Plans Within Their Boundaries

Use the agent runtime's own orchestration model. Execute plans sequentially when that is simpler, or
delegate independent plans to subagents or other workers and run them concurrently. For every
delegated plan or work package, provide the objective, covered targets, selected write root, base
commit, authority, dependencies, known pre-existing changes, intended delivery, expected index/log
decisions, package-level checks, and final scope validation and handoff expectations. The
coordinating agent remains responsible for reconciling plan outcomes and dependent work.

Parallelism does not merge write boundaries. Each worker stays within its assigned selected root
and returns a bounded result. One selected write scope still has one maintenance plan. When multiple
workers intentionally use the same selected root, give them coordinated, non-conflicting work
packages inside that plan; define file ownership and integration order so edits do not overwrite
each other or obscure which package produced a change. The coordinating agent combines their
results into the single scope result. Never let a worker infer permission to cross a mount, perform
an unplanned Git delivery action, or discard another worker's result.

Use whatever coordination mechanisms the agent runtime provides. If they cannot reliably prevent
conflicting same-root edits, serialize only those conflicting packages; unrelated scopes may still
run concurrently.

Each worker result should identify its covered and unresolved targets, changed files, index/log
decisions, package-level check facts, preserved pre-existing changes, new boundary discoveries, and
remaining delivery actions. A worker delegated an entire scope may return the final scope result.
A worker handling only one package returns an intermediate package result; after all packages for
that root are integrated, the coordinating agent or a delegated finalizer runs the root-level
check/handoff and diff review once to produce the scope result. These are agent coordination
results, not CLI schemas.

Before editing a mounted target, translate it into the plan's selected write root. Remove the exact
`read_only_path` prefix from the target and append the remaining source-relative suffix to the
selected `write_path` or maintenance root. For example,
`/host/.doctidex/mounts/api/guides/a.md` under read-only root
`/host/.doctidex/mounts/api` becomes `<selected-write-root>/guides/a.md`. Confirm that the result
stays below the selected root. If it does not, rerun scope for the exact target instead of guessing.

Start from the selected root's own `index.md`; never modify the host `read_only_path`. Load
`$doctidex-git-maintain` and `$doctidex-git-validate` as needed for that plan. For substantial,
multi-step work in one scope, `cd` to its selected root so native tools and commands with optional
paths naturally use the intended tree. Keep using explicit roots while coordinating several plans.

If execution discovers an ordinary local target that is clearly within the same selected root,
authority, objective, and work-package ownership, inspect it and add it to the current package and
plan without rerunning scope; report that addition. If it overlaps another package or changes
dependencies, let the coordinating agent revise ownership before writing.

If the target is reached through a mount, belongs to another or uncertain root, a relevant reusable
root has changed, or the write boundary is unclear, stop before writing that target and rerun scope
with the relevant paths. Unrelated work whose ownership and dependencies remain valid may continue.
Decide whether the observation updates an existing plan or requires another scope plan, then revise
dependencies and order as needed. A target reached through a mount is never silently added to the
current write boundary, even when later scope facts allow it to share the same plan.

A delegated worker may collect the new scope facts, but it must return the discovery to the
coordinating agent before affected work resumes. The coordinating agent may explicitly delegate
authority to revise named plans and dependency decisions to a planning worker; that worker must
return the revised coordination view before affected workers continue.

### 5. Verify and Deliver Per Scope

Complete each maintenance plan as its own result. For an independent maintenance root, run handoff
with its exact path; for a reused host root, run check and changes there. Inspect the native Git diff
in either case. Record that scope's base commit, changes, index/log decisions, validation, target
branch hint, and required commit, push, merge, or selector action.

Coordinate dependent plans only through their explicit results; one scope's successful validation
does not validate another. Close an independent maintenance root only after its Git status is clean
or the user has explicitly disposed of its result. Never close the current host root.

Keep the coordination view current by recording each plan as in progress, completed with changes,
completed with no content changes, blocked with its result preserved, or no longer required by the
task. These are agent planning descriptions, not CLI statuses. Do not treat a no-change plan as a
failure, and do not erase a completed result because another plan is blocked.

When plan outcomes are mixed, report the overall workflow as a partial result: list every plan's
outcome, preserved work, unresolved action, and effect on dependent plans. Do not invent an overall
CLI `status` for the agent-owned coordination plan.

## Failures and Partial Results

A multi-root task is not atomic. Preserve and report successful roots when another root fails.
`maintenance_has_changes` is a preservation result, not a cleanup error: keep the path open and ask
the user how to deliver or dispose of changes. Obtain explicit authorization before commit, push,
merge, selector update, reset, or deletion.
