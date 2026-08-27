# `validate`

`validate` read-only checks the work model, Markdown links, and managed Worktrees.

See [common.md](common.md) for shared interface and errors.

## Usage

```bash
doctidex-git validate \
  [--subdir <REPOSITORY-PATH> | --model-structure]
```

`--subdir` and `--model-structure` are mutually exclusive.

## Result

Diagnostics are not execution failures. `validate` returns `status: "ok"` with `valid: false` when diagnostics exist.

```json
{
  "status": "ok",
  "message": {},
  "valid": false,
  "scope": {"repos-path": "/work/repository", "subdir": "/"},
  "diagnostics": [
    {
      "rule": "link.annotation.required",
      "path": "/docs/guide.md",
      "line": 12,
      "message": "A cross-boundary link requires a matching doctidex annotation.",
      "details": {
        "link-path": "/external/example/index.md",
        "expected-cross-boundary-point": "/external/example"
      }
    }
  ]
}
```

## Common diagnostics

| Rule | Meaning |
|---|---|
| `work-model.valid` | Workspace, projections, relationships, managed paths, or ignore rules are invalid. |
| `link.path.conforms` | Local link cannot normalize to a repository-internal path. |
| `link.target.exists` | Local link target does not exist. |
| `link.annotation.required` | Cross-boundary link lacks a matching annotation. |
| `import.link.tracked` | Link crosses an untracked Installation. |
| `worktree.clean` | Managed Worktree has uncommitted changes. |
| `installation.worktree.dirty` | An Installation has uncommitted changes; reported inside `work-model.valid`. |

When a tracked Installation's physical directory is absent, validation does not restore it or require its link targets. This is expected after cloning tracked metadata.

## Cross-boundary annotation

```markdown
[External](/external/example/index.md)
<!-- doctidex: {cross-boundary-point: /external/example} -->
```

## Handleable errors

| Code | Cause and next step |
|---|---|
| `validation.scope.unavailable` | `--subdir` is unreadable, workspace-internal, or crosses a boundary. |
| `validation.scan.unavailable` | Validation scope cannot be traversed or read. |

`validate` never repairs state. Use [`repair`](repair.md) to align recoverable physical objects.

## Installation context

`validate` is allowed when the selected Git root is inside a managed Installation.
