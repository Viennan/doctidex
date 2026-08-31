# Alpha test: install the alpha wheel and track its tag

This test verifies the released alpha wheel through a fresh, prompt-driven Codex run.

## Workspace

`prepare-workspace.sh <BASE> <VERSION>` creates a unique fresh workspace whose directory name includes the version
under test:

- an initialized Git repository;
- its own `.venv`;
- `bin/doctidex-alpha`, a wrapper anchored to `.venv/bin/doctidex-git`;
- `alpha-command.log`.

`BASE` is any writable parent directory supplied by the caller. The script creates a fresh
`alpha-<VERSION>-XXXXXX` subdirectory under it on every run, so `BASE` must not be the workspace itself.

The wrapper exports a non-default `DOCTIDEX-GIT-HOME`, invokes the installed alpha CLI, and appends one line per call:
`<timestamp> <exit-code> <argument>...`.

## Fixed prompt

Substitute `WORKDIR`, `VERSION`, `WHEEL_URL`, and `GIT_TAG` before running this prompt with Codex:

```text
Work only inside WORKDIR. It is already a Git repository with a .venv.
Do not use pipx.
Install the doctidex-git alpha wheel from WHEEL_URL into WORKDIR/.venv.
Install the bundled Twin Skill into WORKDIR/.agents/skills with the CLI's skills install command, for example
WORKDIR/bin/doctidex-alpha skills install --path WORKDIR/.agents/skills, and read it.
Use WORKDIR/bin/doctidex-alpha for every doctidex-git command; it supplies DOCTIDEX-GIT-HOME.
Do not inspect or modify the installed Python source files. Use only the installed Twin Skill and its references.
Initialize the workspace, then import the alpha tag GIT_TAG as a tracked Installation. The version under test is
VERSION.
```

Run it from the prepared workspace:

```bash
codex exec --ephemeral -C <WORKDIR> --skip-git-repo-check -s danger-full-access \
  --dangerously-bypass-approvals-and-sandbox '<PROMPT>'
```

## Acceptance

Run:

```bash
scripts/release/alpha-test/accept.sh <WORKDIR> <PEP440-VERSION> <GIT-TAG>
```

The test passes when all of the following hold:

- `.venv` contains the expected alpha version;
- `.doctidex-git/` is initialized;
- `pre-commit` and `post-checkout` Git hooks are installed;
- the bundled Twin Skill is installed at `.agents/skills/doctidex-git/`, and its `references/` is a real directory
  rather than a symlink;
- the alpha tag is recorded as a tracked Installation in `imports.json`;
- `alpha-command.log` records `init`, `skills install`, and a tracked `import install` with exit code `0`.
