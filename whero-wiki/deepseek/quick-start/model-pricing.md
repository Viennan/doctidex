# Models & Pricing

The prices listed below are in units of per 1M tokens. A token, the smallest unit of text that the model recognizes, can be a word, a number, or even a punctuation mark. We will bill based on the total number of input and output tokens by the model.

---

## Model Details[​](#model-details "Direct link to Model Details")

**

| Column 1 | Column 2 | Column 3 | Column 4 |
| --- | --- | --- | --- |
| MODEL |  | deepseek-v4-flash<sup>(1)</sup> | deepseek-v4-pro |
| BASE URL (OpenAI Format) |  | [https://api.deepseek.com](https://api.deepseek.com) |  |
| BASE URL (Anthropic Format) |  | [https://api.deepseek.com/anthropic](https://api.deepseek.com/anthropic) |  |
| MODEL VERSION |  | DeepSeek-V4-Flash | DeepSeek-V4-Pro |
| THINKING MODE |  | Supports both non-thinking and thinking (default) modes<br>See [Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode) for how to switch |  |
| CONTEXT LENGTH |  | 1M |  |
| MAX OUTPUT |  | MAXIMUM: 384K |  |
| FEATURES | [Json Output](https://api-docs.deepseek.com/guides/json_mode) | ✓ | ✓ |
| FEATURES | [Tool Calls](https://api-docs.deepseek.com/guides/tool_calls) | ✓ | ✓ |
| FEATURES | [Chat Prefix Completion（Beta）](https://api-docs.deepseek.com/guides/chat_prefix_completion) | ✓ | ✓ |
| FEATURES | [FIM Completion（Beta）](https://api-docs.deepseek.com/guides/fim_completion) | Non-thinking mode only | Non-thinking mode only |
| PRICING | 1M INPUT TOKENS (CACHE HIT) | $0.0028 | $0.003625 |
| PRICING | 1M INPUT TOKENS (CACHE MISS) | $0.14 | $0.435 |
| PRICING | 1M OUTPUT TOKENS | $0.28 | $0.87 |
| Concurrency Limit<sup>(2)</sup> |  | 2500 | 500 |

**

(1) The model names `deepseek-chat` and `deepseek-reasoner` will be deprecated on 2026/07/24 15:59 UTC. For compatibility, they correspond to the non-thinking mode and thinking mode of `deepseek-v4-flash`, respectively.  
(2) For more details on concurrency limits, please refer to [Rate Limit & Isolation](https://api-docs.deepseek.com/quick_start/rate_limit)

---

## Deduction Rules[​](#deduction-rules "Direct link to Deduction Rules")

The expense = number of tokens × price. The corresponding fees will be directly deducted from your topped-up balance or granted balance, with a preference for using the granted balance first when both balances are available.

Product prices may vary and DeepSeek reserves the right to adjust them. We recommend topping up based on your actual usage and regularly checking this page for the most recent pricing information.