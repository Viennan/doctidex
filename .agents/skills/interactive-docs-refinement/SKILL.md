---
name: interactive-docs-refinement
description: Refine repository Markdown documents through focused questions and user feedback. Use when a Markdown document needs missing information resolved or local user comments incorporated during collaborative editing.
---

# Interactive Docs Refinement

Refine repository Markdown documents through focused questions and user feedback.

## Workflow

1. Identify missing information or an unresolved local concern in the relevant document section.
2. Place a focused `<question>...</question>` block in that section. Incorporate the user's
   `<answer>...</answer>` into the section and remove the resolved question unless the user asks to
   retain it.
3. Treat every user-authored `<comment>...</comment>` block as unresolved local feedback. Address
   its substance in the document; do not merely acknowledge it. Remove the block only after the
   affected content is updated.
4. Preserve unrelated content and do not invent user answers or comments. Keep unresolved blocks
   visible until they are resolved.
