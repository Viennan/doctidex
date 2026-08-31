# Issue Note: Clarify doctidex-git installation and entry-point guidance

Status: implemented

## Problem

User documentation and the `doctidex-git` Twin Skill previously said only that `doctidex-git` must be on `PATH`.
They did not explain that `doctidex-git` is a Python console-script entry point, or where that entry point appears
after installing the wheel. This left agents and users to guess whether to activate a virtual environment or to edit
shell rc files to make the command resolve.

## Decision

[`docs/user/overview.md`](../../../../user/overview.md#prerequisites) now owns the installation and entry-point
guidance. It recommends:

```bash
pipx install <WHEEL-URL>
```

`pipx` installs the CLI in an isolated environment and makes `doctidex-git` available on `PATH`; `pipx ensurepath`
is the recovery step when the command is not found. The guide describes the virtual-environment fallback only when
pipx is unavailable or disallowed: install the wheel with `pip` or `uv`, then use `<venv>/bin/doctidex-git` or
activate the environment. `command -v doctidex-git` confirms resolution, and the guidance does not instruct users to
edit shell rc files.

[`docs/user/common.md`](../../../../user/common.md#git-root-and-paths) states the pipx recommendation in one sentence
and links back to the overview for the fallback. It does not repeat the install steps.

[`skills/doctidex-git/SKILL.md`](../../../../../skills/doctidex-git/SKILL.md) replaces the old `Confirm
doctidex-git is on PATH` prerequisite with a short `pipx install <WHEEL-URL>` pointer to the same guidance.

The packaged `whero.doctidex._skill_data` copy was rebuilt so installed skills match the development tree.

No CLI behavior or source code changed.

## Verification

- `scripts/validate-user-doc-links.py` passes against `docs/user/` and `skills/doctidex-git/references/`.
- `src/python/tests/test_skills.py` and `src/python/tests/test_skills_cli.py` pass: 8 passed.
- The packaged `_skill_data` contains the updated Twin Skill.
- `git diff --check` passes.
- No source code changed, so the default test suite was not a required checkpoint.

## Alternatives considered

**Keep only the current `on PATH` wording.**
Rejected: it does not name the entry point or explain the virtual-environment case, which is exactly the failure
that makes agents hunt for or create a global command.

**Document the venv path only in the release workflow.**
Rejected: the confusion affects ordinary users and Twin Skill consumers, not only the release alpha test.

**Add a wrapper or installer command that registers `doctidex-git` globally.**
Rejected: the Python packaging entry point is already the correct mechanism. Adding a global registration step
increases side effects and is not needed for the product.

**Instruct users to add the venv `bin` directory to their shell rc file.**
Rejected: that changes the user's persistent environment and is not an appropriate prerequisite for a
repository-local tool.

## Consequences

Users and agents now get a clear pipx-first install path, with a virtual-environment fallback only when pipx cannot
be used. This reduces the chance that an agent will fail command resolution or edit `~/.zshrc`/`~/.zprofile`.

The trade-off is that the recommended path depends on `pipx`; the fallback remains present for users who cannot or
do not want pipx. The virtual-environment path is Unix-specific, which is acceptable while the product targets
Linux/macOS.

## Related

- [Build the doctidex-git CLI release workflow](../process/2026-08-31-build-doctidex-git-release-workflow.md)
