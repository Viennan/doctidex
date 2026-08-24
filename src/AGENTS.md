# Source Code Guide

This **scoped-AGENTS.md** applies to code under `src/`. The root [AGENTS.md](../AGENTS.md) still applies.

## Scope

The active implementation is Python code under `src/python/`. Read [docs/dev/architecture/overview.md](../docs/dev/architecture/overview.md) before changing behavior.

## Common code conventions

- Keep parameter validation and compatibility at public interfaces.
- Define the internal implementation boundary clearly.
- Inside the internal implementation boundary, do not use extra `if` or `assert` checks to handle non-standard input.

## Python conventions

- Use the project-root `.venv` as the default Python runtime. Create it before use when it does not exist.
- Target Python 3.12 or later.
- Keep the package namespace under `src/python/whero/doctidex/`.
- Use `markdown-it-py` for Markdown parsing and `PyYAML` for structured annotation YAML.
- Use type annotations. When a parameter accepts multiple custom structural types, annotate it with a `Protocol`.
- After annotating with a `Protocol`, do not recover the original type with `isinstance` or similar checks; operate only through the Protocol.
- Resolve circular imports by refactoring, extracting a module, or merging modules; do not use local imports.

## Code style

- Use Ruff with line length 120.
- Keep the enabled rule set as `B`, `E`, `F`, `I`, `UP`.
- Preserve the current import grouping and clean up unused imports.

## Testing

- Keep tests under `src/python/tests/`.
- Use pytest.
- Require at least 80% test coverage; 90% is the quality target.
- Prefer public-interface functional coverage over small internal-interface tests for coverage numbers.
- Test cache and transaction behavior through the real workflow path where practical.

## Design authority

Architecture documents are the current-design authority. Do not let existing implementation idioms narrow the design. When code appears to conflict with design, re-read [docs/dev/architecture/overview.md](../docs/dev/architecture/overview.md) and resolve from design semantics.

When a code change needs a design decision, use [doctidex-issue-design](../.agents/skills/doctidex-issue-design/SKILL.md) before implementation. After design is explicitly authorized for implementation planning, use [doctidex-issue-impl](../.agents/skills/doctidex-issue-impl/SKILL.md) to create the plan and follow execution rules.
