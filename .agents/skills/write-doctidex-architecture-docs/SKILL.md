---
name: write-doctidex-architecture-docs
description: Create, reorganize, revise, or validate current language-neutral Architecture in an artifact's docs architecture directory. Use for common user surfaces, capabilities, key domain and logical models, component dependencies, workflows, observable contracts, structural Architecture replacement, or Architecture cold-read validation; do not use as the authority for Requirement history or a concrete Impls variant.
---

# Write doctidex Architecture Docs

Define the current cross-implementation artifact clearly enough for independent realizations to
preserve the same required capabilities and observable semantics without copying one implementation.

## Establish Authority

1. Read `AGENTS.md` for repository scope and Skill routing.
2. If a corresponding active Requirement must be changed and its Skill is not already loaded, use
   `$write-doctidex-requirement-docs` first, then resume here without reopening this Skill. Do not
   create a Requirement merely because already-current behavior needs documentation.
3. Read the current Architecture, affected public surfaces, applicable Requirements, Impls, code,
   tests, and published Skills as evidence. Read `spec/overview.md` completely before making a
   protocol claim; `spec/refs/` is background, not protocol authority.
4. Keep Architecture language-neutral unless the user explicitly authorizes a language-specific
   design. Public CLI syntax and schemas may be common interfaces; source files, classes, physical
   paths, storage, libraries, and algorithms belong in Impls.

Write documents under `docs/` primarily in Chinese. Preserve precise English terms, identifiers,
schemas, and commands where translation would reduce accuracy.

## Bound the Design with User Surfaces

Lead the Architecture and each supported workflow with:

- the human, agent, or program scenario and concrete problem;
- why the capability exists and which failure it prevents;
- prerequisites, inputs, defaults, permissions, and interface;
- observable results, retained state, failures, and the next decision;
- responsibility, non-responsibility, optional capability, and non-goal boundaries.

Use this surface to decide which common concepts matter. Do not organize the domain model as a
reformatted CLI or JSON field list.

## Define Key Models and Dependencies

Promote a stable concept when it carries user-visible identity, state, or ownership; participates in
several major workflows; governs cross-component collaboration; or defines a safety, compatibility,
or interoperability boundary. For each promoted model, define the properties needed to understand
its identity, state, ownership, relationships, invariants, lifecycle, and failure states.

Do not promote temporary DTOs, parser intermediates, serialization helpers, local aggregates, or
algorithm steps merely because they exist in source. Exact bytes, canonicalization, ordering, parser
behavior, and physical schema belong in Architecture only when they are explicitly public wire,
storage, identity, or interoperability contracts.

Before detailed workflows and interfaces:

1. State directed model and component dependencies.
2. Identify composition and state-ownership boundaries.
3. Prohibit reverse dependencies that would make surfaces or variants redefine the domain.
4. Explain any necessary runtime cycle and which owner breaks the design coupling.

Architecture must define every common concept needed by required workflows, but completeness means
the key design closes. It does not mean reproducing every field, branch, or helper in an existing
implementation.

## Derive Workflows and Contracts

Derive end-to-end flows from the model authorities. For each major workflow, show participant and
subsystem collaboration, inputs, decisions, state transitions, publication semantics, partial
success, concurrency boundary, cancellation, recovery, and observable failure.

Keep exact public schemas and command behavior with their public interface authority. Link back to
the models instead of redefining identities or states in interface pages. Clearly separate
user-visible facts from internal support information.

An Architecture is ready to guide Impls only when every common model, dependency, property, and
transition used by its required workflows is defined consistently and no unresolved active
Requirement changes that authority. Drafting may proceed before that point, but do not claim the
common design is complete.

## Preserve Current and Historical Boundaries

Optimize current Architecture for present correctness and comprehension. Historical Requirements
and archives are provenance, not current structure templates. Do not keep compatibility pages,
duplicate authorities, obsolete terminology, or gaps solely to preserve old links.

Replace an existing Architecture tree structurally only with explicit user authority. Establish the
target tree and unique fact owners before switching navigation and removing superseded pages. Repair
historical links only within the authorized scope; a link replacement is mechanical only when one
unique successor preserves the original meaning. Never retroactively rewrite approved history or
archive content to satisfy current completeness rules.

## Validate Architecture

Check language neutrality, model and dependency closure, user-surface coverage, workflow derivation,
public/internal separation, unique authorities, links, anchors, navigation, diagrams, and whitespace.
When the change affects an Impls variant, use `$write-doctidex-impls-docs` to update or assess its
coverage rather than embedding variant details here.

When Architecture defines an agent-facing Skill surface, make the affected product Architecture own
its audience, reading-chain, command, failure, and maintenance-verification constraints. Link that
product authority instead of copying a generic checklist into this Architecture authoring workflow.

For substantial structural reorganization, use fresh raw-artifact readers:

- Architecture-only: determine whether the key common design can be implemented without Impls or
  source code.
- Architecture plus Impls: determine whether the concrete realization owners, physical state,
  flows, and named evidence can be located without reading source to fill a documentation gap.

Run at most two rounds: the initial reads and one targeted rerun after material repairs. Block only
when a required key model/property, dependency, transition, observable result, safety or
compatibility boundary, or concrete realization owner cannot be determined. Treat byte-level or
platform precision as blocking only for an explicit exact interoperability contract. Keep reports
outside the next reader's raw scope, summarize completed evidence in the active Requirement, and do
not start a third round unless the user explicitly asks.
