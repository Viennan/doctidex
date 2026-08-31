# Issue Note: Clarify validate scope options and rename model-structure

Status: developing

## Problem

[`docs/user/validate.md`](../../../../user/validate.md) shows the `validate` command but does not explain what
`--subdir`, `--model-structure`, or the default invocation do. A user or agent cannot tell whether the default run
scans the whole Git root, whether `--subdir` narrows the Markdown scan or the whole command, or whether
`--model-structure` skips content checks.

The name `--model-structure` is also ambiguous: it reads like a subject (`the model structure`) rather than a mode
(`only the model structure`). The project is still in an unstable line, so this is the right time to correct the
surface before the option becomes a stable contract.

The Twin Skill's "Link across a boundary" guidance does not mention the scoped validation available with
`validate --subdir`, so agents run a full-tree validation even when only one document changed.

## Design

### Impact scope

The change affects the CLI surface, internal parameter names, tests, user documentation, architecture text, and the
Twin Skill:

- [`cli/main.py`](../../../../../src/python/whero/doctidex/cli/main.py)
- [`validate.py`](../../../../../src/python/whero/doctidex/validate.py)
- [`hooks.py`](../../../../../src/python/whero/doctidex/hooks.py)
- validate-related tests and documentation
- [`skills/doctidex-git/SKILL.md`](../../../../../skills/doctidex-git/SKILL.md)

### Command semantics

`validate` has three observable modes:

| Invocation | Behavior |
|---|---|
| `doctidex-git validate` | Full work-model check plus cross-boundary Markdown scan from the Git root. |
| `doctidex-git validate --subdir <PATH>` | Full work-model check; Markdown scan scoped to the requested repository-internal directory. |
| `doctidex-git validate --only-model-structure` | Work-model check only; no Markdown scan. |

`--subdir` remains a scan scope, not a work-model scope. `--only-model-structure` explicitly names the mode that
skips content scanning.

### Rename

The public flag is `--only-model-structure`. The old `--model-structure` spelling is removed, not aliased. Internal
names follow the same wording:

- argparse destination `only_model_structure`;
- `validate(..., only_model_structure=...)`;
- hook worker call sites use `only_model_structure=True`.

### Documentation and Twin Skill

`docs/user/validate.md` owns the mode table. Other user and architecture references use the new flag. The Twin Skill
updates its two bootstrap snippets and adds the optional scoped check after a cross-boundary link:

```bash
doctidex-git validate --subdir <REPOSITORY-PATH>
```

It also states that crossing any BoundaryPoint — `custom`, `import`, `import-ref`, or `worktree` — requires a
`doctidex` StructuredLinkAnnotation naming the first boundary crossed.

## Implementation plan

### Phase 1 — Rename the flag and internal names

Update the argparse definition, `_run_validate`, `validate()` signature, and hook call sites to
`--only-model-structure` / `only_model_structure`. Update error strings and all tests that invoke the old flag.

Checkpoint: `rg '--model-structure'` finds no remaining code/test reference; the default test suite passes.

### Phase 2 — Update documentation and Twin Skill

Rewrite `docs/user/validate.md` to explain the three modes. Update `overview.md`, `hook.md`, `init.md`, `common.md`,
and the architecture overview where the old flag is named. Update `skills/doctidex-git/SKILL.md` bootstrap snippets
and "Link across a boundary" scoped validation, then rebuild `_skill_data`.

Checkpoint: user-document link validator passes; skills tests pass; `_skill_data` is materialized.

### Phase 3 — Final quality pass

Re-read the changed text for one-home prose, run `ruff check` on changed Python files, run the default test suite,
and run `git diff --check`.

## Progress

Phase 1 is complete: the CLI flag, internal parameter, hook call site, error strings, and tests use
`--only-model-structure` / `only_model_structure`. `ruff check` passes and the default test suite passes
(222 passed, 7 deselected).

Phase 2 is complete: `validate.md` explains the three modes, user and architecture references use
`--only-model-structure`, the Twin Skill adds the optional `validate --subdir` check and uses the new flag,
`_skill_data` is rebuilt, the link validator passes, and the skills tests pass.

Phase 3 is complete. `ruff check` passes, the user-document link validator passes, the default test suite passes
(222 passed, 7 deselected), and `git diff --check` passes.

## Risks

Renaming the flag changes every existing unstable invocation and test. The change must update all references in the
same change to avoid a broken command surface.

`--subdir` must remain a scan scope. Users must know that work-model checks still run for the whole repository even
when only a subdirectory's links are scanned.

## Alternatives considered

**Keep `--model-structure` and only improve the prose.**
Rejected: the flag still does not say "only". The ambiguity is in the name itself, not only in the documentation.

**Use `--structure-only` or another short name.**
Rejected: `--only-model-structure` matches the existing vocabulary and makes the exclusion explicit without
inventing a new term.

**Keep the old flag as a deprecated alias.**
Rejected: the project is unstable, so retaining two names adds compatibility surface that the final contract should
not carry.

**Leave the Twin Skill unchanged and rely on the user guide.**
Rejected: the Twin Skill is the agent-facing operating contract; scoped validation belongs at the exact boundary-link
step where it reduces a full-tree scan.
