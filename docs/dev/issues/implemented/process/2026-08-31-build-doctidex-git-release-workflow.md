# Issue Note: Build the doctidex-git CLI release workflow

Status: implemented

## Problem

`doctidex-git` had no repeatable release workflow. Publication relied on ad-hoc steps, and the intended distribution
surface is a Git release tag rather than PyPI. Without a fixed workflow, version and wheel naming, alpha validation,
and release acceptance could drift between releases.

The product is a pure-Python Linux/macOS CLI, so one `py3-none-any` wheel is sufficient.

## Decision

The repository now ships a release workflow as scaffolding and scripts.

### Version and artifacts

One version family produces:

| Object | Alpha | Final |
|---|---|---|
| PEP 440 project version | `X.Y.Za1` | `X.Y.Z` |
| Release branch | `release/vX.Y.Z` | same branch |
| Git tag | `vX.Y.Za1` | `vX.Y.Z` |
| Wheel | `whero_doctidex-X.Y.Za1-py3-none-any.whl` | `whero_doctidex-X.Y.Z-py3-none-any.whl` |

`set-version.sh` updates both `pyproject.toml` and `__init__.py` from one version. `build-wheel.sh` builds the wheel
and rejects an unexpected filename. No PyPI publication is performed.

### Release scripts

[`scripts/release/`](../../../../../scripts/release/) contains:

- [`set-version.sh`](../../../../../scripts/release/set-version.sh);
- [`build-wheel.sh`](../../../../../scripts/release/build-wheel.sh);
- [`generate-release-notes.sh`](../../../../../scripts/release/generate-release-notes.sh);
- [`publish-release.sh`](../../../../../scripts/release/publish-release.sh).

Before either GitHub release is created, `gh auth status` must pass, the version change must be committed to the
release branch, and the release branch must be pushed to `origin`. `publish-release.sh` verifies the remote branch
before calling `gh release create`.

Release notes include only newly implemented `feature`, `architecture`, and `bug-fix` Issue Notes, pinned to the
final tag and based on the previous same-major final release.

### Alpha test

[`scripts/release/alpha-test/`](../../../../../scripts/release/alpha-test/) contains
[`prepare-workspace.sh`](../../../../../scripts/release/alpha-test/prepare-workspace.sh) and
[`accept.sh`](../../../../../scripts/release/alpha-test/accept.sh). `prepare-workspace.sh <BASE> <VERSION>` creates a
fresh versioned workspace with `.venv`, `bin/doctidex-alpha`, and a command log. The fixed prompt forbids `pipx` and
requires installing the alpha wheel into the prepared `.venv`. `accept.sh` verifies the installed version, workspace,
Git hooks, installed Twin Skill and real `references/` directory, tracked alpha tag, and expected command log.

The fixed prompt and acceptance are documented in
[`docs/dev/alpha-tests/01-install-tracked-alpha.md`](../../../../../docs/dev/alpha-tests/01-install-tracked-alpha.md),
and [`docs/dev/testing.md`](../../../../../docs/dev/testing.md#alpha-tests) points to the alpha-test directory.

### Scaffolding

The workflow is discoverable through [`.agents/skills/doctidex-release/SKILL.md`](../../../../../.agents/skills/doctidex-release/SKILL.md),
with root [`AGENTS.md`](../../../../../AGENTS.md) routing release and packaging actions to that skill.

## Verification

- All six release shell scripts pass `bash -n`.
- `build-wheel.sh 2.0.0.dev0` produced `whero_doctidex-2.0.0.dev0-py3-none-any.whl`.
- `prepare-workspace.sh` produced distinct `alpha-<VERSION>-XXXXXX` workspaces with `.git`, `.venv`, the wrapper, and
  the command log.
- Scaffolding and alpha-test links resolve.
- `git diff --check` passes.

## Alternatives considered

**Publish the wheel to PyPI instead of attaching it to a Git release.**
Rejected: the requested distribution surface is Git release tags, and PyPI adds an account and publication surface
that is not needed for this product yet.

**Run the release as fully manual steps without helper scripts.**
Rejected: version/wheel naming and alpha workspace preparation are repetitive and error-prone; scripts make the
workflow repeatable without removing the human decision points.

**Automate the entire workflow in GitHub Actions.**
Rejected: the requested workflow is local-first with user confirmation and a prompt-driven alpha test. A CI workflow
is not the first step and would introduce separate runner and secret management before the local process is stable.

**Verify the alpha with the existing unit tests instead of a subagent workspace test.**
Rejected: unit tests do not observe the released wheel URL, fresh-environment installation, skill installation, or
the prompt that an end consumer will follow.

**Use a separate release branch for the alpha.**
Rejected: the alpha and final release share one release branch and version series; a separate branch would create
extra merge and tag coordination without adding safety.

## Consequences

The release process is now repeatable and discoverable from repository scaffolding rather than an Issue Note. Agents
can build, publish, alpha-test, and release through the `doctidex-release` skill and scripts without re-deriving the
workflow.

The trade-off is new repository tooling surface: release scripts, alpha-test scripts and documents, and a
repository-local skill. The alpha test still depends on network access, the published alpha tag and wheel URL, and a
subagent that can run the fixed prompt.

## Related

- [Clarify doctidex-git installation and entry-point guidance](../bug-fix/2026-08-31-clarify-doctidex-git-installation-and-entry-point.md)
