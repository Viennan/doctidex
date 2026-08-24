# doctidex-git v2 User Guide

`doctidex-git` applies the doctidex directory-tree convention to a Git repository. A repository remains ordinary source and history while also becoming a navigable knowledge-base tree.

The tool manages:

- fixed-revision external repositories as Installations;
- managed symbolic Refs into Installations;
- editable Worktrees;
- custom boundary points;
- validation and repair.

The directory-tree model is defined by [directory-tree-spec.md](../dev/architecture/directory-tree-spec.md). The command architecture is defined by [overview.md](../dev/architecture/overview.md).

## Prerequisites

- Linux or macOS.
- A Git worktree.
- `doctidex-git` on `PATH`.

## Quick start

```bash
cd /path/to/repository
doctidex-git init
doctidex-git validate --model-structure
```

Then install a fixed external revision and expose it with a Ref:

```bash
doctidex-git import install \
  --tracked \
  --url git@github.com:example/project.git \
  --branch main \
  --key example

doctidex-git import ref \
  --install-id <INSTALL-ID> \
  --target-dir /external/example

doctidex-git validate
```

## Mental model

| Concept | User-visible meaning |
|---|---|
| Git root | The boundary for one command and the root of repository-internal `/...` paths. |
| Workspace | `.doctidex-git/` under the Git root. |
| Installation | One external Git URL fixed at one commit and installed at one read-only path. |
| Ref | A managed symbolic link into an Installation. |
| Worktree | An editable Git worktree whose base commit is recorded; it may branch, modify, and commit freely. |
| BoundaryPoint | A path where the current doctidex tree's rules stop. |

## Installation context

Running `doctidex-git` from inside a managed Installation changes which commands are allowed. Use `validate`, `boundary-set parse`, `import query`, and `import restore` there. Commands that mutate the owner work model, create Worktrees, or initialize a workspace are forbidden. `import restore` does not install inside the current Installation; it flattens the local Installation into the owner repository.

See [common.md](reference/common.md#installation-context) for the complete behavior.

## Core behaviors at a glance

| Area | Essential behavior | Detail |
|---|---|---|
| Workspace bootstrap | Run `init` once, then `validate --model-structure`. | `init` creates `.doctidex-git/` and the root `index.md` identity. |
| Installations and Refs | Install a fixed revision, then expose it with a Ref. | Use `import install`, `import ref`, `import restore`, `import query`, and `import remove`. |
| Worktrees | Create an editable worktree from an Installation or URL. | Use `worktree create`, `worktree query`, and `worktree remove`. |
| Custom boundaries | Add or remove custom escape paths. | Use `boundary-set add`, `boundary-set remove`, and `boundary-set parse`. |
| Validation and repair | Observe problems without changes, then repair recoverable physical state. | Use `validate` first; use `repair` to align model and physical objects. |
| Result contract | Every command emits machine-readable JSON. | Success uses `status: "ok"`; `validate` adds `valid`; failures use stable `message.code`. |
| Cache | The CLI caches bare repositories under the doctidex-git home. | Configure with `DOCTIDEX-GIT-HOME` and `config.toml`; see [common.md](reference/common.md#cache-configuration). |
| Installation context | Commands inside an Installation are restricted. | Only `validate`, `boundary-set parse`, `import query`, and `import restore` are allowed; `import restore` flattens the local Installation into the owner repository. |

## Command documents

| Task | Document |
|---|---|
| Common interface and recovery | [common.md](reference/common.md) |
| Initialize the work model | [init.md](reference/init.md) |
| Manage custom boundaries | [boundary-set.md](reference/boundary-set.md) |
| Manage Installations and Refs | [import.md](reference/import.md) |
| Manage Worktrees | [worktree.md](reference/worktree.md) |
| Validate the model and tree | [validate.md](reference/validate.md) |
| Align physical state with the model | [repair.md](reference/repair.md) |

## Usage boundaries

Do not edit state JSON under `.doctidex-git/` by hand. Do not commit managed Installation or Worktree directories. Installation directories are read-only; create a Worktree when you need to modify or commit from a fixed revision. Use `validate` to observe problems and `repair` to align recoverable physical state.

`doctidex-git` coordinates only `doctidex-git` processes that follow its lock and transaction protocol. It does not guarantee race safety against direct external edits, and it never rewrites Git history or undoes commits. `repair` may discard uncommitted Installation changes but never Worktree changes or commit history; see [repair.md](reference/repair.md#what-repair-does-not-do).
