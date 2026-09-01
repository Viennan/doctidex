# Issue Note: Prevent `import install --untracked` from downgrading a tracked Installation

Status: implemented

## Problem

[`imports.py`](../../../../../src/python/whero/doctidex/imports.py) could turn a tracked Installation into an
untracked Installation. In `_install_resolved`, a replaced Installation was built with:

```python
installation = replace(
    existing,
    commit_hash=commit_hash,
    tracked=tracked or bool(view.refs_for(existing)),
    keys=installation_keys,
)
```

For a branch or tag selector, the deterministic `install-id` is stable across commits. When an existing tracked
Installation had no managed Ref and was re-installed with `--untracked` after its source commit changed, `tracked`
was false and the expression made the record untracked. This moved a reproducible tracked declaration into the
machine-local runtime projection.

Tracking is one-way in the current surface: `import track` promotes an untracked Installation, and no command
demotes one. A tracked Installation can be removed with `import remove`, but it must not silently become untracked
as a side effect of re-installing a changed revision.

## Decision

`import install` keeps the same selector and `--tracked`/`--untracked` options. The meaning is now:

- a new Installation is created with the requested tracking state;
- `--tracked` may still promote an existing untracked Installation;
- `--untracked` never demotes an existing tracked Installation.

The existing-Installation replacement in `_install_resolved` uses:

```python
tracked=tracked or existing.tracked,
```

The replacement path no longer uses `view.refs_for(existing)`. Creating a Ref already promotes its Installation to
tracked, so the existing Installation's `tracked` field is the authoritative one-way fact.

[`docs/user/import.md`](../../../../user/import.md) and
[`skills/doctidex-git/SKILL.md`](../../../../../skills/doctidex-git/SKILL.md) state that tracking is one-way: a
tracked Installation must be removed before it can be installed as untracked.

## Verification

- The branch and tag regression cases in `src/python/tests/test_import.py` pass.
- The full default test suite passes: `247 passed, 7 deselected`.
- `ruff check whero/doctidex tests` passes.
- `scripts/validate-user-doc-links.py` passes.
- The skills tests pass: `8 passed`.
- `git diff --check` passes.

## Alternatives considered

**Reject `--untracked` when the command would replace an existing tracked Installation.**
Rejected: the command is already expected to work as a revision replacement, and the existing Ref path preserved
tracking rather than rejecting. Preserving tracking is less disruptive and keeps the one-way tracking invariant
without forcing a remove/reinstall cycle.

**Keep the previous behavior and document that `--untracked` may downgrade a tracked record.**
Rejected: this would contradict the tracked/runtime split. Tracked declarations are reproducible across clones;
allowing a normal `import install` invocation to move them into runtime state would silently lose durable metadata.

**Introduce a separate demotion command.**
Rejected: the requested invariant is that demotion is not allowed, not that a new way to perform it should be added.

## Consequences

A tracked Installation can no longer be demoted by re-installing its branch or tag selector with `--untracked`.
Users who want the selector to be untracked must remove the tracked Installation and then install the revision as
untracked. `--tracked` still promotes an existing untracked Installation when a replacement is needed, and the
one-way tracking contract is now explicit in both user documentation and the Twin Skill.
