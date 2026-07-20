---
type: Whero Wiki
title: Whero Wiki Product
description: Canonical specification, portable skill, tooling, references, and tests for the Whero Wiki model.
format_version: "0.1"
whero_wiki: true
whero_maintenance: true
whero_scope_required: true
---

# Whero Wiki Product

## Scope

This Wiki contains the canonical Whero Wiki specification, portable agent skill,
reference contracts, Python implementation, and tests.

## Organization

The root framework files identify and route the product. Product artifacts are
declared as preserved paths in the root index so Wiki maintenance does not add
framework metadata or perform in-place repairs within them. The host repository
may still modify those artifacts as specification and software changes.

## Operating Constraints

Keep the skill self-contained, resolve bundled resources relative to this root,
and maintain Wiki framework documents only at this directory level.
