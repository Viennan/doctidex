Responses API 支持前缀缓存和 Session 缓存。通过缓存常用上下文信息，减少每次请求时重复处理的开销，达到降低成本目标（命中缓存的输入有折扣优惠）。适合多轮对话、工具调用、角色扮演等需多次传入相同内容的场景。


> * 工作原理和缓存介绍请参见[什么是上下文缓存](https://www.volcengine.com/docs/82379/1398933#dc271b0a)。

> * API 结构及参数请参见 [Responses API](https://www.volcengine.com/docs/82379/1569618)。

> * 部分模型使用 Responses API 时支持隐式缓存，具体参见[隐式缓存](https://www.volcengine.com/docs/82379/1398933#1dfad02a)、[模型列表](https://www.volcengine.com/docs/82379/1330310)。


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">方舟平台的新用户？获取 API Key 及 开通模型等准备工作，请参见 <a href="https://www.volcengine.com/docs/82379/1399008">快速入门</a>。</div>


<span id="14293fd6"></span>
# 支持模型

参见文档[上下文缓存能力](https://www.volcengine.com/docs/82379/1330310#ed095742)。

<span id="f3aac1c0"></span>
# 前提条件

使用前需完成以下操作。

开通模型的缓存服务：在[ ](https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement?LLM=%7B%7D&OpenTokenDrawer=false)[开通管理页](https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement?LLM=%7B%7D&OpenTokenDrawer=false)[ ](https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement?LLM=%7B%7D&OpenTokenDrawer=false)，模型列表的 **推理（缓存）定价** 列开通。

<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/e96b4642ab314149b7de8566f6bb7a79~tplv-goo7wpa0wc-image.image) </span>

<span id="dd3b59ab"></span>
# 快速开始


<Tabs>
<Tab zoneid="f1PoFuL53w" title="Python">
<TabTitle>Python</TabTitle>

```Python
# encoding=utf-8
import os
from volcenginesdkarkruntime import Ark

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('ARK_API_KEY'),
)
# 需要大于等于256个token，否则无法创建前缀缓存
input_text = "你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>"
response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input=[
        {
            "role": "system",
            "content": input_text,
        }
    ],
    caching={"type": "enabled", "prefix": True}, 
    thinking={"type": "disabled"},
)
print(response.usage.model_dump_json())

second_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "用5个简短的要点总结核心情节。"}],
    caching={"type": "enabled"}, 
    thinking={"type": "disabled"},
)

print(second_response.output[0].content[0].text)
print(second_response.usage.model_dump_json())
```



</Tab>
<Tab zoneid="hSwyRoDRBT" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        // Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    ctx := context.Background()
    prefix := true
    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-2-1-pro-260628",
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_EasyMessage{
                        EasyMessage: &responses.ItemEasyMessage{
                            Role:    responses.MessageRole_system,
                            Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>"}},
                        },
                    },
                }}},
            },
        },
        Caching:  &responses.ResponsesCaching{Type: responses.CacheType_enabled.Enum(), Prefix: &prefix},
        Thinking: &responses.ResponsesThinking{Type: responses.ThinkingType_disabled.Enum()},
    })
    if err != nil {
        fmt.Printf("response error: %v", err)
        return
    }
    fmt.Println(resp.GetUsage())

    second_resp, second_err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model:              "doubao-seed-2-1-pro-260628",
        PreviousResponseId: &resp.Id,
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_EasyMessage{
                        EasyMessage: &responses.ItemEasyMessage{
                            Role:    responses.MessageRole_user,
                            Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "用5个简短的要点总结核心情节。"}},
                        },
                    },
                }}},
            },
        },
        Thinking: &responses.ResponsesThinking{Type: responses.ThinkingType_disabled.Enum()},
    })
    if second_err != nil {
        fmt.Printf("second response error: %v", second_err)
        return
    }
    fmt.Println(second_resp.GetUsage())

}
```



</Tab>
<Tab zoneid="xS5mLUB00Q" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
import com.volcengine.ark.runtime.model.responses.response.DeleteResponseResponse;
import com.volcengine.ark.runtime.model.responses.common.ResponsesCaching;
import com.volcengine.ark.runtime.model.responses.common.ResponsesThinking;

public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // The base URL for model invocation
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_SYSTEM).content(
                                MessageContent.builder().stringValue("你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>").build()
                        ).build()
                ).build())
                .caching(ResponsesCaching.builder().type("enabled").prefix(true).build())
                .thinking(ResponsesThinking.builder().type(ResponsesConstants.THINKING_TYPE_DISABLED).build())
                .build();
        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);
        System.out.println(resp.getUsage());
        System.out.println("---------------------");
        CreateResponsesRequest request2 = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .previousResponseId(resp.getId())
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder().stringValue("Briefly summarize the story in 5 bullet points").build()
                        ).build()
                ).build())
                .thinking(ResponsesThinking.builder().type(ResponsesConstants.THINKING_TYPE_DISABLED).build())
                .build();
        ResponseObject resp2 = arkService.createResponse(request2);
        System.out.println(resp2);
        System.out.println(resp2.getUsage());        
        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="X0DvBvVKFB" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
# encoding=utf-8
import os
from openai import OpenAI
 
client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('ARK_API_KEY'),
)
# 需要大于等于256个token，否则无法创建前缀缓存
input_text = "你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>"
response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input=[
        {
            "role": "system",
            "content": input_text,
        }
    ],
    extra_body={"caching": {"type": "enabled", "prefix": True}, "thinking": {"type": "disabled"}},
)
print(response.usage.model_dump_json())

second_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "用5个简短的要点总结核心情节。"}],
    extra_body={"thinking": {"type": "disabled"}},
)

print(second_response.output[0].content[0].text)
print(second_response.usage.model_dump_json())
```



