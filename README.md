# Whero Wiki

Whero Wiki is an agent-oriented model for organizing, maintaining, querying,
and selectively exposing source-preserving knowledge. This repository contains
the v0.0.2 protocol, a portable Codex Skill, Python tooling, workflow references,
and the conformance test suite.

The project is inspired by Google's Open Knowledge Format (OKF) and Karpathy's
LLM Wiki. It remains at an early validation stage; its protocol and tooling
should be treated as experimental and subject to change.

## What You Can Use It For

- **Build a source-preserving knowledge base.** Collect documentation, research,
  standards, and other source snapshots without rewriting them, then add
  maintained indexes and provenance-backed concepts for faster navigation,
  comparison, querying, and citation.
- **Create project knowledge and code maps.** Describe requirements, design
  decisions, implementation entry points, component responsibilities, data
  models, and call relationships alongside a codebase. Whero Wiki supports both
  non-invasive analysis of third-party repositories and project Wikis maintained
  as part of active development.
- **Give development agents durable context.** Route an agent to the relevant
  requirements, design rationale, implementation map, and source evidence so it
  can plan changes with less repeated discovery. Git-aware provenance and
  affected-concept queries help identify knowledge that may need review after
  code changes.
- **Prepare focused context for a task.** Create a structure-preserving View that
  exposes only the files needed for a task while retaining navigation,
  provenance, and ownership boundaries. Expand the View incrementally when the
  agent encounters a genuine information gap.
- **Maintain knowledge without erasing authority.** Keep curated summaries and
  interpretations separate from collected sources, detect stale provenance,
  validate links and framework structure, and preserve nested repositories or
  externally owned material as explicit boundaries.

## Repository Structure

- [`whero-wiki/`](whero-wiki/) is the canonical product bundle and is itself a
  minimally self-hosted Whero Wiki and also an agent `skill` ready to use.
- [`whero-wiki/spec/`](whero-wiki/spec/) contains the normative English protocol
  and synchronized Chinese translations under `spec/CN/`.
- [`whero-wiki/SKILL.md`](whero-wiki/SKILL.md) is the concise user and agent
  interface. Detailed operational guidance lives in `whero-wiki/references/`.
- [`whero-wiki/scripts/`](whero-wiki/scripts/) contains the maintenance,
  validation, link, boundary, restoration, and View tooling.
- [`whero-wiki/tests/`](whero-wiki/tests/) contains tests for the current
  protocol and runtime.
- [`asserts/`](asserts/) contains immutable collected fixtures. Tests operate on
  copies under `.tmp/`.
- [`.agents/skills/`](.agents/skills/) contains repository development Skills
  for testing, review, and remote submission.
- [`.codex/config.toml`](.codex/config.toml) sets trusted project-level Codex
  behavior, including a four-thread agent concurrency limit.

## Model At A Glance

A Whero Wiki is identified by `whero-wiki-meta.md`. It distinguishes collected
sources from Whero-maintained knowledge, keeps framework navigation explicit,
records curated provenance, respects preserved and mounted ownership
boundaries, and uses structure-preserving Views for selective read-through
access. Internal maintained links are relative Markdown links.

The English protocol is normative. `SKILL.md` and workflow references expose
supported operations to agents without duplicating the complete protocol.

## Quick Start

Create the repository environment and install the portable Skill dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r whero-wiki/requirements.txt
```

Inspect the CLI:

```bash
.venv/bin/python whero-wiki/scripts/whero_wiki.py --help
```

Use [`$test-whero-wiki`](.agents/skills/test-whero-wiki/SKILL.md) for the full
isolated test and validation workflow, including self-hosted Wiki validation.

## Development Workflow

Do not start development on `main`. Begin with
[`$submit-whero-wiki-change`](.agents/skills/submit-whero-wiki-change/SKILL.md),
which checks for a clean worktree, discovers the configured remote and default
branch, synchronizes `main` to an exact remote baseline, and creates a prefixed
development branch. Use prefixes such as `feat/`, `bugfix/`, `refactor/`,
`docs/`, `test/`, or `chore/`.

Never merge a local development branch into local `main`; submit the branch
through the remote PR or MR workflow.

Repository instructions are in [`AGENTS.md`](AGENTS.md). Run
[`$review-whero-wiki`](.agents/skills/review-whero-wiki/SKILL.md) only when the
user explicitly authorizes review; final handoff or submission alone does not
authorize it. The submission Skill also handles commits, pushes, and copyable
PR or MR text without creating the PR or MR through a hosting-service CLI.

## License

This project is licensed under the [MIT License](LICENSE).
