---
type: API Caching Model
title: Context Cache Semantics
description: DeepSeek prefix-cache construction, hit rules, usage reporting, and its separation from conversation state.
whero_maintenance: true
whero_curated: true
curation_mode: adapted
curation_status: draft
source_documents:
  - path: deepseek/guides/context-caching.md
    sha256: 6de6030d886added9ba14ab0f9ca1bb1220bc014ae9399e468df81b37ffc0fbe
    role: primary
tags: [cache, context, tokens, conversation]
timestamp: 2026-07-17
---

# Context Cache Semantics

DeepSeek's disk context cache is enabled by default and can reuse matching input
prefixes. It optimizes repeated computation; it does not replace the client's
responsibility to resend conversation history described in
[Conversation and Tool-Call State](conversation-and-tool-call-state.md).

## Prefix Units

A request can hit the cache only by fully matching a persisted cache prefix
unit. The [Context Caching source](../guides/context-caching.md) describes three
ways units are persisted:

1. At the end of user input and at the end of model output for each request.
2. When the system detects a common prefix across multiple requests.
3. At fixed token intervals for long input or output.

Partial overlap with a previously persisted unit is not itself a hit. A later
request may hit a shorter common-prefix unit after the system detects and
persists that common prefix.

## Observability

The response `usage` object exposes:

- `prompt_cache_hit_tokens` for input tokens served through a cache hit;
- `prompt_cache_miss_tokens` for input tokens that missed the cache.

## Operational Limits

- Cache matching applies to the input prefix. Output is still generated and can
  remain random.
- Cache behavior is best effort and does not guarantee a hit.
- Cache construction takes seconds.
- Unused cache data is normally cleared after a period ranging from hours to
  days in this snapshot.

## Authority Boundary

This document removes example repetition but retains the source's cache model.
Use the [Context Caching source](../guides/context-caching.md) for its full worked
examples and exact snapshot wording.