</Tab>
<Tab zoneid="G2YB71nxqg" title="Curl">
<TabTitle>Curl</TabTitle>

1. 创建缓存，并将内容写入。

> 缓存内容*需要大于256个token，否则无法创建前缀缓存。* 


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H "Content-Type: application/json" \
-d '{
    "model": "doubao-seed-2-1-pro-260628",
    "input": "你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>",
    "caching":{
        "type":"enabled", 
        "prefix": true
    },
    "thinking": {
        "type": "disabled"
    }
}'
```



2. 在后续请求中，通过 id，来读取并使用缓存。


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H "Content-Type: application/json" \
-d '{
    "model": "doubao-seed-2-1-pro-260628",
    "input": "用5个简短的要点总结核心情节。",
    "caching":{
        "type":"enabled"
    },
    "thinking": {
        "type": "disabled"
    },
    "previous_response_id":"resp_0217****"
}'
```



</Tab>
</Tabs>


返回的`usage`信息如下：

```JSON
{"input_tokens":2535,"input_tokens_details":{"cached_tokens":0},"output_tokens":0,"output_tokens_details":{"reasoning_tokens":0},"total_tokens":2535,"tool_usage":null,"tool_usage_details":null}
{"input_tokens":2551,"input_tokens_details":{"cached_tokens":2535},"output_tokens":133,"output_tokens_details":{"reasoning_tokens":0},"total_tokens":2684,"tool_usage":null,"tool_usage_details":null}
```


> 在上面示例的长文本场景中，第2次请求 `"cached_tokens":2535` ，相比未使用缓存，带缓存的请求费用下降 80%。在超长输入，如超长文本或超长历史对话场景下，成本下降将更加明显。


<span id="1ec1fe26"></span>
# 前缀缓存

您可以预先存储并缓存角色、背景等初始化信息，后续调用模型时无需重复发送此信息给模型，而将缓存的处理后的初始化信息作为缓存输入，减少重复计算和存储开销，降低使用成本，尤其适用于具有重复提示或标准化开头文本的应用。

Note：首轮输入时，需设置 `"store": true`（默认`true`），`"caching": {"type": "enabled", "prefix": true }`，以创建前缀缓存。后续轮次即可通过 previous_response_id 引用缓存信息。

创建前缀缓存场景限制：Input tokens需要大于等于 256 tokens，否则会报错；stream参数不能设置为true。

> 创建前缀缓存时，返回的usage中total_tokens=input_tokens，output_tokens始终为0。



<Tabs>
<Tab zoneid="djXUxNaUrC" title="Python">
<TabTitle>Python</TabTitle>

```Python
# coding=utf-8
import os
from volcenginesdkarkruntime import Ark

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('ARK_API_KEY'),
)

response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input=[
            {
             "role": "system", 
             "content": "你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>" # Input must exceed 256 tokens; otherwise, prefix caching cannot be created.
            }
          ],
    caching={"type": "enabled", "prefix": True},
    thinking={"type": "disabled"},
)
print(response)

second_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "以 Della 的视角写一篇日记，描述其卖掉长发前的心情。"}],
    thinking={"type": "disabled"},
)
print(second_response)

third_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "分析 O. Henry 在该故事片段中反讽手法的运用，给出简明阐释。"}],
    thinking={"type": "disabled"},
)
print(third_response)
```



