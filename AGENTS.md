# Repository Guide

## Project Scope

`doctidex` is an emerging directory-tree structure standard for use by both
agents and humans. Its current design goals are interoperability, extensibility,
and minimal format constraints.

## Repository Layout

- `spec/overview.md` contains the draft `doctidex` protocol.
- `spec/refs/` contains background reference material.
- `impls/` contains the non-normative implementations of the standard,
  including implementation design documents, shared libraries, and public
  surfaces used by agents.
- `impls/docs/` contains implementation design documents.
- `impls/docs/doctidex-git/` documents the current Git plugin implementation,
  including its architecture, runtime, CLI schema, and agent interpretation.
- `impls/libs/` contains shared implementation libraries.
- `impls/libs/python/` contains the Python implementation.
- `impls/agent-plugins/` contains agent plugins and their agent-facing
  surfaces. `doctidex-git/` provides the plugin for Git repositories.
- `.asserts/` contains read-only source material used to construct tests.
- `.tmp/` contains disposable test workspaces and is ignored by Git.

## Sources of Context

- `impls/docs/` may define stricter implementation conventions, but those
  conventions are not protocol requirements.
- `spec/refs/` contains background references, not `doctidex` requirements.
- `.asserts/` contains collected source material. Treat it as read-only.

## Working Rules

- Keep proposals, accepted specification, and implemented behavior visibly
  distinct.
- Keep `spec/` focused on standard definitions and `impls/` focused on
  non-normative implementation design, code, and agent-facing surfaces.
- Keep the protocol focused on observable structure, semantics, and
  conformance. Implementation, construction, and maintenance workflows belong
  to implementation variants.
- Do not turn placeholders such as "refer to OKF" into detailed requirements
  without an explicit design decision.
- Make small, coherent changes and preserve unrelated user work.
- Keep implementation design documents, shared libraries, agent-facing
  surfaces, and tests aligned once a behavior spans those layers.
- For local development, use the project-root `.venv` and install the Python
  implementation in editable mode with
  `.venv/bin/python -m pip install -e impls/libs/python` before running its CLI
  or tests. This repository-specific setup belongs here, not in published
  Skills.
- Validate changes in proportion to their scope using the tooling that exists
  at the time of the change.

## Agent-Facing Skill Design

- Write published Skills for an installed product. They must not require the
  agent to read source code, implementation documentation, repository-local
  paths, test commands, or debugging notes in order to use the public surface.
- Separate shared and specialized guidance. Use one foundational or
  orchestrator Skill for the user mental model, shared terminology, common CLI
  grammar, output conventions, safety rules, and routing; keep task-specific
  workflows in specialized Skills.
- Give Skills an explicit, acyclic reading chain. A specialized Skill may
  conditionally direct an unfamiliar agent to the foundational Skill and may
  route to another specialized workflow, but common reference material should
  not be copied into every Skill.
- Define specialized terms before using them in a workflow. For every CLI
  command introduced by a Skill, document its exact invocation, argument form
  and constraints, required and optional inputs, omission/default behavior,
  root-selection behavior, read/write and network effects, dry-run/apply and
  batch behavior where applicable, decision-relevant output fields, and
  actionable failure handling.
- Keep parameter and output descriptions user-facing: explain what the agent
  supplies, observes, and can do next, not how the implementation stores or
  computes the result. Internal architecture, repository development, and
  debugging guidance belong in `impls/docs/` or this file.
- A foundational Skill plus the relevant specialized Skill must be sufficient
  to complete the supported workflow without guessing command syntax or
  consulting implementation documentation.
- Preserve the agent's use of native file, search, shell, editing, and Git
  tools. CLI helpers should add doctidex-specific objective facts rather than
  replace mature general-purpose tools.
- Keep CLI behavior deterministic and non-AI. Agents author and judge semantic
  content; CLIs may validate, format, or report objective structure and state.
- Keep default output bounded and explain pagination, collapse, summary, and
  filtering controls wherever a command can return a collection.
- Validate every changed Skill and its agent metadata, then validate the
  containing plugin.
