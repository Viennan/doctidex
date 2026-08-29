# Issue Note: Prefilter Markdown link scanning with ripgrep

Status: implemented

## Problem

`scan_markdown_links` was the only Markdown link scan interface. It walked the selected scope with `os.walk`, read
every `.md` file through Python file I/O, parsed every file with `markdown-it-py`, and returned every local link with
its resolved target and boundary association. For large repositories this paid the full file-read and Markdown-parse
cost even though the callers only needed links that cross a BoundaryPoint.

## Decision

`markdown_links.py` now exposes `scan_cross_boundary_links` instead of `scan_markdown_links`. The in-scope document
definition is unchanged: `.md` files under `scope`, excluding `.doctidex-git` and descendants of a BoundaryPoint.

When `rg` with PCRE2 support is available, the scanner uses a ripgrep candidate prefilter before precise parsing:

- `rg` discovers raw inline-link destinations and reference-definition destinations using multiline PCRE2 patterns.
- The invocation searches hidden and ignored files, restricts to Markdown files, and excludes `.doctidex-git` and
  BoundaryPoint descendants.
- The candidate stream is parsed from `rg --json` output without materializing the whole corpus.
- `_coarse_classify` classifies each raw destination as `target`, `outside-repository`, or `unresolved`. Documents
  with a boundary-crossing or unresolved candidate are selected for precise parsing; root-escaping and external
  candidates are excluded.

The precise pass reads only selected documents and reuses the existing `markdown-it-py` logic. It returns the exact
`MarkdownLink` fields for local links whose resolved target crosses a BoundaryPoint. Deterministic order is preserved
by sorting the selected document paths before precise parsing.

When `rg` is missing, lacks PCRE2 support, or fails during candidate discovery, the scanner falls back to the current
`os.walk` plus per-file `read_text` scan and applies the same cross-boundary filter. The fallback preserves correctness
and result shape with the old performance cost.

`model_view.py` re-exports `scan_cross_boundary_links`. `import unref` and installation removal use it for their
existing blocking checks. `validate` uses it for cross-boundary content diagnostics and no longer emits ordinary
local-link path or target-existence diagnostics.

## Testing

`src/python/tests/test_markdown_link_scan.py` covers the coarse classifier, ripgrep discovery of parenthesized and
multiline destinations, reference-definition links, root-escaping and external candidates, missing-rg fallback, parity
between ripgrep and fallback paths, and a synthetic large tree proving that non-candidate documents are not read by
the precise pass.

The full suite passes. Coverage is 87%. `ruff check src/python/whero/doctidex src/python/tests` and `git diff --check`
pass.

## Consequences

Large repositories avoid Python read and Markdown-parse work for ordinary non-boundary documents when `rg` is
available. The trade-off is a strongly recommended `rg` dependency rather than a hard requirement; without it,
behavior remains correct but retains the previous scan cost.

The prefilter is allowed to over-approximate. It can include extra documents for precise parsing, but it must not
drop a boundary-crossing link. Unresolved candidates keep their document in the precise set, while root-escaping and
external destinations are classified outside the repository and skipped.

`validate` no longer reports `link.path.conforms`, and `link.target.exists` now applies only to cross-boundary links.
This is documented in the user-facing validation reference. The user guide lists `rg` with PCRE2 as a strongly
recommended prerequisite and describes the per-file fallback.

## Alternatives considered

**Keep the current scanner and optimize only Python I/O.**
Rejected: it still parses and returns every link, so it retains the unnecessary Markdown-parse and all-link surface
for large repositories.

**Use ripgrep as the final Markdown parser.**
Rejected: a regular expression cannot reliably implement Markdown link parsing, including multiline labels,
parenthesized destinations, escapes, and reference forms. The existing parser remains the source of truth.

**Add a cross-boundary API while preserving the all-link API for `validate`.**
Rejected: this keeps two scanning paths and still pays full scanning cost on normal `validate` runs. The implementation
removes the unused ordinary-link diagnostics instead.
