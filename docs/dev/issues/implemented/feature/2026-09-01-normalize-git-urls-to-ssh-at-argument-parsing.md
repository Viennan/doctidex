# Issue Note: Normalize Git URLs to SSH at argument parsing

Status: implemented

## Problem

`import install` and `worktree create` previously accepted `--url` as given and stored it in the work model. An HTTPS
URL could therefore be recorded while a host-level Git configuration rewrote HTTPS to SSH during physical Git
operations. The recorded and physical origins then differed, producing
`installation.worktree.inconsistent` during validation.

## Decision

Remote Git source URLs use the canonical SSH form. `repository.py` now exposes `normalize_git_url`, which:

- leaves SSH/scp-like URLs unchanged;
- converts `http://` and `https://` remote URLs to `git@host:path`, preserving nested repository paths and an
  optional `.git`;
- leaves local filesystem paths unchanged.

The CLI uses `normalize_git_url` as the argparse `type` for `--url` on `import install` and `worktree create`, so
conversion happens before workflow resolution or cache access. The normalized value is the one stored in
`Installation.git-url`, `Worktree.url`, default keys, share records, and validation expectations.

[`docs/user/import.md`](../../../../user/import.md) and [`docs/user/worktree.md`](../../../../user/worktree.md)
document that remote URLs use SSH form and that HTTPS input is accepted and converted. The Twin Skill
[`SKILL.md`](../../../../../skills/doctidex-git/SKILL.md) carries a short reminder of the same behavior.

## Verification

- `test_repository_helpers.py` covers HTTPS-to-SSH, SSH passthrough, and local-path passthrough.
- `test_import.py` includes a functional check that an HTTPS `--url` is reported with the normalized SSH `git-url`.
- `ruff check` passes.
- The default test suite passes: 226 passed, 7 deselected.
- `scripts/validate-user-doc-links.py` and the skills tests pass.
- `git diff --check` passes.

## Alternatives considered

**Keep the URL as supplied and make validation compare normalized Git remote URLs.**
Rejected: the recorded identity would still differ from the physical origin and from the source used for cache keys.
Normalizing once at the boundary keeps one canonical form everywhere.

**Normalize inside the cache/resolution layer rather than argument parsing.**
Rejected: normalization is a user-input contract. Applying it later leaves the recorded `git-url` subject to the
host Git rewrite and makes diagnostics show a different URL from the one the user entered.

**Support both HTTPS and SSH as equal canonical forms.**
Rejected: two forms for one source duplicate identity paths and reproduce the validation mismatch across machines
with different Git configuration.

**Reject HTTPS URLs outright.**
Rejected: accepting HTTPS and converting it is more usable, and the user explicitly wants HTTPS input converted to
SSH rather than rejected.

## Consequences

Remote source identity is now stable and machine-independent: HTTPS input becomes SSH before it can be recorded, so
validation no longer sees a mismatch caused by local Git URL rewriting.

The trade-off is a narrower documented remote URL surface. Local filesystem paths still work for repository-local
fixtures, but remote HTTPS URLs are treated as input sugar rather than a second canonical identity.
