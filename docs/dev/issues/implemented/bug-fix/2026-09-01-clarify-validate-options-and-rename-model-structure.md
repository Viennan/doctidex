# Issue Note: Clarify validate scope options and rename model-structure

Status: implemented

## Problem

[`docs/user/validate.md`](../../../../user/validate.md) showed the `validate` command but did not explain what
`--subdir`, `--model-structure`, or the default invocation did. The name `--model-structure` was also ambiguous:
it read like a subject rather than a mode. The Twin Skill did not mention scoped validation for cross-boundary
links.

## Decision

`validate` has three documented modes:

| Invocation | Behavior |
|---|---|
| `doctidex-git validate` | Full work-model check plus cross-boundary Markdown scan from `/`. |
| `doctidex-git validate --subdir <PATH>` | Full work-model check; Markdown scan scoped to the requested repository-internal directory. |
| `doctidex-git validate --only-model-structure` | Work-model check only; no Markdown scan. |

The public flag is `--only-model-structure`. The old `--model-structure` spelling is removed, not aliased. Internal
names match: the argparse destination is `only_model_structure`, `validate()` accepts
`only_model_structure`, and hook call sites pass `only_model_structure=True`.

[`docs/user/validate.md`](../../../../user/validate.md#usage) owns the mode table. User and architecture references
use the new flag. [`skills/doctidex-git/SKILL.md`](../../../../../skills/doctidex-git/SKILL.md) updates its bootstrap
snippets, states that crossing any BoundaryPoint requires a `doctidex` StructuredLinkAnnotation, and offers
`validate --subdir <REPOSITORY-PATH>` as a scoped check.

## Verification

- `ruff check` passes for the changed Python source and tests.
- The default test suite passes: 222 passed, 7 deselected.
- `scripts/validate-user-doc-links.py` passes.
- The skills tests pass: 8 passed.
- `git diff --check` passes.
- `rg -- '--model-structure|model_structure=' src/python/whero src/python/tests` finds no old code/test spelling.

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

## Consequences

The command surface is now self-describing: the flag name says what it excludes, and the user guide states the
default and scoped behaviors. Agents can validate only a changed scope rather than the whole tree.

The trade-off is a breaking rename during the unstable line. `--subdir` remains a scan scope, not a work-model
scope, so model checks still run for the whole repository even when links are scoped.
