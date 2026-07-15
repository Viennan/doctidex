# Your First API Call

The DeepSeek API uses an API format compatible with OpenAI/Anthropic. By modifying the configuration, you can use the OpenAI/Anthropic SDK or softwares compatible with the OpenAI/Anthropic API to access the DeepSeek API.

| PARAM | VALUE |
| --- | --- |
| base\_url (OpenAI) | `https://api.deepseek.com` |
| base\_url (Anthropic) | `https://api.deepseek.com/anthropic` |
| api\_key | apply for an [API key](https://platform.deepseek.com/api_keys) |
| model<sup>\*</sup> | `deepseek-v4-flash`<br>`deepseek-v4-pro`<br>`deepseek-chat` (to be deprecated on 2026/07/24)<br>`deepseek-reasoner` (to be deprecated on 2026/07/24) |

\* The model names `deepseek-chat` and `deepseek-reasoner` will be deprecated on 2026/07/24 15:59 UTC. For compatibility, they correspond to the non-thinking mode and thinking mode of `deepseek-v4-flash`, respectively.

## Integrate with Agent Tools[​](#integrate-with-agent-tools "Direct link to Integrate with Agent Tools")

The DeepSeek API is supported by many popular AI agent and coding assistant tools. If you use tools like Claude Code, GitHub Copilot, or OpenCode, you can use DeepSeek as the backend model directly — no code required.

See the [Agent Integrations Guide](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code) for details.

## Invoke The Chat API[​](#invoke-the-chat-api "Direct link to Invoke The Chat API")

Once you have obtained an API key, you can access the DeepSeek model using the following example scripts in the OpenAI API format. This is a non-stream example, you can set the `stream` parameter to `true` to get stream response.

For examples using the Anthropic API format, please refer to [Anthropic API](https://api-docs.deepseek.com/guides/anthropic_api).

-   curl
-   python
-   nodejs

```
curl https://api.deepseek.com/chat/completions \  -H "Content-Type: application/json" \  -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" \  -d '{        "model": "deepseek-v4-pro",        "messages": [          {"role": "system", "content": "You are a helpful assistant."},          {"role": "user", "content": "Hello!"}        ],        "thinking": {"type": "enabled"},        "reasoning_effort": "high",        "stream": false      }'
```