# Doctidex Git v2 Architecture

This document defines the current `doctidex-git` command architecture. It is authority for the work model, domain
services, link and boundary semantics, and implementation responsibilities. Transactional store design is defined by
[stores-transactions.md](stores-transactions.md).

## Purpose and scope

`doctidex-git` organizes one Git repository as a node in an interconnected multi-repository knowledge network while
preserving ordinary Git development. The repository remains an ordinary development workspace and knowledge base, and can
be used as an authoritative external knowledge source by other repositories. It manages fixed-revision installations,
symbolic refs, editable worktrees, custom boundaries, validation, and repair.

The product is a Linux/macOS CLI, not a hosted service or a replacement for Git. It owns only managed declarations and derived boundaries. Ordinary repository content and user-created worktrees remain outside its ownership.

## Bounded context

The Git-root is the boundary for every command. `--repos-path` selects the owner root when supplied; when omitted,
the CLI discovers it. `--installation-context <INSTALL-ID>` selects a recorded Installation by identity without
replacing Git-root selection. Repository-internal paths begin with `/` and are rooted at the selected Git root, not
the host filesystem.

The domain distinguishes:

- tracked declarations, which are reproducible across clones;
- runtime declarations, which describe machine-local physical objects;
- derived boundaries, which are computed from managed declarations.

## Installation-context behavior

Commands behave differently when the selected Git root is inside a managed Installation rather than an ordinary repository path.

### Context detection

`--installation-context <INSTALL-ID>` is the authoritative Installation selector. The CLI resolves the owner root
from `--repos-path` when supplied; otherwise it requires exactly one ancestor `.doctidex-git` owner candidate and
fails on zero or multiple candidates. It then opens the owner `RuntimeState`, finds the recorded Installation by
`install-id`, and constructs `InstallationContext` from the owner root and the recorded `install-path`.

When `--installation-context` is omitted, path detection is a defensive guard rather than a context resolver. The
CLI walks ancestors for a `.doctidex-git` owner. A selected root that matches a recorded `Worktree.work_path` is an
ordinary repository path. If one owner is found and no Worktree match exists, the path appears to be inside that
owner's Installation and the command fails with `installation.context.argument-required`. Multiple owner candidates
fail with `installation.owner.ambiguous`.

An `InstallationContext` records:

- `owner-root`: the owning repository root;
- `install-path`: the repository-internal path of the Installation selected by `install-id`.

### Command admission

| Command class | Installation-context behavior |
|---|---|
| `validate` | Allowed. |
| `boundary-set parse` | Allowed. |
| `import query` | Allowed. |
| `import restore` | Allowed with special Installation-local routing. |
| `init`, `worktree` | Forbidden. |
| `import install`, `import track`, `import ref`, `import unref` | Forbidden. |
| `boundary-set add`, `boundary-set remove`, `repair` | Forbidden. |
| Other commands | Not yet available. |

Forbidden and unavailable commands fail before state mutation. The failure identifies the owning Installation path.

### Model adaptation

An `InstallationRuntimeStore` coordinates two stores without merging their state:

- the owner RuntimeStore, which owns the outer repository work model;
- the Installation RuntimeStore, which owns declarations inside the selected Installation.

An `InstallationRuntimeModelView` exposes Installation-local records. It sets `presentation-path` to the owner-side Installation with the same `install-id` when one exists; otherwise the field is absent. The Installation and owner models remain separate.

`import restore` with `--installation-context` reads the requested Installation from the local model, then installs it into the owner work model as an untracked Installation. It never creates a nested Installation inside the current Installation; the local Installation is flattened into the owner repository's runtime projection. The result keeps the local Installation identity and supplies the owner-side `presentation-path`.

## Domain model

| Aggregate or value object | Meaning |
|---|---|
| **Installation** | One external Git source at one fixed commit and one read-only install path. |
| **Ref** | A managed symbolic link from a repository path into an Installation. |
| **Worktree** | A managed, untracked editable Git worktree. |
| **CustomBoundaryPoint** | A tracked boundary declared directly by `boundary-set add`. |
| **StructuredLinkAnnotation** | A `doctidex` HTML-comment YAML block attached to one Markdown link. |
| **CacheItem** | A cached bare repository identity and publication state. |
| **RuntimeState** | The merged tracked and runtime model view. |

### Installation

An Installation remains addressable by `install-id` even when its physical worktree is absent. A tracked Installation is stored in `imports.json`; an untracked Installation is stored in `runtime.json`. An Installation is read-only: validation reports uncommitted changes, and repair discards them to restore the recorded commit. `/.doctidex-git/imports/` is the managed Installation directory; its only allowed descendants are Installation directories created or restored by the import service.

Revision selectors are resolution inputs, not live tracking relationships. A branch or tag resolves once to `commit-hash`; a direct commit is reused by URL and commit.

Multiple Installations that resolve the same source to the same commit share one physical Git worktree through the [Installation share store](installation-shares.md).

### Ref

A Ref links a `target-dir` to the root or a `src-sub-dir` of one tracked Installation. Creating a Ref promotes its Installation to tracked. Removal is blocked while an in-scope Markdown link crosses its boundary. `target-dir` must not be inside `/.doctidex-git/imports/` or `/.doctidex-git/worktrees/`, and must not be below an existing BoundaryPoint.

### Worktree

A Worktree records origin and creation base but does not track later commits. It may branch, modify, and commit freely from its base commit, and it is not read-only. Default paths live under `/.doctidex-git/worktrees/`; a custom path receives tool-managed Git ignore rules. Removing a dirty recorded worktree requires `--force`. `worktree create --work-path` rejects paths inside `/.doctidex-git/imports/` and paths below an existing BoundaryPoint, including when the physical path is absent.

### Boundary points

