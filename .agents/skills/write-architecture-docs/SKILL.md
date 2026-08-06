---
name: write-architecture-docs
description: Write and validate complete product Architecture documents under docs/architecture. Use when defining or revising product purpose, mental models, domain and public data models, core workflows, design constraints, or internal architecture.
---

# Write Architecture Docs

Write and validate the complete current product Architecture under `docs/architecture/`.

## Architecture Scope

Architecture is the product's complete design authority. It must define:

- purpose, scope, actors, and mental models;
- domain models and all public data models, including configuration, options, artifacts, and other
  user-visible state;
- semantic and implementation design constraints;
- internal architecture, responsibilities, dependencies, and ownership; and
- every core workflow that uses the defined models.

Use DDD patterns as a source of core principles for organizing internal architecture, not as a
formal structure to apply mechanically.

## Model and Field Completeness

Document every domain and public data model. For every field, explain its meaning, role and
responsibility in related workflows, model position, lifecycle or presence, and applicable design
constraints. Do not describe only request and response fields or rely on names and schemas without
explanation.

## Workflow Completeness

Describe every core workflow, including each workflow that participates in or changes a defined
model. Cover actors and components, inputs, decisions, state transitions, outputs, observable
effects, failures, and recovery. Prefer sequence diagrams for temporal or multi-party flows.

## Design Constraints and Implementation Links

Record both semantic constraints and implementation constraints, including required design patterns,
libraries, references, or code patterns when they constrain the product. Link each architecture
topic to its corresponding implementation documentation, including code and non-code artifacts.
Architecture may define the design directly or route to an authoritative implementation document;
links must let an agent recover the product's complete current design and implementation knowledge.

## Validation

Before handoff, check product purpose, mental model, model and field coverage, workflow coverage,
constraint completeness, diagram accuracy, implementation links, ownership, and consistency with
current repository artifacts. Do not claim completeness while a required model, workflow,
constraint, or implementation link is missing.
