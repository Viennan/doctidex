---
type: API Request Model
title: Thinking Mode Controls
description: DeepSeek thinking-mode controls, parameter effects, output fields, and state rules.
whero_maintenance: true
whero_curated: true
curation_mode: adapted
curation_status: draft
source_documents:
  - path: deepseek/guides/thinking-mode.md
    sha256: e8ba4499edffbc18523da9b17c7c5b0016cc013f07c771d1977fae84262e3bdd
    role: primary
tags: [thinking, reasoning, request-parameters]
timestamp: 2026-07-17
---

# Thinking Mode Controls

DeepSeek thinking mode exposes reasoning before the final answer and changes
both request controls and conversation-state obligations. This concept preserves
the exact control semantics from the [Thinking Mode source](../guides/thinking-mode.md)
while separating them from its long code examples.

## Control Model

| API format | Control | Snapshot behavior |
| --- | --- | --- |
| OpenAI | `thinking.type` | `enabled` or `disabled`; thinking defaults to enabled. |
| OpenAI | `reasoning_effort` | Accepts `high` or `max`; `low` and `medium` map to `high`, while `xhigh` maps to `max`. |
| Anthropic | `output_config.effort` | Uses `high` or `max` for effort control. |

With the OpenAI SDK, place `thinking` in `extra_body`. The source states that
regular thinking requests default to `high`; some complex agent requests may be
set automatically to `max`.

## Parameter Effects

Thinking mode does not support `temperature`, `top_p`, `presence_penalty`, or
`frequency_penalty`. Sending these fields does not produce an error for
compatibility, but they have no effect.

## Output and State

The response returns `reasoning_content` beside `content`. State handling depends
on whether the assistant performed a tool call:

- Without a tool call between user messages, prior `reasoning_content` does not
  need to be included; if included later, the API ignores it.
- After a tool call, the assistant's `reasoning_content` must be passed back in
  subsequent requests. Omitting it causes a 400 response according to the
  source.

See [Conversation and Tool-Call State](conversation-and-tool-call-state.md) for
the complete message-history and tool-loop model.

## Authority Boundary

This concept is a retrieval-oriented adaptation. The
[Thinking Mode source](../guides/thinking-mode.md) remains authoritative for
exact behavior, examples, and snapshot-specific limitations.

