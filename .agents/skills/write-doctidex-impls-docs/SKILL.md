---
name: write-doctidex-impls-docs
description: Create, reorganize, revise, or validate a condition-specific realization in an artifact's docs Impls directory. Use for variant installation and integration, Architecture coverage, components, physical data, code ownership, algorithms, side effects, concurrency, recovery, platform choices, source/test evidence, or material implementation limitations; do not use to redefine common Architecture or Requirement history.
---

# Write doctidex Impls Docs

Explain how one language, runtime, platform, or deployment variant realizes the current Architecture
without turning the document into either a thin code map or a line-by-line source transcription.

## Establish Authority

1. Read `AGENTS.md` for repository scope and Skill routing.
2. If a corresponding active Requirement must change and its Skill is not already loaded, use
   `$write-doctidex-requirement-docs` first, then resume here without reopening this Skill.
3. Read the complete applicable Architecture before treating a capability as required or optional,
   including its worksite/handoff authority when the variant can materialize configuration or
   artifacts.
4. Verify realization claims against the variant's source, tests, packaging, public interfaces, and
   published Skills. Current code is evidence for implementation fact; it cannot silently override
   Architecture.

Write documents under `docs/` with Chinese carrying the heading, prose, and table logic while
preserving exact identifiers, symbols, schemas, commands, paths, established technical terms, and
quotations. Do not leave a long English-only explanatory passage behind a Chinese heading or lead-in.

## State Applicability and User Surface

Start the variant with its language/runtime/platform/deployment conditions, version, prerequisites,
supported Architecture, installation and integration paths, and material limitations.

Define how human, agent, and program users access this variant: entry points, inputs, defaults,
effects, observable results, failures, and next actions. Link common semantics to Architecture and
describe only variant-specific setup, calls, examples, and operating boundaries locally. Do not
duplicate published Skill tutorials.

For every materialized user-surface worksite, create one variant inventory/construction authority.
It must enumerate actual configuration files, every materializable option/state, artifacts, selected
root/host/managed/cache/diagnostic locations, producer/consumer/use/lifecycle, physical
representation, source/test evidence, and the direct Architecture authority for shared semantics.
It must also define isolated fixture construction and a scenario matrix covering all semantically
distinct retained states; only evidence-backed equivalent scenarios may merge. Do not let component
pages independently redefine the same physical inventory.

## Explain the Realization

Organize around stable implementation responsibilities rather than mirroring every source file.
Cover the significant realization of each Architecture model and workflow:

- concrete components, callers, dependencies, and state owners;
- physical data and storage, serialization, libraries, algorithms, and platform choices;
- end-to-end control and data flows, subprocess or network effects, and publication order;
- failure translation, partial success, concurrency, cancellation, recovery, and cleanup;
- code ownership and representative source and test evidence.

For each worksite object, distinguish explicitly between a common contract that the variant realizes,
a variant choice that Architecture leaves open, a private mechanic that cannot affect correct
user-surface implementation or handoff, and a material limitation. If a current file/option/artifact
cannot be explained from Architecture, route the missing semantic definition back to Architecture;
do not label it private merely because Python/source currently owns its bytes.

For a major module or equivalent ownership unit, explain its purpose, intended callers, important
types and entry points, owned state, effects, and failure/concurrency boundary. Link directly to
source symbols or tests for helper attributes, temporary models, parser details, and local
algorithms that are self-explanatory. Do not require a separate documentation row for every module,
private function, field, branch, or intermediate object.

Use compact examples only when they reduce rediscovery. A code map is evidence, not a substitute for
the realization design.

## Maintain Architecture Coverage

Map every required Architecture capability to its variant user entry, main implementation support,
materialized worksite inventory row when applicable, and representative evidence. Keep the matrix at
the level of key models and major workflows; avoid turning internal differences into product
requirements.

Classify a difference before calling it a gap:

- Document a variant choice when Architecture intentionally leaves the mechanism open.
- Correct Architecture or Impls when the documents misclassify current common or concrete behavior.
- Record a material limitation only when a required capability or observable semantic is missing,
  or when a major mechanism, safety/compatibility boundary, or explicit interoperability contract
  is violated.

A missing optional capability is valid only when Architecture marks it optional. A missing required
capability blocks a Requirement that introduces, changes, or claims that realization. A
documentation-only Requirement may still complete when it accurately exposes a pre-existing,
out-of-scope implementation gap and makes no false completeness claim; record the concrete public
contract/source/test difference in the active Requirement and leave product repair to a separate
authorized Requirement.

Impls must not supply a missing common definition back into Architecture. If its Skill is not
already loaded, use `$write-doctidex-architecture-docs` when a stable concept or behavior belongs
across variants, then resume here without reopening this Skill.

## Preserve Boundaries and Validate

Optimize current Impls for present correctness. Do not retain obsolete Details terminology,
compatibility pages, duplicate authorities, or weak code lists to accommodate historical paths.
Replace a current Impls tree structurally only with explicit user authority, and repair historical
links only when the authorized successor is unambiguous.

Validate applicability, user surface, Architecture coverage, component and physical-state design,
source/test targets, limitations, links, anchors, navigation, whitespace, and Chinese logical
organization of explanatory prose. English-only prose is not acceptable merely because a page title
or surrounding labels are Chinese; retain English only where it is a precise term, literal, symbol,
command, path, schema, or quotation. Run relevant tests and static checks in proportion to the
changed realization claims. For a substantial Architecture and Impls reorganization, construct the
worksite fixtures and evidence matrix here, then follow the bounded Architecture-only reader plus
full-knowledge verifier contract in `$write-doctidex-architecture-docs`; do not start an extra
cold-read cycle from this Skill. The verifier evaluates whether reader understanding is sufficient
to implement user-surface behavior, not whether it recreated every source algorithm, lock, call
path, byte layout, or helper.
