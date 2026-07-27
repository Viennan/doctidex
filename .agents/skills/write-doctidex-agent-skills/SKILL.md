---
name: write-doctidex-agent-skills
description: Design, create, or revise agent-facing Skills and their metadata for doctidex, including published product Skills under impls/agent-plugins and repository-maintenance Skills under .agents/skills. Use when defining triggers, mental models, reading chains, command contracts, failure guidance, progressive disclosure, or Skill validation; do not use for ordinary product documentation.
---

# Write doctidex Agent Skills

Create Skills that let another agent complete the supported workflow without guessing, reading
implementation code, or inheriting the authoring conversation. Keep the Skill concise and route
detailed contracts through shallow references.

## Select the Audience First

Distinguish two surfaces:

- Published product Skills under `impls/agent-plugins/` are written for an installed product. They
  must not depend on this repository, source paths, implementation documents, tests, or debug setup.
- Repository-maintenance Skills under `.agents/skills/` are local developer workflows. They may
  require `AGENTS.md`, repository-relative authorities, code, tests, and local validation commands.

Never leak repository-only guidance into a published Skill. Do not weaken published user-surface
rules merely because a maintainer Skill has deeper access.

## Define Trigger and Scope

1. Gather concrete trigger examples and non-trigger examples.
2. Put all “when to use” information in the frontmatter `description`; keep frontmatter to `name`
   and `description` only.
3. Use lowercase hyphenated, preferably verb-led names under 64 characters.
4. State authority and mutation boundaries in the body. A review Skill must require explicit review
   authorization; write or repair authority must be separately explicit.
5. When the user authorizes file creation for a new Skill, use the environment's `skill-creator`
   workflow and initialization tooling rather than hand-building an incomplete folder. For a
   design-only, review-only, or no-edit request, propose the scaffold and stop before initialization.

## Design the Reading Chain

Use one foundational/orchestrator Skill for shared mental model, terms, CLI grammar, outputs, safety,
and routing. Put task-specific workflows in specialized Skills. Keep the chain explicit and acyclic;
a specialized Skill may route to the foundation when unfamiliar and to another specialist only at a
real workflow boundary.

Define acyclicity over the runtime reading sequence. A routing table may name specialists and an
unfamiliar specialist may direct the agent to load the foundation once, but the resulting sequence
must be `foundation -> selected specialist -> next specialist` without reopening an already-loaded
Skill. Say “if not already read” and where to resume whenever a backward-looking routing link exists.

Do not copy shared paragraphs into every Skill. Keep `SKILL.md` procedural and under 500 lines;
place detailed references one level below it, link each directly, and say when to read it. Do not add
README, changelog, installation guide, or unused resource directories.

## Write the User Mental Model

Define every specialized term before use. Explain the problem, user-controlled inputs, default
context, observable result, and next decision. Preserve the agent's native file, search, shell,
editing, and Git tools. Add only domain-specific objective assistance; do not wrap mature tools
without meaningful doctidex information.

For published Skills, expose logical roots, paths, mounts, revisions, statuses, and actions needed to
work. Hide caches, keys, locks, worktree management, internal schemas, repository setup, test commands,
and implementation diagnostics. Maintenance paths needed to edit are public; how they are created is
not.

## Specify Commands Completely

Read [command-contract.md](references/command-contract.md) whenever a Skill introduces or routes to
a CLI command. A foundational Skill plus the relevant specialized Skill must define exact invocation,
arguments, constraints, omission behavior, context/root selection, read/write/network effects,
preview/apply, batch behavior, bounded collections, decision fields, and actionable failures.

Do not force agents to infer syntax from examples or repeatedly call `--help`. Examples supplement a
contract; they do not replace it.

## Keep Objective and Subjective Work Separate

CLI helpers must be deterministic and non-AI. They may parse, validate, format supplied content, or
report objective facts. Agents author index prose, log entries, summaries, priorities, semantic
judgments, and review conclusions. Never imply that an empty candidate list proves semantic quality.

Control result size. Document path scoping, limit, depth, pagination, collapse, and structural summary
where applicable. Do not encourage maximum limits or unbounded path enumeration.

## Design Failure Guidance

For each expected failure explain the user-level cause, affected object, incomplete operation,
preserved result, ordered safe actions, and whether user input is required. Do not expose stack traces
or internal storage as a normal decision surface. Tell the agent to report unrecoverable errors
directly to the user with usable facts.

## Create Metadata and Validate

Generate `agents/openai.yaml` from the final Skill. Quote strings; keep `display_name`, a 25–64
character `short_description`, and a one-sentence `default_prompt` that explicitly names
`$skill-name`. Set `policy.allow_implicit_invocation: false` when the Skill must only run after an
explicit user action, such as repository review.

Validate every changed Skill and metadata with:

```text
.venv/bin/python <skill-creator-dir>/scripts/quick_validate.py <skill-dir>
```

For a published Skill, also validate its containing plugin with:

```text
.venv/bin/python <plugin-creator-dir>/scripts/validate_plugin.py <plugin-dir>
```

Resolve `<skill-creator-dir>` and `<plugin-creator-dir>` from the active Skill catalog entries; do
not search product source or copy these maintenance commands into published Skills. Run forward
tests on realistic requests using fresh independent agents, raw artifacts, and no expected answer
leakage. Include clean, failure, ambiguity, and boundary cases; revise the Skill when success depends
on authoring context.

Read [content-checklist.md](references/content-checklist.md) for the final completeness pass.
