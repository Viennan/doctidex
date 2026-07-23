---
type: Conversation State Model
title: Conversation and Tool-Call State
description: Client-managed history and state obligations across ordinary, tool-calling, and thinking turns.
whero_maintenance: true
whero_curated: true
curation_mode: synthesized
curation_status: draft
source_documents:
  - path: deepseek/guides/multi-round-conversation.md
    sha256: 00de937b09319d2de3ead9df8bcdd5666703a5e6f0349b67ca895b50fa688d84
    role: primary
  - path: deepseek/guides/thinking-mode.md
    sha256: e8ba4499edffbc18523da9b17c7c5b0016cc013f07c771d1977fae84262e3bdd
    role: supporting
  - path: deepseek/guides/tool-calls.md
    sha256: 113bced6bd862c7db118bd098fa67ef295c920a668d16c4723d5d0869fa3f134
    role: supporting
tags: [conversation, tools, reasoning, state]
timestamp: 2026-07-17
---

# Conversation and Tool-Call State

DeepSeek `/chat/completions` is stateless: the server does not retain prior
conversation context for the next request. The client reconstructs context by
sending the relevant message history on every turn, as shown in the
[Multi-round Conversation source](../guides/multi-round-conversation.md).

## Ordinary Conversation

For a normal multi-round exchange:

1. Send the current `messages` list.
2. Append the returned assistant message.
3. Append the next user message.
4. Send the resulting history with the next request.

This client-managed state is independent of server-side prefix caching. See
[Context Cache Semantics](context-cache-semantics.md).

## Tool-Call Loop

The model proposes tool calls but does not execute the tools. The client must:

1. Append the assistant message containing `tool_calls`.
2. Execute each requested function externally.
3. Append a `tool` message with the matching `tool_call_id` and result.
4. Send the expanded history to the model and repeat until no tool call remains.

The [Tool Calls source](../guides/tool-calls.md) recommends appending the complete
SDK assistant message because it already carries `content`, `reasoning_content`,
and `tool_calls` when those fields are present.

## Thinking-State Branch

[Thinking Mode Controls](thinking-mode-controls.md) defines an additional state
branch:

- If no tool call occurred between user messages, earlier `reasoning_content`
  may be omitted and is ignored if resent.
- If a tool call occurred, preserve the assistant's `reasoning_content` with the
  tool-call message in all subsequent requests. The source documents a 400 error
  when this requirement is violated.

## Strict Function Schemas

The snapshot's beta strict mode uses `https://api.deepseek.com/beta`, requires
`strict: true` on every function, and validates the supplied JSON Schema. For
every object, all properties must be listed in `required` and
`additionalProperties` must be `false`. The supported and unsupported schema
keywords vary by type; use the [Tool Calls source](../guides/tool-calls.md) for
the exact snapshot matrix rather than generalizing from standard JSON Schema.

## Authority Boundary

This concept synthesizes state rules that are separated across three sources.
Those collected sources remain authoritative if any wording here is incomplete
or conflicts with exact request behavior.