</Tab>
<Tab zoneid="O5HBLu3vDx" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        // Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    ctx := context.Background()
    prefix := true
    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-2-1-pro-260628",
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_EasyMessage{
                        EasyMessage: &responses.ItemEasyMessage{
                            Role:    responses.MessageRole_system,
                            Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>"}},
                        },
                    },
                }}},
            },
        },
        Caching:  &responses.ResponsesCaching{Type: responses.CacheType_enabled.Enum(), Prefix: &prefix},
        Thinking: &responses.ResponsesThinking{Type: responses.ThinkingType_disabled.Enum()},
    })
    if err != nil {
        fmt.Printf("response error: %v", err)
        return
    }
    fmt.Println(resp)

    second_resp, second_err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model:              "doubao-seed-2-1-pro-260628",
        PreviousResponseId: &resp.Id,
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_EasyMessage{
                        EasyMessage: &responses.ItemEasyMessage{
                            Role:    responses.MessageRole_user,
                            Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "以 Della 的视角写一篇日记，描述其卖掉长发前的心情。"}},
                        },
                    },
                }}},
            },
        },
        Thinking: &responses.ResponsesThinking{Type: responses.ThinkingType_disabled.Enum()},
    })
    if second_err != nil {
        fmt.Printf("second response error: %v", second_err)
        return
    }
    fmt.Println(second_resp)

    third_resp, third_err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model:              "doubao-seed-2-1-pro-260628",
        PreviousResponseId: &resp.Id,
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_EasyMessage{
                        EasyMessage: &responses.ItemEasyMessage{
                            Role:    responses.MessageRole_user,
                            Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "分析 O. Henry 在该故事片段中反讽手法的运用，给出简明阐释。"}},
                        },
                    },
                }}},
            },
        },
        Thinking: &responses.ResponsesThinking{Type: responses.ThinkingType_disabled.Enum()},
    })
    if third_err != nil {
        fmt.Printf("second response error: %v", third_err)
        return
    }
    fmt.Println(third_resp)
}
```



</Tab>
<Tab zoneid="MbacOb7Afv" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
import com.volcengine.ark.runtime.model.responses.response.DeleteResponseResponse;
import com.volcengine.ark.runtime.model.responses.common.ResponsesCaching;
import com.volcengine.ark.runtime.model.responses.common.ResponsesThinking;

public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // The base URL for model invocation
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_SYSTEM).content(
                                MessageContent.builder().stringValue("你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>").build()
                        ).build()
                ).build())
                .caching(ResponsesCaching.builder().type("enabled").prefix(true).build())
                .thinking(ResponsesThinking.builder().type(ResponsesConstants.THINKING_TYPE_DISABLED).build())
                .build();
        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);
        System.out.println("---------------------");
        CreateResponsesRequest request2 = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .previousResponseId(resp.getId())
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder().stringValue("以 Della 的视角写一篇日记，描述其卖掉长发前的心情。").build()
                        ).build()
                ).build())
                .thinking(ResponsesThinking.builder().type(ResponsesConstants.THINKING_TYPE_DISABLED).build())
                .build();
        ResponseObject resp2 = arkService.createResponse(request2);
        System.out.println(resp2);
        System.out.println("---------------------");
        CreateResponsesRequest request3 = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .previousResponseId(resp.getId())
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder().stringValue("分析 O. Henry 在该故事片段中反讽手法的运用，给出简明阐释。").build()
                        ).build()
                ).build())
                .thinking(ResponsesThinking.builder().type(ResponsesConstants.THINKING_TYPE_DISABLED).build())
                .build();
        ResponseObject resp3 = arkService.createResponse(request3);
        System.out.println(resp3);

        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="rXDuoykFJg" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
# coding=utf-8
import os
from openai import OpenAI

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('ARK_API_KEY'),
)

response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input=[
            {
             "role": "system", 
             "content": "你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>"  # It needs to exceed 256 tokens; otherwise, prefix caching cannot be created.
            }
    ],
    extra_body={
        "caching": {"type": "enabled", "prefix": True},
        "thinking":{"type":"disabled"}
    }
)
print(response)

second_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "以 Della 的视角写一篇日记，描述其卖掉长发前的心境。"}],
    extra_body={
        "thinking":{"type":"disabled"}
    }
)
print(second_response)

third_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "分析 O. Henry 在该故事片段中反讽手法的运用，给出简明阐释。"}],
    extra_body={
        "thinking":{"type":"disabled"}
    }
)
print(third_response)
```



</Tab>
<Tab zoneid="pmXs2rouhM" title="Curl">
<TabTitle>Curl</TabTitle>

