# Issue Note: Write Git hook scripts in a tool-compatible way

Status: implemented

## Problem

`hook install` wrote `pre-commit` and `post-checkout` directly into the Git hooks directory and replaced any file at
those names. Tools such as husky, lefthook, and pre-commit could already own those hooks or set `core.hooksPath`, so
the install path silently overwrote or bypassed that tooling. The generated scripts also used `exec`, so an existing
hook could not run after the doctidex worker.

## Decision

`hook install` now modifies existing hook scripts in place instead of replacing them. It injects a marked doctidex
block after the leading comment block and before the original first non-comment line.

### Injected block

For a hook named `<name>`, the injected block is:

```sh
# doctidex-git begin <name>
/resolved/path/to/doctidex-git hook <name> "$@" || exit $?
# doctidex-git end <name>
```

The injected command runs first. If it fails, the script exits and the original hook content does not run. On success,
the shell continues with the original lines.

### Injection and idempotency

`hook install` keeps the shebang and leading comments at the top, inserts one blank line, the marked block, and one
blank line before the original first non-comment line. If the first executable region already contains the current
marked block, the script is left unchanged. Otherwise any previous doctidex block is removed and the current block is
inserted.

`core.hooksPath` is respected through the existing hooks-path resolution; doctidex does not change the configured hook
path.

## Verification

The full test suite passes. `ruff check src/python/whero/doctidex src/python/tests` passes and `git diff --check`
passes. Tests cover absent scripts, existing scripts, comment-only scripts, repeated installation, old-block removal,
successful delegation to the existing hook, and short-circuiting when doctidex fails.

## Consequences

Existing hook content is preserved below the injected block, and doctidex is a first participant in the hook chain. A
doctidex failure stops the chain as part of the user contract.

The implementation uses no backup file. If another hook manager later regenerates the script, a subsequent
`hook install` re-injects the current block. Backward compatibility with older injected command formats is not
provided because the product is unstable.

## Related

- [Add a pre-commit model-structure validation hook](../feature/2026-08-29-add-pre-commit-model-structure-validation-hook.md)

## Alternatives considered

**Keep direct overwrite.**
Rejected: it is simple, but it breaks interoperability with existing hook managers.

**Refuse to install when hooks are managed by another tool.**
Rejected: it avoids clobbering but leaves doctidex without its commit or checkout behavior in those repositories.

**Adopt or require a third-party hook manager.**
Rejected: it adds a dependency and moves the product out of its current `hook install` ownership.

**Set `core.hooksPath` to a doctidex-only directory without delegation.**
Rejected: it risks displacing existing hook managers and does not preserve their behavior.

**Use a separate dispatcher directory with saved previous hook path.**
Rejected for this issue: it gives clearer ownership, but it adds a dispatcher and more state for the same preservation
result.

**Add recognized hook-manager adapters now.**
Rejected for the first implementation: it has the widest surface and ongoing maintenance cost; it can be added later
without changing the selected injection convention.
