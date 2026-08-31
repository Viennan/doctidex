# Issue Note: Add user-doc link validation and structure rules

Status: implemented

## Problem

Packaging `docs/user/` into a Twin Skill requires the user documents to remain internally reachable after they
are copied into `skills/doctidex-git/references/`. Before this decision, that property was not enforced:
`docs/user/overview.md` linked to the architecture overview under `docs/dev/`, outside the user surface, and the
repository had no common home for helper scripts or a mechanical gate against dangling links in the published skill.

## Decision

`docs/user/` is flat. The former `docs/user/reference/*.md` files now live directly under `docs/user/`, and
`docs/user/overview.md` links to them as siblings.

`scripts/validate-user-doc-links.py` is the mechanical user-document link gate. It takes `--docs-root` and
`--references-root`, parses Markdown with `markdown-it-py`, and rejects schemes, netlocs, leading `/`, and `..`
escapes. It verifies that each target stays inside `docs/user/`, exists in the packaged `references/` tree, and that
any fragment resolves. It emits one JSON violation per bad link and exits non-zero.

`src/python/tests/test_validate_user_doc_links.py` is the only test for that script. It is marked `validator_script`
and `no_cover`, so the default suite excludes it and coverage does not include it. The run command is documented in
`docs/dev/testing.md`.

The user-documentation contract is recorded in `docs/AGENTS.md` and
`.agents/skills/doctidex-doc-maintenance/SKILL.md`: links stay relative and inside `docs/user/`, usage-required design
context is explained in place, and user documents do not link to or copy large portions of `docs/dev/`. The root
`AGENTS.md` directory diagram records `scripts/` as the repository-local helper-script tree.

The packaging step owned by
[the companion feature issue](../feature/2026-08-31-add-agent-skill-support-to-doctidex-git.md) runs the
validator against `docs/user/` and `skills/doctidex-git/references/` and aborts on a non-zero result.

## Verification

The dedicated test suite passes with:

```bash
cd src/python
../../.venv/bin/python -m pytest -o addopts='' -m validator_script \
  tests/test_validate_user_doc_links.py
```

The default suite excludes that file via `addopts`, and the full default suite passes. The validator also passes
against a temporary copy of the flat `docs/user/` tree:

```bash
.venv/bin/python scripts/validate-user-doc-links.py \
  --docs-root docs/user \
  --references-root <TEMP-COPY>
```

`ruff check scripts/validate-user-doc-links.py src/python/tests/test_validate_user_doc_links.py` and
`git diff --check` pass.

## Alternatives considered

**Validate links manually during review.**
Rejected: a human check does not reliably catch dangling links in a copied skill, and the repository needs a
mechanical gate.

**Rewrite links during packaging.**
Rejected: rewriting changes the source contract at publication time and hides the fact that the source layout is not
self-contained.

**Place the helper script under `src/` or `.agents/skills/`.**
Rejected: `src/` is shipped product code and `.agents/skills/` is agent scaffolding. Repository-local helper scripts
belong in the separate `scripts/` tree.

**Keep the existing out-of-scope architecture link and exempt it from validation.**
Rejected: that link would dangle after the user documents are copied into the skill, and an exception would weaken the
invariant the script protects.

**Move the needed design text wholesale into user documents.**
Rejected: it duplicates authoritative design prose and creates a second source that can drift from `docs/dev/`.

**Keep design links in user documents and make the published skill resolve them back to the repository.**
Rejected: the published skill must be self-contained, and a non-user-document link would dangle after installation.

**Preserve the `docs/user/reference/` subdirectory.**
Rejected: the flat layout removes one needless level and lets `overview.md` link to sibling reference files directly.

## Consequences

User documentation is now self-contained and mechanically protected from out-of-scope or dangling links, and the
repository has a stable `scripts/` home for helper tooling.

The dedicated validator test is intentionally outside the default suite and coverage. It must be run explicitly during
changes to `scripts/validate-user-doc-links.py`, and the documentation points to the exact command.

User-facing prose may not link to design documents, so contributors must summarize usage-required context in place
without duplicating large sections of `docs/dev/`. The link validator enforces only reachability, not that balance.