1. 创建缓存，并将内容写入。


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H "Content-Type: application/json;charset=utf-8" \
-d '{
    "model": "doubao-seed-2-1-pro-260628",
    "input":[
                {
                 "role":"system", 
                 "content":"你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>" # Input must exceed 256 tokens; otherwise, prefix caching cannot be created.
                }
          ],
    "caching":{
        "type":"enabled",
        "prefix": true
    },
    "thinking": {
        "type": "disabled"
    }
}'
```



2. 在第二轮请求中，通过第一轮返回 id，来读取并使用缓存。


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H "Content-Type: application/json" \
-d '{
    "model": "doubao-seed-2-1-pro-260628",
    "input": "以 Della 的视角写一篇日记，描述其卖掉长发前的心境。",
    "caching":{
        "type":"enabled"
    },
    "thinking": {
        "type": "disabled"
    },
    "previous_response_id":"<THE_ID_FROM_FIRST_CALL>"
}'
```



3. 在第三轮请求中，还是通过第一轮返回 id，来读取并使用缓存。


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H "Content-Type: application/json" \
-d '{
    "model": "doubao-seed-2-1-pro-260628",
    "input": "分析 O. Henry 在该故事片段中反讽手法的运用，给出简明阐释。",
    "caching":{
        "type":"enabled"
    },
    "thinking": {
        "type": "disabled"
    },
    "previous_response_id":"<THE_ID_FROM_FIRST_CALL>"
}'
```



</Tab>
</Tabs>


<span id="3e69e743"></span>
# Session 缓存

Responses API 支持自动储存历史上下文对话并保持缓存，通过调用 previous_response_id 在多轮对话等场景中使用缓存输入并降低推理成本。


<Tabs>
<Tab zoneid="BnCM9nP13d" title="Python">
<TabTitle>Python</TabTitle>

```Python
# encoding=utf-8
import os
from volcenginesdkarkruntime import Ark
 
client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('ARK_API_KEY'),
)
input_text = "你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>"
response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input=[
        {
            "role": "system", 
            "content": input_text
        },
        {
            "role": "user",
            "content":"用5个简短的要点总结核心情节。"
        }
    ],
    caching={"type": "enabled"},
    thinking={"type": "disabled"},
)
print(response)
print(response.usage.model_dump_json())

# 在后续请求中输入缓存信息
second_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "以 Della 的视角写一篇日记，描述其卖掉长发前的心情。"}],
    caching={"type": "enabled"},
    thinking={"type": "disabled"},
)

print(second_response)
print(second_response.usage.model_dump_json())

third_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=second_response.id,
    input=[{"role": "user", "content": "根据原文节选和 Della 刚写的日记，想象 Jame 读到这篇日记时会有怎样的感受。"}],
    caching={"type": "enabled"},
    thinking={"type": "disabled"},
)
print(third_response)
print(third_response.usage.model_dump_json())
```



</Tab>
<Tab zoneid="Qoeq9tjE1S" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        // Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    ctx := context.Background()

    input := "你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>"
    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-2-1-pro-260628",
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{
                    {
                        Union: &responses.InputItem_EasyMessage{
                            EasyMessage: &responses.ItemEasyMessage{
                                Role:    responses.MessageRole_system,
                                Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: input}},
                            },
                        },
                    },
                    {
                        Union: &responses.InputItem_EasyMessage{
                            EasyMessage: &responses.ItemEasyMessage{
                                Role:    responses.MessageRole_user,
                                Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "用5个简短的要点总结核心情节。"}},
                            },
                        },
                    },
                }},
            },
        },
        Caching:  &responses.ResponsesCaching{Type: responses.CacheType_enabled.Enum()},
        Thinking: &responses.ResponsesThinking{Type: responses.ThinkingType_disabled.Enum()},
    })
    if err != nil {
        fmt.Printf("response error: %v", err)
        return
    }
    fmt.Println(resp)
    fmt.Println(resp.GetUsage())

    second_resp, second_err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model:              "doubao-seed-2-1-pro-260628",
        PreviousResponseId: &resp.Id,
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_EasyMessage{
                        EasyMessage: &responses.ItemEasyMessage{
                            Role:    responses.MessageRole_user,
                            Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "以 Della 的视角写一篇日记，描述其卖掉长发前的心情。"}},
                        },
                    },
                }}},
            },
        },
        Thinking: &responses.ResponsesThinking{Type: responses.ThinkingType_disabled.Enum()},
    })
    if second_err != nil {
        fmt.Printf("second response error: %v", second_err)
        return
    }
    fmt.Println(second_resp)
    fmt.Println(second_resp.GetUsage())
    third_resp, third_err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model:              "doubao-seed-2-1-pro-260628",
        PreviousResponseId: &second_resp.Id,
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_EasyMessage{
                        EasyMessage: &responses.ItemEasyMessage{
                            Role:    responses.MessageRole_user,
                            Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "根据原文节选和 Della 刚写的日记，想象 Jame 读到这篇日记时会有怎样的感受。"}},
                        },
                    },
                }}},
            },
        },
        Thinking: &responses.ResponsesThinking{Type: responses.ThinkingType_disabled.Enum()},
    })
    if third_err != nil {
        fmt.Printf("third response error: %v", third_err)
        return
    }
    fmt.Println(third_resp)
    fmt.Println(third_resp.GetUsage())
}
```



