---
name: submit-whero-wiki-change
description: Prepare and submit Whero Wiki repository changes through a named development branch, validation, intentional staging, commit, push, and a copyable PR or MR title and body, with xhigh subagent review only when separately authorized. Use when starting work that will be submitted remotely, preparing commits, pushing a branch, or drafting a pull-request or merge-request description for this repository.
---

# Submit Whero Wiki Change

Read the repository `AGENTS.md` and preserve unrelated worktree changes. This
Skill may create commits or push only when the user has explicitly requested
those remote-submission actions.

## Enforce Git Guardrails

- Never develop, commit, or push repository changes on `main`.
- Never merge a local development branch into local `main`.
- Update local `main` only by fast-forwarding it from its configured remote.
- Never discard, stash, reset, amend, rebase, force-push, or overwrite user work
  without explicit authorization for that exact operation.
- Do not use `gh`, `glab`, or another API client to create or edit a PR or MR.

## Start New Work

Require a clean worktree before synchronizing `main`. Determine the configured
remote and default branch rather than assuming names when they differ. For the
normal `origin/main` case:

```bash
git switch main
git fetch origin main
git pull --ff-only origin main
git rev-list --left-right --count origin/main...main
git switch -c <type>/<short-description>
```

Use a meaningful prefix such as `feat/`, `bugfix/`, `refactor/`, `docs/`,
`test/`, or `chore/`. Proceed only when the post-pull count is exactly `0 0`,
meaning local `main` equals the fetched remote branch. If local `main` is ahead,
behind after the pull, or divergent, stop and report the state. Do not resolve
it by merging into `main`.

If already-started uncommitted work is found on `main`, do not fetch, pull,
stage, commit, or push. With explicit user approval for the inferred branch
name, create a prefixed development branch at the current commit to preserve
the worktree. Then fetch and compare that branch with the remote base. Ask
before any rebase or history rewrite. This is recovery from a nonconforming
start, not permission to develop on `main`.

For already-started work, verify the current branch is not `main`, fetch the
remote baseline, and check that the branch is based on the current remote
default branch. If it is stale or divergent, report that fact and request
authorization before rebasing or otherwise rewriting history.

## Prepare The Change

1. Inspect `git status`, the branch, remotes, commits, and the complete net diff
   against the remote base. Include untracked and deleted files. Inspect
   `git diff --cached --name-only`; if the index contains unrelated user work,
   stop and ask rather than unstaging or committing it.
2. Run `$test-whero-wiki` with checks proportional to the change.
3. Run `$review-whero-wiki` only when the user separately and explicitly
   authorizes review. A request to commit, push, submit, or draft PR or MR text
   is not review authorization. Otherwise skip it and report that no review was
   run. Resolve or explicitly record every substantiated finding when review is
   authorized.
4. Re-run affected checks after fixes.
5. Require the index to be empty or to contain only paths explicitly authorized
   for this commit. Stage only intentional paths with `git add -- <paths>`.
   Inspect `git diff --cached --name-status` and `git diff --cached` before
   committing. Never unstage unrelated user work without approval.
6. Create a concise imperative commit, using a conventional prefix when useful.
   Do not amend an existing commit unless explicitly asked.
7. Push only the development branch, normally with:

   ```bash
   git push -u origin HEAD
   ```

Never push `HEAD` when it resolves to `main`. Never force-push without explicit
authorization and a stated reason.

## Draft The PR Or MR

Build the title and body from the net change between the remote base and the
submitted branch, not from abandoned intermediate attempts. Explain why first,
then what changed. Include meaningful validation, compatibility or rollout
considerations when applicable, and references to relevant issues.

Use repository-relative paths. Exclude local absolute paths, credentials,
private URLs, and confidential context. Do not claim remote CI results that
have not completed.

Do not create the PR or MR. End the response with one standalone fenced
Markdown block in this form so the user can copy it:

~~~markdown
```markdown
PR/MR title:
<concise title>

PR/MR body:

## Why
<motivation and user impact>

## What Changed
- <net change>

## Validation
- <command or focused behavioral verification>

## Risks
- <risk, rollout note, or "None identified">
```
~~~

Outside that block, report the pushed branch and commit, any compare URL that
can be derived without creating a PR or MR, and all skipped or blocked steps.
