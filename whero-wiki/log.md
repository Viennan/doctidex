---
type: Whero Wiki Log
title: Whero Wiki Product Log
whero_maintenance: true
whero_view_required: true
---

# Whero Wiki Product Log

## 2026-07-21

- **v0.0.2 Baseline**: Unified Wiki creation, framework metadata, validation,
  links, Views, curated collections, preserved patterns, external-reference
  declarations, and restoration planning under version `0.0.2`.
- **Runtime Surface**: Reduced identity, View state, validation profiles, link
  handling, and public entry points to one current contract.
- **Test Suite**: Replaced history-layered coverage with 79 current-contract
  tests organized around identity, Views, links, boundaries, project
  provenance, and bundle consistency.
- **View Runtime**: Replaced delegated child Views with immediate-source links,
  automatic whole-Mount and source-symlink promotion, View-of-View availability
  enforcement, caller-friendly source inference, and explicit restoration.
- **Protocol**: Established terminology-led contracts for the Wiki model,
  external references, Views, preserved boundaries, links, and conformance.
- **Translation**: Added synchronized Chinese protocol documents under
  `spec/CN/` and made paired protocol maintenance a repository rule.
- **Skill**: Reduced the portable skill to operational workflows and explicit
  routing, while keeping draft protocol details in selectively loaded files.
- **References**: Split the combined links, mounts, preserved paths, and
  projection reference into focused link, external-reference, and View
  workflow guides.
- **View Architecture**: Split the View builder into request, source, Git
  identity, planning, status, execution, service, and CLI modules with
  structured plans and results.
- **View Protocol Simplification**: Made every path reachable in the immediate
  source a legal selection, with automatic whole-boundary promotion. Replaced
  delegated child Views with relative links to immediate-source path entries,
  prohibited resolving through source symlinks, and limited View-of-View
  expansion to material already available in the source View.

## 2026-07-20

- **Initialization**: Established the product directory as a valid self-hosted
  Whero Wiki with root-only framework metadata.
- **Standard**: Added index-declared preserved paths as non-invasive ownership
  boundaries with whole-only disclosure semantics.
- **Implementation**: Added preserved-boundary discovery, validation, maintenance
  protection, View-profile support, CLI reporting, and focused tests.
- **Validation**: Enforced framework document structure and reachable index
  chains, corrected project concept depth, and excluded isolated indexes from
  concept coverage.
- **Provenance**: Added symlink-safe paths, stable maintained-record checks,
  real Git commit verification, rename-aware affected queries, and coverage for
  user-authored references.
- **Links**: Corrected URL query, hostname, Markdown heading, and explicit HTML
  anchor handling.
- **View Preflight**: Rejected selected untracked, ignored, or structurally dirty
  Git content before mutation and removed credentials and URL metadata from
  recorded remotes.
- **Preserved Views**: Clarified that selecting any preserved descendant
  promotes the selection to its preserved root and discloses the boundary whole;
  outer documents may link into preserved content without triggering automatic
  transitive disclosure.
- **Git Content Identity**: Added regular-file blob comparison for committed and
  worktree states. Content changes intersecting disclosed roots now stop before
  mutation and require a user-reviewed repair or rebuild; changes outside the
  disclosed roots and executable-bit-only changes remain acceptable.
- **View Input Paths**: Separated canonical source-relative POSIX selection
  storage from CLI input syntax. The builder now accepts absolute, home-relative,
  source-relative, working-directory-relative, and selection-list-relative paths
  with `.` or `..`, then validates and normalizes them inside the source boundary.