</Tab>
<Tab zoneid="VP5ocObmG2" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
import com.volcengine.ark.runtime.model.responses.common.ResponsesCaching;
import com.volcengine.ark.runtime.model.responses.common.ResponsesThinking;

public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // The base URL for model invocation
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();
        String input = "你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>";
        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .input(ResponsesInput.builder()
                        .addListItem(ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_SYSTEM).content(
                                MessageContent.builder().stringValue(input).build()
                        ).build())
                        .addListItem(ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder().stringValue("用5个简短的要点总结核心情节。").build()
                        ).build())
                        .build())
                .caching(ResponsesCaching.builder().type("enabled").build())
                .thinking(ResponsesThinking.builder().type(ResponsesConstants.THINKING_TYPE_DISABLED).build())
                .build();
        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);
        System.out.println(resp.getUsage());
        System.out.println("---------------------");
        CreateResponsesRequest request2 = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .previousResponseId(resp.getId())
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder().stringValue("以Della的视角写一篇日记，描述其卖掉长发前的心情。").build()
                        ).build()
                ).build())
                .thinking(ResponsesThinking.builder().type(ResponsesConstants.THINKING_TYPE_DISABLED).build())
                .build();
        ResponseObject resp2 = arkService.createResponse(request2);
        System.out.println(resp2.getOutput());
        System.out.println(resp2.getUsage());
        System.out.println("---------------------");
        CreateResponsesRequest request3 = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .previousResponseId(resp2.getId())
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder().stringValue("根据原文节选和 Della 刚写的日记，想象 Jame 读到这篇日记时会有怎样的感受。").build()
                        ).build()
                ).build())
                .thinking(ResponsesThinking.builder().type(ResponsesConstants.THINKING_TYPE_DISABLED).build())
                .build();
        ResponseObject resp3 = arkService.createResponse(request3);
        System.out.println(resp3.getOutput());
        System.out.println(resp3.getUsage());

        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="SQNGnbHLVd" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('ARK_API_KEY'),
)

input_text = "你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>"
response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input=[
            {
                "role": "system", 
                "content": input_text
            },
            {
                "role": "user",
                "content":"用5个简短的要点总结核心情节。"
            }
          ],
    extra_body={
        "caching": {"type": "enabled"},
        "thinking":{"type":"disabled"}
    }
)
print(response)

second_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "以 Della 的视角写一篇日记，描述其卖掉长发前的心情。"}],
    extra_body={
        "caching": {"type": "enabled"},
        "thinking":{"type":"disabled"}
    }
)
print(second_response)

third_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=second_response.id,
    input=[{"role": "user", "content": "根据原文节选和 Della 刚写的日记，想象 Jame 读到这篇日记时会有怎样的感受。"}],
    extra_body={
        "caching": {"type": "enabled"},
        "thinking":{"type":"disabled"}
    }
)
print(third_response)
```



</Tab>
<Tab zoneid="y72SNAM8lk" title="Curl">
<TabTitle>Curl</TabTitle>

1. 创建缓存，并将内容写入。


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-1-pro-260628",
    "input":[
                {
                 "role":"system", 
                 "content":"你是一名文学分析助手，回答需简洁明了，请根据下面内容分析《麦琪的礼物》相关问题。<麦琪的礼物小说内容>"
                },
                {
                 "role": "user",
                 "content":"用5个简短的要点总结核心情节。"
                }
          ],
    "caching":{
        "type":"enabled"
    },
    "thinking": {
        "type": "disabled"
    }
}'
```



2. 在第二轮请求中，通过第一轮返回 id，来读取并使用缓存。

> 如需更新缓存，配置 "caching":{"type":"enabled" } ，并使用返回的请求的 id。


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H "Content-Type: application/json" \
-d '{
    "model": "doubao-seed-2-1-pro-260628",
    "input": "以 Della 的视角写一篇日记，描述其卖掉长发前的心情。",
    "caching":{
        "type":"enabled"
    },
    "thinking": {
        "type": "disabled"
    },
    "previous_response_id": "<THE_ID_FROM_FIRST_CALL>"
}'
```



3. 在第三轮请求中，通过第二轮返回 id，来读取并使用缓存。


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H "Content-Type: application/json" \
-d '{
    "model": "doubao-seed-2-1-pro-260628",
    "input": "根据原文节选和 Della 刚写的日记，想象 Jame 读到这篇日记时会有怎样的感受。",
    "caching":{
        "type":"enabled"
    },
    "thinking": {
        "type": "disabled"
    },
    "previous_response_id": "<THE_ID_FROM_SECOND_CALL>"
}'
```



