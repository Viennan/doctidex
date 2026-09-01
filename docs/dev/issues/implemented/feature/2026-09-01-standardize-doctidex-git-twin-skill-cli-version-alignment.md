# Issue Note: Standardize doctidex-git Twin Skill and CLI version alignment

Status: implemented

## Problem

The shipped `doctidex-git` Twin Skill did not make its relationship to the co-released CLI explicit. The skill never
stated that it was authoritative only for the CLI version it shipped with, so an agent could read a skill installed for
one release while running a `doctidex-git` binary from another release.

There was no version metadata in the skill frontmatter and no supported way for an agent to compare the skill version
with the installed CLI version. The CLI had no `--version` option, and installation guidance explained `pipx`, `pip`,
and `uv` mechanics without naming the release source where users and agents obtain the supported version and wheel URL.

## Decision

The Twin Skill and CLI now carry the same version through three release-owned projections:

| Projection | Location |
|---|---|
| Python package version | `src/python/whero/doctidex/__init__.py` |
| PEP 440 project version | `src/python/pyproject.toml` |
| Twin Skill version | `skills/doctidex-git/SKILL.md` under `doctidex.version` |

`doctidex.version` is a top-level YAML field under `doctidex` and stores the PEP 440 CLI version. The skill
`description` remains concise and carries the Twin Skill identity and product promise; installation sources and
verification steps are not loaded into it.

`doctidex-git --version` prints the installed CLI version as plain text:

```text
doctidex-git 2.0.0
```

The option is a top-level informational surface rather than a command, does not resolve a Git root, and is an intentional
plain-text exception to the command JSON result contract.

The Twin Skill now contains a dedicated `## Install and update` section. It states the skill's version authority, points
to https://github.com/Viennan/doctidex/releases as the source of supported versions and wheel URLs, gives concise
`pipx` and virtual-environment install paths, and requires reinstalling the skill after a CLI update. `## Before you
start` requires running `doctidex-git --version` and comparing it with `doctidex.version`, especially after updating the
CLI or reinstalling skills.

The release workflow keeps all three version projections synchronized:

- `scripts/release/set-version.sh` updates `pyproject.toml`, `whero.doctidex.__version__`, and the skill frontmatter.
- `scripts/validate-version-alignment.py` fails when the three tracked projections differ, and `build-wheel.sh` runs it
  before building.
- `publish-alpha.sh` and `publish-final.sh` stage and commit the skill version file with the Python version change.

The user documents and Twin Skill maintenance scaffolding record the same contract:

- `docs/user/overview.md` is the owning installation reference and names the release URL.
- `docs/user/common.md` and `docs/user/skills.md` link to that owner and keep only the local command or reinstall
  requirement.
- `.agents/skills/doctidex-twin-skill-maintenance/SKILL.md` requires `doctidex.version` to match the co-released CLI.
- `docs/dev/architecture/overview.md` records the skill version as a release-owned projection and `--version` as the
  plain informational surface.

## Verification

- `src/python/tests/test_cli_contract.py` verifies `main(["--version"])` exits `0` and prints the package version.
- `src/python/tests/test_version_alignment.py` verifies the three tracked projections agree.
- The full default test suite passes.
- `ruff check` passes for the changed Python files.
- `scripts/validate-version-alignment.py` passes.
- `scripts/validate-user-doc-links.py --docs-root docs/user --references-root skills/doctidex-git/references` passes.
- The changed release scripts pass `bash -n`.
- `git diff --check` passes.

## Alternatives considered

**State version matching only in prose without frontmatter metadata.**
Rejected: prose is not machine-checkable, so an agent cannot reliably discover a mismatch before following the skill.

**Put the version in the frontmatter `description` or `name` instead of a structured field.**
Rejected: those fields are presentation-oriented; a structured `doctidex.version` field gives version comparison a
stable, parseable contract.

**Add a separate `--skill-version` command instead of `--version`.**
Rejected: `--version` is the conventional, discoverable surface, and one version value is enough; a second command
adds surface without adding information.

**Continue the previous installation prose and only add a GitHub Releases link.**
Rejected: the tool-by-tool instructions remained too long and did not make the version-to-skill reinstallation step
prominent.

## Consequences

Agents now receive an explicit version-matched operating contract: the skill records its target CLI version, the CLI
exposes the same value, and release tooling prevents the three version sources from drifting. The installation path
now names the release source and the required skill reinstallation after a CLI update.

The trade-off is additional release surface: a third version projection, a version-alignment validator, and updated
publisher scripts. `--version` is a plain-text exception to the JSON result convention, which is intentional for
conventional version discovery.

## Related

- [Add Twin Skill support to doctidex-git](2026-08-31-add-agent-skill-support-to-doctidex-git.md)
- [Formalize doctidex-git Twin Skill maintenance in scaffolding](../process/2026-08-31-formalize-doctidex-git-twin-skill-maintenance.md)
- [Build the doctidex-git CLI release workflow](../process/2026-08-31-build-doctidex-git-release-workflow.md)
- [Clarify doctidex-git installation and entry-point guidance](../bug-fix/2026-08-31-clarify-doctidex-git-installation-and-entry-point.md)
