---
name: user-docs
description: Create and maintain user-facing Markdown documents under docs/user. Use when writing or revising repository documentation for human, agent, or program users.
---

# User Docs

Create and maintain user-facing documents in `docs/user/`.

## Complete Product Perspective

When the current product design is known, organize documentation from that complete design rather
than from the incremental order, numbering, or local structure of Requirements. Requirements are
inputs for recovering facts and design intent, not a template for the final document structure.
Choose an organization that gives users a coherent view of the complete user surface and their
actual usage and decision paths.

## User Surface

1. Start each document or workflow with a concrete user scenario and problem.
2. Explain why the capability exists and which failure or need it addresses.
3. State prerequisites, inputs, defaults, permissions, and interface.
4. Describe expected user behavior and usage patterns with concrete use cases, including but not
   limited to code and command-line examples.
5. Describe observable results, retained state, failures, recovery, and the next decision.
6. Define responsibilities, non-responsibilities, optional capabilities, and non-goals.
7. Organize around the user surface, not a restatement of CLI or JSON fields. Include implementation
   detail only when it changes user-observable behavior.
