---
type: Whero Wiki Log
title: Whero Wiki Product Log
whero_maintenance: true
whero_scope_required: true
---

# Whero Wiki Product Log

## 2026-07-20

- **Initialization**: Established the product directory as a valid self-hosted
  Whero Wiki with root-only framework metadata.
- **Standard**: Added index-declared preserved paths as non-invasive ownership
  boundaries with whole-only disclosure semantics.
- **Implementation**: Added preserved-boundary discovery, validation, maintenance
  protection, partial-view support, CLI reporting, and focused tests.
- **Validation**: Enforced framework document structure and reachable index
  chains, corrected project concept depth, and excluded isolated indexes from
  concept coverage.
- **Provenance**: Added symlink-safe paths, stable maintained-record checks,
  real Git commit verification, rename-aware affected queries, and coverage for
  user-authored references.
- **Links**: Corrected URL query, hostname, Markdown heading, and explicit HTML
  anchor handling.
- **Disclosure**: Rejected selected untracked, ignored, or structurally dirty
  Git content before mutation and removed credentials and URL metadata from
  recorded remotes.
- **Preserved Disclosure**: Clarified that selecting any preserved descendant
  promotes the selection to its preserved root and discloses the boundary whole;
  outer documents may link into preserved content without triggering automatic
  transitive disclosure.
- **Git Content Identity**: Added regular-file blob comparison for committed and
  worktree states. Content changes intersecting disclosed roots now stop before
  mutation and require a user-reviewed repair or rebuild; changes outside the
  disclosed roots and executable-bit-only changes remain acceptable.
- **Disclosure Input Paths**: Separated canonical source-relative POSIX selection
  storage from CLI input syntax. The builder now accepts absolute, home-relative,
  source-relative, working-directory-relative, and selection-list-relative paths
  with `.` or `..`, then validates and normalizes them inside the source boundary.
