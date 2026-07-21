# Link Workflows

This guide covers active link tooling. The normative contract is in
[Links](../spec/links.md).

## Inspect Links

Use the bundled CLI instead of adding backlink sections to documents:

```bash
<python> <skill-directory>/scripts/whero_wiki.py links list --wiki <root>
<python> <skill-directory>/scripts/whero_wiki.py links inbound \
  --wiki <root> --target <path>
<python> <skill-directory>/scripts/whero_wiki.py links broken --wiki <root>
<python> <skill-directory>/scripts/whero_wiki.py links graph \
  --wiki <root> --format json
```

The parser ignores fenced and inline code and supports inline, image, and
reference-style Markdown links. Reports distinguish external, resolved,
unavailable, missing, invalid boundary-crossing, and missing-anchor states.
Queries do not become part of local filesystem paths. Anchor validation uses
parsed Markdown headings and explicit HTML `id` or anchor `name` attributes.

Use `--mode auto` by default. It detects `whero-wiki-view.md`. Use `--mode
full` or `--mode view` only to override detection.

## Write Links

Write maintained internal links as standard relative Markdown links computed
from the document being written. Callers may supply more convenient Wiki-root-
relative or filesystem paths to tools, but stored destinations stay relative.

During authorized collected-source localization, rewrite only a confidently
resolved destination or append the exact marker
`<!-- whero:unresolved-local-link -->`.

## Views And Boundaries

Inspect source-relative logical paths in a View instead of resolving directory
symlinks to ultimate-source paths. A link may legitimately target undisclosed
content; report it as unavailable. Link scanning stops at preserved paths,
nested Wikis, Views, and submodules unless a task explicitly enters that
ownership boundary.
