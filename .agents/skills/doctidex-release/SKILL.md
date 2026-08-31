---
name: doctidex-release
description: Build, validate, and publish doctidex-git releases through Git release tags, including alpha testing and release notes.
---

# doctidex-release

This is a guide, not a script. It owns the execution rules for the `doctidex-git` release workflow. Design rationale
and versioning decisions live in the
[release workflow Issue Note](../../../docs/dev/issues/developing/process/2026-08-31-build-doctidex-git-release-workflow.md).

## When to use it

Use this workflow when a release must move from `main` through an alpha pre-release to a final Git release tag. It
does not publish to PyPI.

## Workflow

Run the phases in order and stop at a failed checkpoint:

1. From `main`, fetch, fast-forward, confirm `vX.Y.Z`, then create `release/vX.Y.Z`.
2. Run the default test suite.
3. Set the alpha version, build the alpha wheel, smoke-test it, and publish `vX.Y.Za1`.
4. Run the alpha test.
5. Generate release notes, set the final version, build the final wheel, and publish `vX.Y.Z`.

The user confirms the version and the decision to proceed after each phase. The scripts own the mechanical steps.

## Scripts

- [`set-version.sh`](../../../scripts/release/set-version.sh) updates the Python version in both version sources.
- [`build-wheel.sh`](../../../scripts/release/build-wheel.sh) builds the pure-Python wheel and verifies its filename.
- [`generate-release-notes.sh`](../../../scripts/release/generate-release-notes.sh) lists newly implemented
  `feature`, `architecture`, and `bug-fix` Issue Notes.
- [`publish-release.sh`](../../../scripts/release/publish-release.sh) creates a GitHub release and attaches the wheel.

Use the project-root `.venv` for Python commands.

## Alpha test

Prepare a fresh workspace with:

```bash
scripts/release/alpha-test/prepare-workspace.sh <BASE> <VERSION>
```

The script creates a unique versioned workspace such as `alpha-<VERSION>-XXXXXX`, its `.venv`, the
`bin/doctidex-alpha` wrapper, and the command log. Read the fixed prompt and acceptance checks in
[`01-install-tracked-alpha.md`](../../../docs/dev/alpha-tests/01-install-tracked-alpha.md), run the subagent task, then
run:

```bash
scripts/release/alpha-test/accept.sh <WORKDIR> <PEP440-VERSION> <GIT-TAG>
```

The alpha prompt forbids `pipx` and installs the wheel into the prepared `.venv`.

## Release rules

- Never publish to PyPI.
- Use immutable tags. Do not move or delete a published tag after release notes reference it.
- Publish one universal `py3-none-any` wheel while the package remains pure Python.
- Use the `gh` token permissions documented in the Issue Note: classic PAT `repo`, or fine-grained
  `Contents: Read and write` plus `Metadata: Read`.
