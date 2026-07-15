# Anthropic API

To meet the demand for using the Anthropic API ecosystem, our API has added support for the Anthropic API format, with the `base_url` being `https://api.deepseek.com/anthropic`.

With simple configuration, you can integrate the capabilities of DeepSeek into the Anthropic API ecosystem.

---

## Use DeepSeek in Claude Code[​](#use-deepseek-in-claude-code "Direct link to Use DeepSeek in Claude Code")

Please refer to [Integrate with AI Tools](https://api-docs.deepseek.com/guides/coding_agents).

## Invoke DeepSeek Model via Anthropic API[​](#invoke-deepseek-model-via-anthropic-api "Direct link to Invoke DeepSeek Model via Anthropic API")

1.  Install Anthropic SDK

```
pip install anthropic
```

2.  Config Environment Variables

```
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropicexport ANTHROPIC_API_KEY=${YOUR_API_KEY}
```

3.  Invoke the API

```
import anthropicclient = anthropic.Anthropic()message = client.messages.create(    model="deepseek-v4-pro",    max_tokens=1000,    system="You are a helpful assistant.",    messages=[        {            "role": "user",            "content": [                {                    "type": "text",                    "text": "Hi, how are you?"                }            ]        }    ])print(message.content)
```

**Note:** When you pass an unsupported model name to DeepSeek's Anthropic API, the API backend will automatically map it to the `deepseek-v4-flash` model.

---

## Anthropic Model Mapping[​](#anthropic-model-mapping "Direct link to Anthropic Model Mapping")

When you use the Anthropic API, we map the Claude model names you pass in:

-   Models starting with claude-opus are mapped to deepseek-v4-pro
-   Models starting with claude-haiku or claude-sonnet are mapped to deepseek-v4-flash

With this mapping, when using the developer mode of the new Claude Desktop APP, you can bypass the APP's model name restrictions by simply changing the base\_url and api\_key to connect to DeepSeek models.

---

## Anthropic API Compatibility Details[​](#anthropic-api-compatibility-details "Direct link to Anthropic API Compatibility Details")

### HTTP Header[​](#http-header "Direct link to HTTP Header")

| Field | Support Status |
| --- | --- |
| anthropic-beta | Ignored |
| anthropic-version | Ignored |
| x-api-key | Fully Supported |

### Simple Fields[​](#simple-fields "Direct link to Simple Fields")

| Field | Support Status |
| --- | --- |
| model | Use DeepSeek Model Instead |
| max\_tokens | Fully Supported |
| container | Ignored |
| mcp\_servers | Ignored |
| metadata | `user_id` is supported, others are ignored<br>Please refer to [Rate Limit & Isolation](https://api-docs.deepseek.com/quick_start/rate_limit) for more information about `user_id` parameter. |
| service\_tier | Ignored |
| stop\_sequences | Fully Supported |
| stream | Fully Supported |
| system | Fully Supported |
| temperature | Fully Supported (range \[0.0 ~ 2.0\]) |
| thinking | Supported (`budget_tokens` is ignored) |
| output\_config | Only `effort` is supported |
| top\_k | Ignored |
| top\_p | Fully Supported |

### Tool Fields[​](#tool-fields "Direct link to Tool Fields")

#### tools[​](#tools "Direct link to tools")

| Field | Support Status |
| --- | --- |
| name | Fully Supported |
| input\_schema | Fully Supported |
| description | Fully Supported |
| cache\_control | Ignored |

#### tool\_choice[​](#tool_choice "Direct link to tool_choice")

| Value | Support Status |
| --- | --- |
| none | Fully Supported |
| auto | Supported (`disable_parallel_tool_use` is ignored) |
| any | Supported (`disable_parallel_tool_use` is ignored) |
| tool | Supported (`disable_parallel_tool_use` is ignored) |

### Message Fields[​](#message-fields "Direct link to Message Fields")

| Field | Variant | Sub-Field | Support Status |
| --- | --- | --- | --- |
| content | string |  | Fully Supported |
| content | array, type="text" | text | Fully Supported |
| content | array, type="text" | cache\_control | Ignored |
| content | array, type="text" | citations | Ignored |
| content | array, type="image" |  | Not Supported |
| content | array, type = "document" |  | Not Supported |
| content | array, type = "search\_result" |  | Not Supported |
| content | array, type = "thinking" |  | Supported |
| content | array, type="redacted\_thinking" |  | Not Supported |
| content | array, type = "tool\_use" | id | Fully Supported |
| content | array, type = "tool\_use" | input | Fully Supported |
| content | array, type = "tool\_use" | name | Fully Supported |
| content | array, type = "tool\_use" | cache\_control | Ignored |
| content | array, type = "tool\_result" | tool\_use\_id | Fully Supported |
| content | array, type = "tool\_result" | content | Fully Supported |
| content | array, type = "tool\_result" | cache\_control | Ignored |
| content | array, type = "tool\_result" | is\_error | Ignored |
| content | array, type = "server\_tool\_use" |  | Supported |
| content | array, type = "web\_search\_tool\_result" |  | Supported |
| content | array, type = "code\_execution\_tool\_result" |  | Not Supported |
| content | array, type = "mcp\_tool\_use" |  | Not Supported |
| content | array, type = "mcp\_tool\_result" |  | Not Supported |
| content | array, type = "container\_upload" |  | Not Supported |