The complete boundary view is derived from current state:

| Type | Source |
|---|---|
| `custom` | `boundary-set.json` |
| `import` | `Installation.install-path` |
| `import-ref` | `Ref.target-dir` |
| `worktree` | `Worktree.work-path` |

When paths overlap, resolution selects the first ancestor boundary from the Git root and does not continue below it.

### Link and annotation semantics

Markdown documents under the Git root follow these link rules:

- A path beginning with `/` is relative to the Git root.
- A path not beginning with `/` is relative to the source document's directory.
- Relative links are preferred when they express the same target.

A cross-boundary link must be followed by a `StructuredLinkAnnotation` that records the first crossed BoundaryPoint:

```markdown
[External](/external/example/guide.md)
<!-- doctidex: {cross-boundary-point: /external/example} -->
```

The annotation must be a full path-segment prefix of the link path and must resolve to the first crossed BoundaryPoint.
The Git root is the anchor for these paths; no `index.md` root-identity declaration is required.

## Domain services by command cluster

### Workspace bootstrap service

Commands: `init`

`init` establishes the `.doctidex-git` workspace, empty state projections, and Git ignore protection. A non-empty
workspace is already initialized; `validate --model-structure` or `repair` is the next step.

### Boundary management service

Commands: `boundary-set add`, `boundary-set remove`, `boundary-set parse`

This service manages custom BoundaryPoints. `remove` refuses a derived boundary. `parse` returns the first boundary for each requested path.

### Import service

Commands: `import install`, `import restore`, `import track`, `import remove`, `import ref`, `import unref`, `import query`

`install` resolves one revision, prepares the install path, and records a tracked or untracked Installation. `restore` recreates a tracked Installation at its recorded commit without re-resolving branch or tag. `track` moves an Installation into the tracked projection. `remove` deletes records and physical paths only when no Ref or in-scope link depends on them. `ref` and `unref` maintain managed symbolic links. `query` supports identity, path, ref, and fuzzy key selectors.

### Worktree service

Commands: `worktree create`, `worktree remove`, `worktree query`

`create` accepts an Installation or URL source, resolves a fixed commit, creates a detached Git worktree, and records it. Default paths use short random names until an unused path is found. `remove` deletes the managed directory and optional custom ignore rule; a dirty worktree requires `--force`. `query` returns the recorded Worktree.

### Validation service

Commands: `validate`

`validate` is read-only. It checks the work model first because an untrustworthy model cannot drive a complete Markdown
scan. Full validation covers state projections, physical Installations, Refs, Worktrees, ignore protection, local link
targets, cross-boundary annotations, and tracked-Installation requirements. It reports dirty Installations and dirty
Worktrees. It does not scan `.doctidex-git` or paths below a BoundaryPoint.

### Repair service

Commands: `repair`

`repair` aligns JSON records and managed physical objects. It recovers residual journals, restores missing or inconsistent Installations, Refs, and Worktrees, removes unrecorded links, and reconciles ignore rules. For a dirty Installation, it discards the dirty changes and restores the recorded commit; it does not discard Worktree changes. It is maintenance, not history rollback, and does not modify Markdown link content.

## Store and coordination services

The RuntimeStore owns tracked and runtime JSON projections. The CacheStore owns bare repository cache records. The StoreCoordinator coordinates retry and cache-before-RuntimeStore lock order; it performs repair outside a failed RuntimeStore transaction and retries the actual operation without serializing the whole command. Explicit repair is owned by the repair service. Commands needing both domains acquire cache access before RuntimeStore access.

The stores are not database transactions. Their objective is recoverable model state under cooperating `doctidex-git` processes, not reversal of every filesystem or Git side effect.

## Cross-cutting rules

- The CLI emits machine-readable JSON.
- `validate` returns `valid` plus diagnostics; operational failures use structured errors and exit status 2.
- Path normalization rejects repository escape.
- Markdown syntax recognition uses `markdown-it-py`; boundary and source-location logic supplements parser-recognized links.
- Git cache accelerates operations but does not replace RuntimeStore declarations.
- Coordination is scoped to cooperating `doctidex-git` processes. A command does not protect its state files, managed paths, or cache from external edits, and does not provide safety against non-`doctidex-git` concurrent actors.
- Python package is `whero.doctidex` under `src/python/whero/doctidex/`.

## Implementation responsibilities

| Responsibility | Implementation |
|---|---|
| CLI envelope and argument contract | [cli/main.py](../../../src/python/whero/doctidex/cli/main.py), [cli/results.py](../../../src/python/whero/doctidex/cli/results.py) |
| Domain records | [model.py](../../../src/python/whero/doctidex/model.py) |
| Shared model relations and link scans | [model_view.py](../../../src/python/whero/doctidex/model_view.py) |
| Installation-context resolution and owner routing | [installation.py](../../../src/python/whero/doctidex/installation.py) |
| Store protocol and journals | [store/](../../../src/python/whero/doctidex/store/) |
| Git source access and cache | [repository.py](../../../src/python/whero/doctidex/repository.py), [git_cache.py](../../../src/python/whero/doctidex/git_cache.py) |
| Command workflows | [boundary.py](../../../src/python/whero/doctidex/boundary.py), [imports.py](../../../src/python/whero/doctidex/imports.py), [worktree.py](../../../src/python/whero/doctidex/worktree.py), [initialization.py](../../../src/python/whero/doctidex/initialization.py), [validate.py](../../../src/python/whero/doctidex/validate.py), [repair.py](../../../src/python/whero/doctidex/repair.py) |
| Cross-store recovery | [coordination.py](../../../src/python/whero/doctidex/coordination.py) |

Model views own shared relationship semantics. Command modules own policy, such as whether a relationship blocks deletion, creates a diagnostic, or triggers physical repair.
