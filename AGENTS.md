# Repository Guide

## Project Scope

`doctidex` is an emerging directory-tree structure standard for agents and humans. Its current
design goals are interoperability, extensibility, and minimal format constraints.

## Repository Layout

- `spec/overview.md` contains the draft normative protocol; `spec/refs/` is background material.
- `docs/` contains non-normative current design and project-wide Requirement history.
- `docs/requirements/` contains numbered Requirements. A user-selected large Requirement uses one
  numbered directory with an `overview.md` and independently statused children.
- `docs/<artifact>/architecture/` defines current cross-implementation design;
  `docs/<artifact>/impls/<variant>/` defines a condition-specific realization.
- `docs/doctidex-git/` documents the Git plugin using that Architecture/Impls structure.
- `impls/` contains implementations, shared libraries, and public agent surfaces.
- `impls/libs/python/` contains the Python implementation.
- `impls/agent-plugins/doctidex-git/` contains the published Git plugin and its installed-product
  Skills.
- `.agents/skills/` contains repository-local maintenance Skills. They may read repository design,
  source, and tests and are not published user surfaces.
- `.asserts/` is read-only collected source material. `.tmp/` is disposable and ignored by Git.

## Repository Doctidex Organization

- Maintain this repository as a doctidex tree under `spec/overview.md`. Indexes describe the working
  source/documentation tree; they do not recreate another documentation system.
- Keep source, tool/configuration, generated, vendored, fixture, asset, collected-source, and other
  unsuitable directories atomic. A responsible parent states their purpose without recursively
  indexing internal files.
- Reuse authoritative navigation already present under `docs/` and elsewhere. Higher indexes link
  to that authority instead of duplicating its structure or prose.
- Atomic reduces index depth but does not hide purpose or content. Apply it only where the protocol
  permits: an atomic directory cannot contain `index.md` or `log.md`, and an existing doctidex index
  hierarchy remains non-atomic.

## Sources of Context

- `spec/overview.md` alone defines protocol requirements. Read it completely before making a
  protocol claim.
- `docs/` may impose stricter non-normative implementation conventions.
- `spec/refs/` is background, and `.asserts/` is read-only test source material.

## Working Rules

- Keep proposals, current design, accepted specification, and implemented behavior visibly
  distinct.
- Do not force Markdown line breaks merely to satisfy a per-line character limit when doing so
  harms rendering or structure; in particular, keep each heading on one line.
- Keep `spec/` normative, `docs/` focused on non-normative design and Requirement history, and
  `impls/` focused on code and agent-facing products.
- Do not turn placeholders such as "refer to OKF" into detailed requirements without an explicit
  design decision.
- Preserve unrelated user work and keep changes coherent with the user-authorized scope.
- Align design, implementation, tests, and public surfaces when behavior spans those layers.
- Use the project-root `.venv`; install the Python implementation for local development with
  `.venv/bin/python -m pip install -e impls/libs/python` before running its CLI or tests.
- Validate changes in proportion to their scope with current repository tooling.

## Documentation Authority and Routing

Documents under `docs/` are primarily Chinese. Use established English for identifiers, schemas,
commands, and technical terms when it is more precise. This language rule does not apply outside
`docs/`.

Each document type has one repository-local authoring authority:

| Document | Current authority | Use when |
|---|---|---|
| Requirement | `.agents/skills/write-doctidex-requirement-docs/` | Recording intent, refining an active Requirement, handling user feedback, status, dependencies, approval, or implementation tracking. |
| Architecture | `.agents/skills/write-doctidex-architecture-docs/` | Defining current language-neutral user surfaces, common capabilities, key models, mechanisms, policies, workflows, and observable contracts. |
| Impls | `.agents/skills/write-doctidex-impls-docs/` | Defining a language/runtime/platform realization, physical design, code ownership, evidence, coverage, and material limitations. |

Use this order when work spans layers:

1. If the user intends to create or record a Requirement, use the Requirement Skill immediately.
2. If a requested artifact change belongs to a corresponding active Requirement, update that
   Requirement before editing the artifact.
3. Update Architecture before Impls when common design changes; update only Impls for a purely
   variant-specific change.
4. Align other authorized implementation, test, or public surfaces, validate, and return to the
   Requirement lifecycle.

Do not create a Requirement merely to document already-current behavior when there is no recording
intent or corresponding active record. Keep one authoritative explanation per fact and cross-link
Architecture, Impls, and Requirements where the relationship aids traceability.

Prioritize coherent current Architecture and Impls over historical page compatibility. Requirements
and archives preserve provenance rather than current structure. Structural replacement and
historical link repair require the authority defined by the applicable authoring Skill.

## Repository Maintenance Skills

- Use `.agents/skills/review-doctidex-repository/` only when the user explicitly authorizes a review,
  audit, compliance check, or review-and-repair cycle. The review Skill owns scope, independent
  lenses, finding adjudication, repair authorization, and re-review.
- Use `.agents/skills/write-doctidex-agent-skills/` for published or repository-local Skill content,
  metadata, reading chains, command contracts, and validation. Preserve its published-product versus
  repository-maintenance audience boundary.
- Let each maintenance Skill own its detailed rules. `AGENTS.md` selects and orders Skills; it does
  not duplicate their authoring or review checklists.