</Tab>
</Tabs>


<span id="0387e087"></span>
# 控制存储/缓存生命周期

支持通过字段 **expire_at** 字段指定上下文存储（ **store** ）及上下文缓存（ **caching** ）过期时刻。当前最大可存储时间为 7 天，即当前UTC Unix 时间戳 + 604800。

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">与 Context API 指定 <strong>ttl</strong> （Time To Live，即对应信息保存在方舟平台的时长）不同，Responses API 存储和缓存指定的为过期时刻，具体不同如下。</div>



* <div data-tips="true" data-tips-type="warning">Context API ：通过 <strong>ttl</strong> 指定缓存可存储的时长，当<code>当前时刻 - 缓存最近使用时刻</code>大于 <strong>ttl</strong> 值，则存储过期。会随着缓存被调用，而重置缓存保存时长。</div>


* <div data-tips="true" data-tips-type="warning">Responses API：通过 <strong>expire_at</strong> 指定上下文存储及缓存的过期时刻，当<code>当前时刻</code> 超过 <code>过期时刻</code> ，则存储过期。不随着缓存/存储的使用而重置缓存生命周期。</div>



<div data-tips="true" data-tips-type="warning">使用 Responses API 存储/存储过期，需通过<a href="https://www.volcengine.com/docs/82379/1569618">接口</a>重新创建存储/缓存内容。</div>



<Tabs>
<Tab zoneid="hDYZVjlrIo" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark
import time

# Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
api_key = os.getenv('ARK_API_KEY')

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input=[
            {
             "role": "system", 
             "content": "Hello"
            }
          ],
    caching={"type": "enabled"}, 
    thinking={"type": "disabled"},
    expire_at=int(time.time()) + 3600,
)
print(response.model_dump_json())
```



</Tab>
<Tab zoneid="rWeMB005io" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"
    "time"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model/responses"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    ctx := context.Background()

    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-2-1-pro-260628",
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{
                    {
                        Union: &responses.InputItem_EasyMessage{
                            EasyMessage: &responses.ItemEasyMessage{
                                Role:    responses.MessageRole_system,
                                Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "Hello"}},
                            },
                        },
                    },
                }},
            },
        },
        Caching:  &responses.ResponsesCaching{Type: responses.CacheType_enabled.Enum()},
        Thinking: &responses.ResponsesThinking{Type: responses.ThinkingType_disabled.Enum()},
        ExpireAt: volcengine.Int64(time.Now().Unix() + 3600),
    })
    if err != nil {
        fmt.Printf("response error: %v", err)
        return
    }
    fmt.Println(resp)
    fmt.Println(resp.GetUsage())
}
```



</Tab>
<Tab zoneid="XCxOFXNBsw" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;
import com.volcengine.ark.runtime.model.responses.common.ResponsesCaching;
import com.volcengine.ark.runtime.model.responses.common.ResponsesThinking;
import java.time.Instant;

public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // The base URL for model invocation
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();
 
        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .input(ResponsesInput.builder()
                        .addListItem(ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_SYSTEM).content(
                                MessageContent.builder().stringValue("Hello").build()
                        ).build())
                        .build())
                .caching(ResponsesCaching.builder().type("enabled").build())
                .thinking(ResponsesThinking.builder().type(ResponsesConstants.THINKING_TYPE_DISABLED).build())
                .expireAt(Instant.now().getEpochSecond() + 3600)
                .build();
        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);
        System.out.println(resp.getUsage());

        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="u4vFUwQQ34" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI
import time

# Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input=[
            {
             "role": "system", 
             "content": "Hello"
            }
          ],
    extra_body={
        "thinking":{"type":"disabled"},
        "caching":{"type":"enabled"},
        "expire_at": int(time.time()) + 3600 # The expiration time for storage and cache is 1 hour from the current time.
    }
)
print(response.model_dump_json())
```



</Tab>
<Tab zoneid="LlZVqU8yQM" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
-H "Authorization: Bearer $ARK_API_KEY" \
-H "Content-Type: application/json" \
-d '{
    "model": "doubao-seed-2-1-pro-260628",
    "input":[
                {
                 "role":"system", 
                  "content":"Hello"
                }
          ],
    "expire_at":<The UTC Unix timestamp of the expiration time>,
    "caching":{
        "type":"enabled"
    },
    "thinking": {
        "type": "disabled"
    }
}'
```



