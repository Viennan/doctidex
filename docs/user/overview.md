# doctidex-git v2 User Guide

`doctidex-git` organizes Git repositories into an interconnected knowledge network. A repository remains ordinary source
and history while also becoming a navigable knowledge base that can reference fixed external Git revisions and can itself
be referenced by other repositories.

The tool manages:

- fixed-revision external repositories as Installations;
- managed symbolic Refs into Installations;
- editable Worktrees;
- custom boundary points;
- validation and repair.

The command architecture is defined by [overview.md](../dev/architecture/overview.md).

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

## Repository layout at a glance

The following directory tree shows one repository with an Installation, a Ref, an editable Worktree, and a custom
boundary. It is a usage illustration, not a required directory-tree standard.

```text
/path/to/repository                       # Git root; /... paths start here
├── README.md
├── docs/
│   └── guide.md
├── .doctidex-git/                        # Workspace
│   ├── config.toml
│   ├── boundary-set.json                 # custom BoundaryPoints
│   ├── imports.json                      # tracked Installations
│   ├── import-refs.json                  # Refs
│   ├── runtime.json                      # untracked Installations, Worktrees, shares
│   ├── imports/
│   │   └── github.com/
│   │       └── example/
│   │           └── <commit>/             # read-only Installation
│   └── worktrees/
│       └── github.com/
│           └── example/
│               └── <name>/               # editable Worktree
├── external/
│   └── example -> Installation           # Ref; /external/example is an import-ref BoundaryPoint
├── vendor/
│   └── third-party/                      # custom BoundaryPoint
└── links.md
```

The diagram maps to the retained concepts:

- `.doctidex-git/` is the managed Workspace.
- `.doctidex-git/imports/...` holds read-only Installations.
- `.doctidex-git/worktrees/...` is the default location for editable Worktrees; `worktree create --work-path` can place one elsewhere.
- An Installation can contain its own `.doctidex-git/`, which is the source of recursive sub-Installations.
- `external/example` is a Ref; its target path is a derived `import-ref` BoundaryPoint.
- `vendor/third-party` can be declared as a custom BoundaryPoint in `boundary-set.json`.
- A Markdown link that crosses one of those boundaries uses a StructuredLinkAnnotation:

```markdown
[External](/external/example/readme.md)
<!-- doctidex: {cross-boundary-point: /external/example} -->
```

`index.md` is not required in this layout.

## Mental model

| Concept | User-visible meaning |
|---|---|
| Git root | The boundary for one command and the root of repository-internal `/...` paths. |
| Workspace | `.doctidex-git/` under the Git root. |
| Installation | One external Git URL fixed at one commit and installed at one read-only path. |
| Ref | A managed symbolic link into an Installation. |
| Worktree | An editable Git worktree whose base commit is recorded; it may branch, modify, and commit freely. |
| BoundaryPoint | A path where the current repository's link and scan rules stop. |
| StructuredLinkAnnotation | A `doctidex` comment that records the first BoundaryPoint crossed by a Markdown link. |

`index.md` has no special role. `init` creates only the `.doctidex-git` workspace and its state files; it does not create
or modify `index.md`.

## Installation context

Use `--installation-context <INSTALL-ID>` to operate on a recorded Installation. In that context, `validate`,
`boundary-set parse`, `import query`, and `import restore` are allowed. Commands that mutate the owner work model,
create Worktrees, or initialize a workspace are forbidden. Running from inside a managed Installation without
`--installation-context` is blocked and asks for the argument. `import restore` does not install inside the current
Installation; it flattens the local Installation into the owner repository.

See [common.md](reference/common.md#installation-context) for the complete behavior.

## Core behaviors at a glance

| Area | Essential behavior | Detail |
|---|---|---|
| Workspace bootstrap | Run `init` once, then `validate --model-structure`. | `init` creates `.doctidex-git/` and its state projections. |
| Installations and Refs | Install a fixed revision, then expose it with a Ref. | Use `import install`, `import ref`, `import restore`, `import query`, and `import remove`. |
| Worktrees | Create an editable worktree from an Installation or URL. | Use `worktree create`, `worktree query`, and `worktree remove`. |
| Custom boundaries | Add or remove custom escape paths. | Use `boundary-set add`, `boundary-set remove`, and `boundary-set parse`. |
| Validation and repair | Observe problems without changes, then repair recoverable physical state. | Use `validate` first; use `repair` to align model and physical objects. |
| Result contract | Every command emits machine-readable JSON. | Success uses `status: "ok"`; `validate` adds `valid`; failures use stable `message.code`. |
| Cache | The CLI caches bare repositories under the doctidex-git home. | Configure with `DOCTIDEX-GIT-HOME` and `config.toml`; see [common.md](reference/common.md#cache-configuration). |
| Installation context | Select an Installation with `--installation-context`; the allowed command set is restricted. | Only `validate`, `boundary-set parse`, `import query`, and `import restore` are allowed; `import restore` flattens the local Installation into the owner repository. |

## Command documents

| Task | Document |
|---|---|
| Common interface and recovery | [common.md](reference/common.md) |
| Initialize the work model | [init.md](reference/init.md) |
| Manage custom boundaries | [boundary-set.md](reference/boundary-set.md) |
| Manage Installations and Refs | [import.md](reference/import.md) |
| Manage Worktrees | [worktree.md](reference/worktree.md) |
| Validate the model and links | [validate.md](reference/validate.md) |
| Align physical state with the model | [repair.md](reference/repair.md) |

## Usage boundaries

Do not edit state JSON under `.doctidex-git/` by hand. Do not commit managed Installation or Worktree directories.
Installation directories are read-only; create a Worktree when you need to modify or commit from a fixed revision. Use
`validate` to observe problems and `repair` to align recoverable physical state.

`doctidex-git` coordinates only `doctidex-git` processes that follow its lock and transaction protocol. It does not
guarantee race safety against direct external edits, and it never rewrites Git history or undoes commits. `repair` may
discard uncommitted Installation changes but never Worktree changes or commit history; see
[repair.md](reference/repair.md#what-repair-does-not-do).
