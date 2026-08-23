# Common Interface and Recovery

All command clusters share Git-root selection, repository paths, cache configuration, JSON output, and recovery boundaries.

## Git root and paths

Every command accepts:

```bash
doctidex-git [--repos-path <REPOSITORY-ROOT-PATH>] <command> [options]
```

When `--repos-path` is omitted, the CLI discovers the enclosing Git root. When provided, it must name the Git root exactly.

Repository-internal paths begin with `/` and are rooted at the Git root, not the host filesystem:

```text
/docs/guide.md
/.doctidex-git/imports/...
```

Path normalization may collapse `.` and `..`, but the result must not escape the repository.

## Cache configuration

The default doctidex-git home is `~/.doctidex-git`. `DOCTIDEX-GIT-HOME` selects another home. `config.toml` may set `cache-path`; otherwise the cache is `<home>/cache`.

The cache stores bare Git repositories. It is not the authority for Installations, Refs, or Worktrees.

## Installation context

When the selected Git root is inside a managed Installation, the CLI runs in Installation context rather than ordinary repository context.

Detection walks ancestor directories for a `.doctidex-git` directory. If exactly one owner is found, the current path belongs to that owner's Installation. If multiple owners are found, the command fails with `installation.owner.ambiguous`.

### Allowed commands

The following commands are allowed in Installation context:

- `validate`
- `boundary-set parse`
- `import query`
- `import restore`

`import restore` has special Installation-local routing: it reads the requested Installation from the local work model and installs it into the owner work model as an untracked Installation. It never creates a nested Installation inside the current Installation; the local Installation is flattened into the owner repository. The returned Installation keeps its local identity and provides an owner-side `presentation-path`.

### Forbidden commands

The following commands are forbidden inside an Installation:

- `init`
- `worktree`
- `import install`
- `import track`
- `import ref`
- `import unref`
- `boundary-set add`
- `boundary-set remove`
- `repair`

Other commands are not yet available in Installation context.

### Context errors

| Code | Meaning |
|---|---|
| `installation.owner.ambiguous` | The path is nested in multiple Installation workspaces. |
| `installation.context.forbidden` | The requested command is prohibited inside an Installation. |
| `installation.context.unavailable` | The command is not yet available inside an Installation, or local declarations cannot be read. |

## Success results and exit codes

Except for `validate`, a generic success result is:

```json
{"status": "ok", "message": {}}
```

Command-specific fields are documented by each command cluster.

| Result | `status` | Exit code |
|---|---|---:|
| Command completed | `ok` | 0 |
| `validate` found diagnostics | `ok`, `valid: false` | 1 |
| Argument, model, or workflow failure | `error` | 2 |

## Structured errors

Failures return a stable machine-readable envelope:

```json
{
  "status": "error",
  "message": {
    "code": "<STABLE-CODE>",
    "summary": "<HUMAN-READABLE-SUMMARY>",
    "context": {"command": "<COMMAND>", "repos-path": "<GIT-ROOT>"},
    "subject": {"kind": "<OBJECT-KIND>"},
    "details": {}
  }
}
```

Automation must rely on `message.code` and `message.details`, not `summary`.

Common errors:

| Code | Cause and next step |
|---|---|
| `argument.invalid` | Missing, conflicting, duplicate, or malformed arguments. |
| `git-root.unresolved` | The requested or discovered path is not a usable Git root. |
| `repository-path.invalid` | A repository-internal path is malformed or escapes the repository. |
| `work-model.uninitialized` | Run `init` first. |
| `work-model.invalid` | Run `validate --model-structure`. |
| `store.transaction.unavailable` | Store or residual transaction recovery failed; run `repair` or retry. |

## Recovery boundary

`validate` is read-only. `repair` aligns managed physical objects with JSON records but does not modify Markdown links or roll back Git history.

Normal commands detect residual RuntimeStore journals, run internal repair, and retry up to three times. For direct investigation:

```bash
doctidex-git validate --model-structure
doctidex-git repair
doctidex-git validate
```
