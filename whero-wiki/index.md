---
type: Whero Wiki Index
title: Whero Wiki Product Index
description: Routes to the Whero Wiki specification, portable skill, implementation, and validation assets.
whero_maintenance: true
whero_view_required: true
whero_preserved_paths:
  - SKILL.md
  - agents
  - references
  - requirements.txt
  - scripts
  - spec
  - tests
---

# Whero Wiki Product Index

This root is the canonical product workspace and portable skill. Its product
artifacts are preserved from Wiki-framework maintenance and are changed only as
authorized specification, implementation, reference, or test work.

## Skill And Interface

- [Skill instructions](SKILL.md) define the complete agent workflow and route to
  task-specific references.
- [Agent metadata](agents/) provides the OpenAI-facing skill interface.

## Product Contracts

- [Protocol specification](spec/) contains the normative English v0.0.2 contract and
  its synchronized Chinese translations under `spec/CN/`.
- [References](references/) provide current operational workflows for curated
  knowledge, project knowledge, links, external boundaries, Views, and
  historical OKF background.

## Implementation And Validation

- [Scripts](scripts/) implement the active v0.0.2 maintenance, validation, link,
  provenance, boundary, and View workflows.
- [Tests](tests/) cover maintained knowledge, preserved boundaries, links,
  mounts, provenance, project initialization, and View behavior.
- [Python requirements](requirements.txt) declare the portable runtime
  dependencies.

## History

- [Product log](log.md) records meaningful specification, navigation, and
  implementation changes to this root.
