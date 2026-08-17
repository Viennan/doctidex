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

Write documents under `docs/` with Chinese carrying the heading, prose, and table logic. Preserve
precise English terms, identifiers, schemas, commands, paths, code symbols, and quotations where
translation would reduce accuracy, but do not leave a long English-only explanatory passage behind
a Chinese heading or lead-in.

## Bound the Design with User Surfaces

Lead the Architecture and each supported workflow with:

- the human, agent, or program scenario and concrete problem;
- why the capability exists and which failure it prevents;
- prerequisites, inputs, defaults, permissions, and interface;
- observable results, retained state, failures, and the next decision;
- responsibility, non-responsibility, optional capability, and non-goal boundaries.

Use this surface to decide which common concepts matter. Do not organize the domain model as a
reformatted CLI or JSON field list.

## Define a Handoff-Complete Worksite

Treat a user-surface worksite as a cross-variant product contract. For every semantically distinct
state a supported variant can leave behind, Architecture must let another variant identify and
correctly handle every configuration file, materialized option/state, and artifact present in the
selected root, host repository, managed paths, and any operation-exposed cache/diagnostic location.

For each such object, define or directly route to its identity, owner, presence condition, producer,
consumer, use, lifecycle, observable effect, failure/recovery boundary, and one of these handoff
outcomes: direct read/write, conversion, preservation, or safe rejection. A configuration field can
remain an opaque matching value only when its meaning and safe incoming treatment are still explicit.
Do not call an unexplained configuration file an opaque internal artifact.

Architecture needs strong, direct evidence for these claims: a reader must be able to cite a page
that expressly defines the matching file, option, artifact, or behavior. Names, loose implication,
several unrelated fragments, and a link to Impls/source are not direct Architecture authority.

Completeness has a deliberate upper bound. Define the semantics required to correctly implement the
user surface: inputs/defaults, configuration/artifact effects, results, failures, recovery, handoff,
compatibility, and safety. Do not promote a local algorithm, call graph, lock primitive, cache/temp
layout, module boundary, parser detail, byte ordering, or optimization when it does not change those
behaviors. Such mechanics belong to Impls/source evidence.

## Define Key Models and Dependencies

Promote a stable concept when it carries user-visible identity, state, or ownership; participates in
several major workflows; governs cross-component collaboration; or defines a safety, compatibility,
or interoperability boundary. For each promoted model, define the properties needed to understand
its identity, state, ownership, relationships, invariants, lifecycle, and failure states.

Do not promote temporary DTOs, parser intermediates, serialization helpers, local aggregates, or
algorithm steps merely because they exist in source. Exact bytes, canonicalization, ordering, parser
behavior, and physical schema belong in Architecture only when they are explicitly public wire,
storage, identity, or interoperability contracts. Conversely, promote a concept or the minimum
semantics it carries whenever an Architecture-only reader needs it to identify, explain, use,
transition, recover, or safely hand off a materialized worksite object. Current single-variant
status is not a reason to keep such a concept private.

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

Check language neutrality, Chinese logical organization of explanatory prose, model and dependency
closure, user-surface coverage, workflow derivation, public/internal separation, unique authorities,
links, anchors, navigation, diagrams, and whitespace. English-only prose is not acceptable merely
because a page title or surrounding labels are Chinese; retain English only where it is a precise
term, literal, symbol, command, path, schema, or quotation.
When the change affects an Impls variant, use `$write-doctidex-impls-docs` to update or assess its
coverage rather than embedding variant details here.

When Architecture defines an agent-facing Skill surface, make the affected product Architecture own
its audience, reading-chain, command, failure, and maintenance-verification constraints. Link that
product authority instead of copying a generic checklist into this Architecture authoring workflow.

For substantial structural reorganization or a change to materialized worksite/handoff semantics,
construct isolated fixtures for every semantically distinct user-surface worksite a current variant
can produce or retain. Include normal, partial-success, blocked, recovery, migration/compatibility,
damaged, hidden, and interruption states when they leave different files/options/artifacts or
observable effects. Equivalent scenarios may merge only with Impls/source/test evidence that all of
those facts are equal. Do not use a few happy paths as state coverage. Fixtures must expose actual
selected-root, host, managed-path, cache, and other relevant locations without user credentials.

Use two independent fresh readers:

- Architecture-only reader: receives only the raw fixture worksite, its user-visible transcript and
  current Architecture. It recursively inventories actual files/artifacts, explains every present
  configuration file and materialized option plus every artifact's producer/consumer/use/lifecycle,
  and cites strong direct Architecture evidence. It must not read Impls, source, tests, Requirements,
  fixture-construction records, or earlier reports.
- Full-knowledge verifier: independently reads applicable Requirements, Architecture, all Impls,
  source, tests, public surfaces, fixture construction and the reader result. It confirms the cited
  evidence actually supports each conclusion, rejects invention/strained inference, and checks that
  the understanding suffices for correct user-surface behavior. It must not use its own knowledge to
  fill an Architecture-only gap.

Run at most two paired rounds: the initial read and one targeted rerun after material repairs. Block
only when a required model/property, materialized configuration/artifact meaning, dependency,
transition, observable result, safety/compatibility/handoff boundary, or concrete realization owner
cannot be determined. Missing reproduction of source internals is not a gap by itself. Treat
byte-level or platform precision as blocking only for an explicit exact interoperability contract.
Keep reports outside the next reader's raw scope, summarize completed evidence in the active
Requirement, and do not start a third round unless the user explicitly asks.