</Tab>
</Tabs>


<span id="2c55c76f"></span>
# 删除缓存

Responses API 支持根据 ID 来删除缓存，与删除历史对话一致，如下所示，便于您根据业务自主控制缓存信息量，如删除不必要的缓存信息，减少冗余输入，降低成本。


<Tabs>
<Tab zoneid="cuDb6kgYM3" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark

api_key = os.getenv('ARK_API_KEY')
client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

response = client.responses.delete("resp_0217****")
print(response)
```



</Tab>
<Tab zoneid="SY0JDXV5ov" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"

    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    ctx := context.Background()
    resp := client.DeleteResponse(ctx, "resp_0217****")
    fmt.Println()
    fmt.Println(resp)
}
```



</Tab>
<Tab zoneid="qd7Wrx7npZ" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.DeleteResponseResponse;

public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");

        // The base URL for model invocation
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();
        DeleteResponseResponse deleteResult = arkService.deleteResponse(
                DeleteResponseRequest.builder().responseId("resp_0217****").build()
        );

        System.out.println(deleteResult);

        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="v9kCJGgIXV" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
from openai import OpenAI
import os

api_key = os.getenv('ARK_API_KEY')
client = OpenAI(    
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

response = client.responses.delete("resp_0217****")
print(response)
```



</Tab>
<Tab zoneid="EVvUaggFPj" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses/resp_0217**** \
  -X DELETE \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
```



</Tab>
</Tabs>


需注意，删除某轮缓存后，后续轮次缓存的信息在下次请求时会重新计算和存储。如下图所示（图中场景为第5轮请求后调用接口删除第3轮对话信息）。

<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/e82470faec7f446c94dfcb55810fe08e~tplv-goo7wpa0wc-image.image) </span>

第6轮请求时，4、5 轮信息将重新计算并缓存，此时其信息将作为输入，而非缓存输入进行计费。

<span id="c03763f2"></span>
# 使用说明


* **store** ：写入缓存前提是存储已开启，即手动配置 **store** 字段为`true`或保持缺省（默认为 `true`）。

* **caching** ：

   * **前一轮对话的请求开启了缓存写入，当前轮次对话才能写入缓存** 。以此类推，当某轮次请求需写入缓存，则需保证所有前置轮次请求写入缓存状态开启，即前置所有轮次均有`"caching": {"type": "enabled" }`。举例：当希望第 5 轮请求能写入缓存信息，则需要 1~4 轮均保持缓存写入开启。当其中一轮请求关闭缓存写入，则后续轮次对话请求均无法写入缓存。

   * 前面轮次只要存在`"caching": {"type": "enabled" }`，则不支持使用json_schema，但支持使用json_object。

   * 缓存的有效期可以通过 `expire_at` 字段自定义，最长支持 7 天。


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">store 字段：控制是否存储本轮请求信息，加入历史上下文中，供下次调用。主要作用为简化上下文管理，无需手动管理历史上下文，通过传入 id 输入历史上下文。开启存储功能是写入缓存的前提，及 <strong>store</strong> 字段为 <code>true</code>。</div>


<div data-tips="true" data-tips-type="tip">caching 字段是控制平台是否将本轮信息以链式结构写入缓存中。在下次请求传入 id 调用时，可减小 prefill 阶段计算开销，降低请求成本（通过缓存输入模型的内容会有较高折扣）。</div>



* <div data-tips="true" data-tips-type="tip">doubao\-seed\-1.8 之前的模型：缓存输入和模型回答，不含思维链内容。</div>


* <div data-tips="true" data-tips-type="tip">doubao\-seed\-1.8 模型：缓存输入的内容。</div>



<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">在版本切换过程中，缓存暂不可用，使用 Responses API 请求时将无法命中缓存，但会进行存储并产生缓存存储费用；版本切换完成后，可正常命中历史轮次的缓存。具体参见<a href="https://www.volcengine.com/docs/82379/1182403#d7c15496">版本切换</a>。</div>



* **instructions** ：若想写入缓存， **instructions** 字段应为空。若在本轮请求里设置了 **instructions** ，该轮对话不能调用已有缓存，也无法将本轮信息写入缓存。

* **thinking** ：请求中 **thinking** 字段的赋值应该与前一轮保持一致才可使用缓存/写入缓存。


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">当第1轮设定<code>"thinking":{"type":"auto"}</code>，则后续如需使用或者写入缓存，均需一样赋值，设定<code>"thinking":{"type":"auto"}</code>。</div>


