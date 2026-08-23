# `import`

`import` manages fixed-revision Installations and managed Refs.

See [common.md](common.md) for shared interface and errors.

## Install

```bash
doctidex-git import install \
  (--tracked | --untracked) \
  --url <GIT-URL> \
  (--branch <BRANCH> | --tag <TAG> | --commit <HASH>) \
  [--key <QUERY-KEY>]...
```

`--tracked` or `--untracked` is required. Exactly one revision selector is required.

Branch and tag selectors resolve once. Re-running the same branch/tag with an unchanged remote commit reuses the Installation; a changed commit replaces it.

Success:

```json
{
  "status": "ok",
  "message": {},
  "install-id": "<INSTALL-ID>",
  "install-path": "/.doctidex-git/imports/<DOMAIN>/<REPOSITORY>/<SELECTOR>"
}
```

## Restore and track

```bash
doctidex-git import restore --install-id <INSTALL-ID>
doctidex-git import track --install-id <INSTALL-ID>
```

`restore` accepts only tracked Installations and uses the recorded `commit-hash`; it does not re-resolve a branch or tag. `track` promotes an untracked Installation to tracked.

## Ref management

```bash
doctidex-git import ref \
  --install-id <INSTALL-ID> \
  [--src-sub-dir <INSTALL-REPOSITORY-PATH>] \
  --target-dir <REPOSITORY-PATH>

doctidex-git import unref --target-dir <REPOSITORY-PATH>
```

`ref` creates a relative symlink and derives an `import-ref` boundary. Creating a Ref promotes its Installation to tracked. `unref` is a no-op when no Ref exists and is blocked while a Markdown link crosses the Ref boundary.

## Query

```bash
doctidex-git import query \
  (--install-id <INSTALL-ID> | --install-path <REPOSITORY-PATH> | \
   --ref-path <REPOSITORY-PATH> | --key <QUERY-KEY>...)
```

Exactly one selector class is required. `--key` is repeatable fuzzy search.

```json
{
  "status": "ok",
  "message": {},
  "candidates": [
    {
      "git-url": "<GIT-URL>",
      "commit-hash": "<HASH>",
      "install-id": "<INSTALL-ID>",
      "install-path": "/<INSTALL-PATH>",
      "keys": ["<QUERY-KEY>"],
      "branch": "<BRANCH-OR-EMPTY>",
      "tag": "<TAG-OR-EMPTY>",
      "refs": [
        {"src-sub-dir": "/<INSTALL-SUB-DIR-OR-EMPTY>", "target-dir": "/<REPOSITORY-PATH>"}
      ]
    }
  ]
}
```

## Remove

```bash
doctidex-git import remove \
  (--install-id <INSTALL-ID> | --untracked | --auto)
```

`--install-id` selects one Installation. `--untracked` selects all untracked Installations. `--auto` selects untracked Installations and Installations without managed Refs.

Removal is blocked when a tracked Installation still has a Ref or an in-scope Markdown link crosses its boundary.

## Handleable errors

| Code | Cause and next step |
|---|---|
| `revision.unresolvable` | Selector cannot resolve to a commit. |
| `cache.repository.unavailable` | Bare repository cannot be obtained. |
| `installation.target.unavailable` | Install path is occupied or unusable. |
| `installation.not-found` | Requested Installation does not exist. |
| `installation.tracking-state.invalid` | `restore` received an untracked Installation. |
| `installation.restore.unavailable` | Tracked Installation cannot be restored at its commit. |
| `installation.remove.blocked` | Ref or cross-boundary link still depends on the Installation. |
| `ref.source.unavailable` | Installation or `src-sub-dir` cannot be a link source. |
| `ref.target.unavailable` | Target is occupied or cannot be created. |
| `ref.target.inconsistent` | Physical symlink does not match the Ref record. |
| `ref.remove.blocked` | Markdown link still crosses the Ref boundary. |

## Installation context

Inside a managed Installation, `import query` and `import restore` are allowed. `import restore` reads the local Installation and installs it into the owner work model as an untracked Installation. `import install`, `import track`, `import ref`, and `import unref` are forbidden.
