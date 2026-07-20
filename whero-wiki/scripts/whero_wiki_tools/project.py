"""Initialize project repositories as Whero Wikis."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from .errors import WheroToolError
from .frontmatter import write_markdown_atomic
from .model import WIKI_META_FILENAME
from .paths import is_within


def init_project_wiki(
    root: Path,
    title: str,
    description: str,
    *,
    agent_guide: Path | None = None,
    dry_run: bool = False,
) -> list[Path]:
    root = root.expanduser().resolve(strict=True)
    planned = [root / WIKI_META_FILENAME, root / "index.md", root / "log.md"]
    if agent_guide is not None:
        guide = agent_guide if agent_guide.is_absolute() else root / agent_guide
        guide = guide.resolve(strict=False)
        if not is_within(guide, root):
            raise WheroToolError(f"agent guide must stay inside the project root: {guide}")
        planned.append(guide)
    collisions = [path for path in planned if os.path.lexists(path)]
    if collisions:
        raise WheroToolError(
            "refusing to overwrite project Wiki files: " + ", ".join(str(path) for path in collisions)
        )
    if dry_run:
        return planned
    meta_fields = {
        "type": "Whero Wiki",
        "title": title,
        "description": description,
        "format_version": "0.1",
        "whero_wiki": True,
        "whero_maintenance": True,
        "whero_scope_required": True,
        "whero_project_wiki": True,
    }
    meta_body = (
        f"\n# {title}\n\n## Scope\n\n{description}\n\n"
        "## Knowledge Maintenance\n\n"
        "Maintain project requirement, design, implementation, user, and "
        "reference knowledge "
        "alongside the code that it explains. Keep these knowledge directories "
        "outside source directories. Use a root `docs/` directory by default, "
        "or a semantically similar name when `docs/` conflicts, and record its "
        "route in the root index. Declare owner-managed trees under "
        "`whero_preserved_paths` when Whero must not maintain their internals and "
        "whole-only disclosure is acceptable.\n"
    )
    index_fields = {
        "type": "Whero Wiki Index",
        "title": title,
        "description": description,
        "whero_maintenance": True,
        "whero_scope_required": True,
        "whero_curated_root": True,
        "whero_curated_format_version": "0.1",
    }
    index_body = (
        f"\n# {title}\n\n{description}\n\n"
        "Create curated knowledge under root `docs/` by default, using "
        "`docs/user`, `docs/requirements`, `docs/design`, "
        "`docs/impl/<language>`, and `docs/references` only when needed. If "
        "`docs/` conflicts, choose a "
        "semantically similar parent such as `knowledge/` and link it here.\n"
        "Use `whero_preserved_paths` in this index or a nearer maintained index "
        "for owner-managed files and directories that must remain non-invasive "
        "and can only be disclosed whole.\n"
    )
    log_fields = {
        "type": "Whero Wiki Log",
        "title": f"{title} Knowledge Log",
        "whero_maintenance": True,
        "whero_scope_required": True,
    }
    log_body = (
        f"\n# {title} Knowledge Log\n\n## {date.today().isoformat()}\n\n"
        "- **Initialization**: Established the project as a Whero Wiki.\n"
    )
    write_markdown_atomic(planned[0], meta_fields, meta_body)
    write_markdown_atomic(planned[1], index_fields, index_body)
    write_markdown_atomic(planned[2], log_fields, log_body)
    if agent_guide is not None:
        planned[-1].parent.mkdir(parents=True, exist_ok=True)
        planned[-1].write_text(PROJECT_AGENT_GUIDE, encoding="utf-8")
    return planned


PROJECT_AGENT_GUIDE = """# Whero Wiki Project Maintenance

Treat this project as a Whero Wiki. Maintain requirement, design,
implementation, user, and reference knowledge as part of normal development
rather than as a later cleanup task.

Keep curated knowledge under root `docs/` by default, outside source directories,
and link its roots from the root `index.md`. If `docs/` conflicts, use another
semantically similar, user-approved parent. This development layout is distinct
from non-invasive analysis of a third-party repository; that analysis may use
any concept organization.

- Record materially changed needs and their useful decision history in
  `docs/requirements`; label superseded, rejected, and version-bound statements.
- Keep only history that explains constraints, tradeoffs, reversals,
  compatibility obligations, or likely future decisions. Remove obsolete
  speculation that would mislead retrieval.
- Normalize current why and what into design concepts before or with
  direction-changing code, linking requirement history when useful.
- Update implementation concepts with code entry points, responsibilities, and
  call relationships when implementation changes.
- Explain every field in documented records, schemas, configs, DTOs, and events.
- Inspect existing directory names before using `docs/`; choose a semantically
  similar parent such as `knowledge/` when it conflicts.
- Ask the user for missing intent, requirement history, and design history when
  adapting an existing project; do not infer design decisions from code alone.
- Preserve external references and mounted Whero Wikis under their own ownership
  boundaries.
- Declare owner-managed source, generated, or legacy paths under
  `whero_preserved_paths` when Whero must not write inside them and whole-only
  disclosure is acceptable. Use a mount when inner partial disclosure is needed.
- Before completing a change, inspect `git diff --name-status`, run the Whero
  affected-concept query, validate the Wiki, and run `git diff --check`.
"""