<div data-tips="true" data-tips-type="tip">当第1轮未设置 <strong>thinking</strong> 字段，即不赋值，后续请求如需写入缓存或者调用已有缓存，也需不设置 <strong>thinking</strong> 字段。</div>



* **tools** ：仅在首轮请求时可以设置 **tools** 字段，后续所有对话将默认携带 tools 字段信息的缓存输入。

   * 不支持在后续轮次对话请求中设置 **tools** 字段，会冲突并报错处理。

   * 若首轮对话信息被删除，则后续所有轮次对话都不携带 **tools** 字段信息的缓存输入，也无法配置 **tools** 字段。


<span id="66b5f218"></span>
# 计费说明

计费单价请参见：[模型价格](https://www.volcengine.com/docs/82379/1544106)。

<span id="77706357"></span>
## 计费项


* **输入** （元/千 token）：正在进行的对话中的新增文本，即在删除场景后，需重新计算和缓存的历史对话信息。

* **缓存输入** （元/千 token）：输入为预先处理和缓存的内容，优化了计算和存储的开销，计费费率会显著低于新输入内容。

* **存储** （元/千 token/小时）：历史对话存储在缓存中，会产生存储费用。计算方式根据每个自然小时使用缓存的量乘以单价进行累加。


<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>



* <div data-tips="true" data-tips-type="warning">存储费用在缓存创建即产生，直到该缓存被手动删除或过期，停止计费。</div>


* <div data-tips="true" data-tips-type="warning">存储费用在每个自然小时如 8:00 整点出账，不足 1 小时按照 1 小时计算。</div>


* **输出** （元/千 token）：模型根据输入信息生成的内容。计费方式与未使用 Session 缓存的调用方式一致。


<span id="fd37f379"></span>
## 计费逻辑

> 每次请求计费用量可在返回的`usage`结构体看到，具体查看 [Responses API文档](https://www.volcengine.com/docs/82379/1569618)。


<span id="f0bb1ba1"></span>
### **输入 token 量**

可以通过`input_tokens - cached_tokens`来获得。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">doubao\-seed\-1.8 模型输入内容会包含上一轮的思维链内容，输入 tokens 量会增加，可以通过开启上下文编辑功能管理思维链内容和工具调用内容，控制输入 tokens，其中命中的缓存为输入内容与上下文编辑后缓存内容的交集。</div>


<span id="96dc7964"></span>
### **存储费用**

在请求中开启缓存后才会产生存储费用，即参数配置为`"caching": {"type": "enabled" }`。按自然小时计算，该小时内每一轮请求产生的新增缓存 token 量累加计算存储费用。

> 存储按自然小时计算，不足 1 小时会按 1 小时计算。



<span aceTableMode="list" aceTableWidth="1,4,4"></span>
|模型 |doubao\-seed\-1.8 之前的模型 |doubao\-seed\-1.8 模型 |
|---|---|---|
|缓存内容 |缓存输入和模型回答，不包含思维链内容。 |缓存输入的内容。 |
|请求示意图 |<span>![图片](https://arkdoc.tos-cn-beijing.volces.com/flowcharts/responses-api/context-cache-03.svg) </span> |<span>![图片](https://arkdoc.tos-cn-beijing.volces.com/flowcharts/responses-api/context-cache-04.svg) </span> |
|单次请求计算逻辑 |```Plain```<br>```- 缓存内容：输入的 token + 输出的 token - 思维链的 token```<br>```- 新增的缓存内容：当前轮次请求缓存内容 - 上一轮已缓存的内容```<br>```- 缓存存储费用：在缓存有效期内，每小时存储费用为新增的缓存内容 token × 存储单价```<br> |```Plain```<br>```- 缓存内容：输入的 token```<br>```- 新增的缓存内容：当前轮次请求缓存内容 - 上一轮已缓存的内容```<br>```- 缓存存储费用：在缓存有效期内，每小时存储费用为新增的缓存内容 token × 存储单价```<br> |


<span id="1e793b8c"></span>
### 费用计算

开启缓存后一次请求 1 个小时的费用包含：请求产生的 token 费用和缓存存储费用。以一次请求为例，计算公式如下：


* 使用缓存的请求费用


```Plain
= 输入花费 + 缓存输入花费 + 输出花费
= (input_tokens − cached_tokens) * 输入单价  
 + cached_tokens * 缓存输入单价 
 + output_tokens * 输出单价 
```



* 缓存存储费用


```Plain
= 新增的缓存存储费用
= 新增的缓存内容 token × 存储单价
= (当前轮次请求缓存内容  - 上一轮已缓存的内容) × 存储单价
```




