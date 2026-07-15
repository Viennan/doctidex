模型上下文（Context）包括输入信息（问题）和输出信息（回答），当触发深度思考时输出还包括思维链内容（CoT）。思维链内容展现模型处理问题的过程，包括将问题拆分为多个问题进行处理，生成多种回复综合得出更好回答的过程。在多轮对话中，上下文管理在保持话题一致性等方面非常重要，对此方舟提供了一些管理上下文的方法。

<span id="5ddcab90"></span>
# 上下文输入

<span id="8739761c"></span>
## 手动输入上下文

[Chat API](https://www.volcengine.com/docs/82379/1494384) 发起请求，是独立无状态的，需手动管理上下文。需通过交替排列 user 消息 与 assistant 消息，让模型在请求中获取之前对话信息。


<Tabs>
<Tab zoneid="UmzHrju6yQ" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seed-2-1-pro-260628",
    "messages": [
        {"role": "user", "content": "深度思考模型与非深度思考模型区别"},
        {"role": "assistant", "content": "推理模型主要依靠逻辑、规则或概率等进行分析、推导和判断以得出结论或决策，非推理模型则是通过模式识别、统计分析或模拟等方式来实现数据描述、分类、聚类或生成等任务而不依赖显式逻辑推理。"},
        {"role": "user", "content": "我要研究深度思考模型与非深度思考模型区别的课题，怎么体现我的专业性"}
    ]
  }'
```



* 您可按需替换 Model ID。Model ID 查询见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="wU7imdsCJM" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# Install SDK:  pip install 'volcengine-python-sdk[ark]'
from volcenginesdkarkruntime import Ark 

client = Ark(
    # The base URL for model invocation
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    # Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'), 
    # Deep thinking takes longer; set a larger timeout, with 1,800 seconds or more recommended
    timeout=1800,
)

# 创建一个对话请求
completion = client.chat.completions.create(
    # Replace with Model ID
    model = "doubao-seed-2-1-pro-260628",
    messages=[
        {"role": "user", "content": "研究深度思考模型与非深度思考模型区别"},
        {"role": "assistant", "content": "推理模型主要依靠逻辑、规则或概率等进行分析、推导和判断以得出结论或决策，非推理模型则是通过模式识别、统计分析或模拟等方式来实现数据描述、分类、聚类或生成等任务而不依赖显式逻辑推理。"},
        {"role": "user", "content": "我要研究深度思考模型与非深度思考模型区别的课题，怎么体现我的专业性"},
    ],
)

if hasattr(completion.choices[0].message, 'reasoning_content'):
    print(completion.choices[0].message.reasoning_content)
print(completion.choices[0].message.content)
```



</Tab>
<Tab zoneid="n6dBUBWQWs" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"
    "time"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        //通过 os.Getenv 从环境变量中获取 ARK_API_KEY
        os.Getenv("ARK_API_KEY"),
        // The base URL for model invocation
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
        //深度思考耗时更长，请设置更大的超时限制，推荐为30分钟及以上
        arkruntime.WithTimeout(30*time.Minute),
    )
    // 创建一个上下文，通常用于传递请求的上下文信息，如超时、取消等
    ctx := context.Background()
    // 构建聊天完成请求，设置请求的模型和消息内容
    req := model.CreateChatCompletionRequest{
        // Replace with Model ID
        Model: "doubao-seed-2-1-pro-260628",
        Messages: []*model.ChatCompletionMessage{
            {
                // 消息的角色为用户
                Role: model.ChatMessageRoleUser,
                Content: &model.ChatCompletionMessageContent{
                    StringValue: volcengine.String("研究深度思考模型与非深度思考模型区别"),
                },
            },
            {
                // 消息的角色为模型
                Role: model.ChatMessageRoleAssistant,
                Content: &model.ChatCompletionMessageContent{
                    StringValue: volcengine.String("推理模型主要依靠逻辑、规则或概率等进行分析、推导和判断以得出结论或决策，非推理模型则是通过模式识别、统计分析或模拟等方式来实现数据描述、分类、聚类或生成等任务而不依赖显式逻辑推理。"),
                },
            },
            {
                // 消息的角色为用户
                Role: model.ChatMessageRoleUser,
                Content: &model.ChatCompletionMessageContent{
                    StringValue: volcengine.String("我要研究深度思考模型与非深度思考模型区别的课题，怎么体现我的专业性"),
                },
            },
        },
    }

    // 发送聊天完成请求，并将结果存储在 resp 中，将可能出现的错误存储在 err 中
    resp, err := client.CreateChatCompletion(ctx, req)
    if err != nil {
        // 若出现错误，打印错误信息并终止程序
        fmt.Printf("standard chat error: %v\n", err)
        return
    }
    // 检查是否触发深度思考，触发则打印思维链内容
    if resp.Choices[0].Message.ReasoningContent != nil {
        fmt.Println(*resp.Choices[0].Message.ReasoningContent)
    }
    // 打印聊天完成请求的响应结果
    fmt.Println(*resp.Choices[0].Message.Content.StringValue)
}
```



</Tab>
<Tab zoneid="PH2uQHS0wy" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.volcengine.ark.runtime;

import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionRequest;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessage;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessageRole;
import com.volcengine.ark.runtime.service.ArkService;
import java.time.Duration;
import java.util.Arrays;
import java.util.List;

/**
 * 这是一个示例类，展示了如何使用ArkService来完成聊天功能。
 */
public class ChatCompletionsExample {
    public static void main(String[] args) {
        // 从环境变量中获取API密钥
        String apiKey = System.getenv("ARK_API_KEY");
        // 创建ArkService实例
        ArkService arkService = ArkService.builder()
                .apiKey(apiKey)
                .timeout(Duration.ofMinutes(30))// 深度思考耗时更长，请设置更大的超时限制，推荐为30分钟及以上
                // The base URL for model invocation
                .baseUrl("https://ark.cn-beijing.volces.com/api/v3")
                .build();
        // 多轮消息列表
        final List<ChatMessage> messages = Arrays.asList(
            ChatMessage.builder().role(ChatMessageRole.USER).content("研究深度思考模型与非深度思考模型区别").build(),
            ChatMessage.builder().role(ChatMessageRole.ASSISTANT).content("推理模型主要依靠逻辑、规则或概率等进行分析、推导和判断以得出结论或决策，非推理模型则是通过模式识别、统计分析或模拟等方式来实现数据描述、分类、聚类或生成等任务而不依赖显式逻辑推理。").build(),
            ChatMessage.builder().role(ChatMessageRole.USER).content("我要研究深度思考模型与非深度思考模型区别的课题，怎么体现我的专业性").build()
        );
        // 创建聊天完成请求
        ChatCompletionRequest chatCompletionRequest = ChatCompletionRequest.builder()
                .model("doubao-seed-2-1-pro-260628")//Replace with Model ID
                .messages(messages) // 设置消息列表
                .build();
        // 发送聊天完成请求并打印响应
        try {
            // 获取响应并打印每个选择的消息内容
            arkService.createChatCompletion(chatCompletionRequest)
                    .getChoices()
                    .forEach(choice -> {
                        // 进行空值检查后打印推理内容
                        if (choice.getMessage().getReasoningContent() != null) {
                            System.out.println("推理内容: " + choice.getMessage().getReasoningContent());
                        } else {
                            System.out.println("推理内容为空");
                        }
                        // 打印消息内容
                        System.out.println("消息内容: " + choice.getMessage().getContent());
                    });
        } catch (Exception e) {
            System.out.println("请求失败: " + e.getMessage());
        } finally {
            // 关闭服务执行器
            arkService.shutdownExecutor();
        }
    }
}
```



</Tab>
<Tab zoneid="ntJRdjzDnh" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI

client = OpenAI(
    # 从环境变量中读取方舟API Key
    api_key=os.environ.get("ARK_API_KEY"), 
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    # 深度思考耗时更长，避免链接超时导致失败，请设置更大的超时限制，推荐为1800 秒及以上
    timeout=1800,
    )
completion = client.chat.completions.create(
    # Replace with Model ID
    model = "doubao-seed-2-1-pro-260628",
    messages=[
        {"role": "user", "content": "研究深度思考模型与非深度思考模型区别"},
        {"role": "assistant", "content": "推理模型主要依靠逻辑、规则或概率等进行分析、推导和判断以得出结论或决策，非推理模型则是通过模式识别、统计分析或模拟等方式来实现数据描述、分类、聚类或生成等任务而不依赖显式逻辑推理。"},
        {"role": "user", "content": "我要研究深度思考模型与非深度思考模型区别的课题，怎么体现我的专业性"},
    ],
)

if hasattr(completion.choices[0].message, 'reasoning_content'):
    print(completion.choices[0].message.reasoning_content)
print(completion.choices[0].message.content)
```



</Tab>
</Tabs>


<span id="cc13704a"></span>
## 通过 ID 输入上下文

[Responses API](https://www.volcengine.com/docs/82379/1569618) 支持更简洁方式管理上下文。默认情况下请求的输入和输出都会持久化存储，后续请求只需传入 ID 就可以引入对应请求的输入和输出。


<Tabs>
<Tab zoneid="WcHwzBV44q" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
      "model": "doubao-seed-2-1-pro-260628",
      "input": "Hi，讲个笑话。"
  }'
```


```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
      "model": "doubao-seed-2-1-pro-260628",
      "previous_response_id":"<id>",
      "input": "这个笑话的笑点在哪？"
  }'
```


第二次请求需将 curl 命令中的 `<id>` 替换为上一次请求返回的 Response id。


</Tab>
<Tab zoneid="KEju3H49In" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark

# Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
api_key = os.getenv('ARK_API_KEY')

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# Create the first-round conversation request
response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input="Hi，帮我讲个笑话。"
)
print(response)

# Create the second-round conversation request
second_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "这个笑话的笑点在哪？"}],
)
print(second_response)
```



</Tab>
<Tab zoneid="SbxWRz1JtP" title="Go">
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
    // Create the first-round conversation request
    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-2-1-pro-260628",
        Input: &responses.ResponsesInput{Union: &responses.ResponsesInput_StringValue{StringValue: "Hi，讲个笑话。"}},
    })
    if err != nil {
        fmt.Printf("response error: %v\n", err)
        return
    }
    fmt.Println(resp)

    id := resp.GetId()
    inputMessage := &responses.ItemEasyMessage{
        Role:    responses.MessageRole_user,
        Content: &responses.MessageContent{Union: &responses.MessageContent_StringValue{StringValue: "这个笑话的笑点在哪？"}},
    }
    fmt.Println("-----------------")
    // Create the second-round conversation request
    second_resp, second_err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "doubao-seed-2-1-pro-260628",
        PreviousResponseId: &id,
        Input: &responses.ResponsesInput{
            Union: &responses.ResponsesInput_ListValue{
                ListValue: &responses.InputItemList{ListValue: []*responses.InputItem{{
                    Union: &responses.InputItem_EasyMessage{
                        EasyMessage: inputMessage,
                    },
                }}},
            },
        },
    })
    if second_err != nil {
        fmt.Printf("second response error: %v\n", second_err)
        return
    }
    fmt.Println(second_resp)
}
```



</Tab>
<Tab zoneid="T8DuK4DJLc" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.example;
import com.volcengine.ark.runtime.model.responses.item.ItemEasyMessage;
import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import com.volcengine.ark.runtime.model.responses.constant.ResponsesConstants;
import com.volcengine.ark.runtime.model.responses.item.MessageContent;

public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // The base URL for model invocation
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();
        // Create the first-round conversation request
        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .input(ResponsesInput.builder().stringValue("Hi，帮我讲个笑话。").build())
                .build();
        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);
        // Create the second-round conversation request
        CreateResponsesRequest request2 = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .previousResponseId(resp.getId())
                .input(ResponsesInput.builder().addListItem(
                        ItemEasyMessage.builder().role(ResponsesConstants.MESSAGE_ROLE_USER).content(
                                MessageContent.builder().stringValue("这个笑话的笑点在哪？").build()
                        ).build()
                ).build())
                .build();
        ResponseObject resp2 = arkService.createResponse(request2);
        System.out.println(resp2);

        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="FnmGt0vrnA" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
from openai import OpenAI
import os

# Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# Create the first-round conversation request
response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input="Hi，帮我讲个笑话。"
)
print(response)

# Create the second-round conversation request
second_response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    previous_response_id=response.id,
    input=[{"role": "user", "content": "这个笑话的笑点在哪？"}],
)
print(second_response)
```



</Tab>
</Tabs>


<span id="88aa9091"></span>
# 上下文长度控制

输入长内容，或对话轮数增加，需同时考虑模型输出长度和上下文窗口限制。模型输入和输出会进行计量，达到长度限制会截断或报错。合理控制模型输出长度，平衡业务效果、成本与稳定性：


* 减少触发限流（TPM 限制、突发流量限制等），保障服务稳定性。

* 精确控制 token 用量，平衡成本与质量。

* 控制推理耗时，提升用户交互体验。


同时，平台支持对模型输出（思维链、回答）长度控制，来控制 token 用量。核心规格及参数，如下图：

<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/1d7c7f33e7b9451893989339e7e7017c~tplv-goo7wpa0wc-image.image) </span>

> 不同模型支持的上下文窗口、最大输入、最大思维链长度均有差异，可在 [模型列表](https://www.volcengine.com/docs/82379/1330310) 查询。


<span id="3cb3d444"></span>
## 控制输出（回答+思维链）长度

[Chat API](https://www.volcengine.com/docs/82379/1494384) 使用 **max_completion_tokens** 字段，控制模型输出长度，当模型输出达到配置值时，模型停止推理。

> [Responses API](https://www.volcengine.com/docs/82379/1569618) 使用 max_output_tokens 字段 控制模型输出长度，详细信息参见 [设置最大输出长度](https://www.volcengine.com/docs/82379/1956279#1460ba95)。


支持的模型：250528及之后版本的大语言模型，如无特殊说明，默认支持该字段。方舟平台大语言模型列表，请参见[文本生成能力](https://www.volcengine.com/docs/82379/1330310#32e9e053)。

> doubao\-1\-5\-pro\-32k\-character\-250715、doubao\-seed\-translation\-250915 模型不支持该字段。



<Tabs>
<Tab zoneid="ZgxnU8tUgb" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seed-2-1-pro-260628",
    "messages": [
        {
            "role": "user",
            "content": "你好"
        }
    ],
    "max_completion_tokens": 1024
  }'
```



* 您可按需替换 Model ID。Model ID 查询见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="XT5umZWmw6" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# Install SDK:  pip install 'volcengine-python-sdk[ark]'
from volcenginesdkarkruntime import Ark 

client = Ark(
    # The base URL for model invocation
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    # Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'), 
    # Deep thinking takes longer; set a larger timeout, with 1,800 seconds or more recommended
    timeout=1800,
)

# 创建一个对话请求
completion = client.chat.completions.create(
    # Replace with Model ID
    model = "doubao-seed-2-1-pro-260628",
    messages=[
        {"role": "system", "content": "你是 AI 人工智能助手"},
        {"role": "user", "content": "常见的十字花科植物有哪些？"},
    ],
    # 设置模型最大输出长度为 1024 token，按需调整
    max_completion_tokens = 1024,
)
print(completion.choices[0].message.content)
```



</Tab>
<Tab zoneid="w7z1OHyboa" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "io"
    "os"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        os.Getenv("ARK_API_KEY"),
        // The base URL for model invocation
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
        //深度思考耗时更长，请设置更大的超时限制，推荐为30分钟及以上
        arkruntime.WithTimeout(30*time.Minute),
    )
    
    ctx := context.Background()

    fmt.Println("----- standard request -----")
    req := model.CreateChatCompletionRequest{
        // Replace with Model ID
       Model: "doubao-seed-2-1-pro-260628",
       Messages: []*model.ChatCompletionMessage{
          {
             Role: model.ChatMessageRoleSystem,
             Content: &model.ChatCompletionMessageContent{
                StringValue: volcengine.String("你是 AI 人工智能助手"),
             },
          },
          {
             Role: model.ChatMessageRoleUser,
             Content: &model.ChatCompletionMessageContent{
                StringValue: volcengine.String("常见的十字花科植物有哪些？"),
             },
          },
       },
       MaxCompletionTokens: volcengine.Int(1024), // 设置最大输出长度为 1024 token
    }

    resp, err := client.CreateChatCompletion(ctx, req)
    if err != nil {
       fmt.Printf("standard chat error: %v\n", err)
       return
    }
    fmt.Println(*resp.Choices[0].Message.Content.StringValue)
}
```



</Tab>
<Tab zoneid="T5j7tnXRfl" title="Java">
<TabTitle>Java</TabTitle>

```java
package com.volcengine.ark.runtime;

import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionRequest;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessage;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessageRole;
import com.volcengine.ark.runtime.service.ArkService;
import java.util.ArrayList;
import java.util.List;
import java.time.Duration;

public class ChatCompletionsExample {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // 创建ArkService实例
        ArkService arkService = ArkService.builder()
                .apiKey(apiKey)
                .timeout(Duration.ofMinutes(30))// 深度思考耗时更长，请设置更大的超时限制，推荐为30分钟及以上
                // The base URL for model invocation
                .baseUrl("https://ark.cn-beijing.volces.com/api/v3")
                .build();
        System.out.println("\n----- standard request -----");
        final List<ChatMessage> messages = new ArrayList<>();
        final ChatMessage systemMessage = ChatMessage.builder().role(ChatMessageRole.SYSTEM).content("你是 AI 人工智能助手").build();
        final ChatMessage userMessage = ChatMessage.builder().role(ChatMessageRole.USER).content("常见的十字花科植物有哪些？").build();
        messages.add(systemMessage);
        messages.add(userMessage);
        ChatCompletionRequest chatCompletionRequest = ChatCompletionRequest.builder()
                .model("doubao-seed-2-1-pro-260628")//Replace with Model ID
                .messages(messages)
                .maxCompletionTokens(1024)// 设置最大输出长度为 1024 token
                .build();
        arkService.createChatCompletion(chatCompletionRequest).getChoices().forEach(choice -> System.out.println(choice.getMessage().getContent()));
        // shutdown service
        arkService.shutdownExecutor();
    }
}
```



</Tab>
</Tabs>


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>



* <div data-tips="true" data-tips-type="tip"><strong>max_tokens</strong> 、 <strong>max_completion_tokens</strong> 不可同时设置，会直接报错。</div>



 &nbsp;

<span id="c7fbdbe3"></span>
## 控制回答长度

[Chat API](https://www.volcengine.com/docs/82379/1494384) 可通过设置 **max_tokens** 字段，控制模型回答长度。当回答长度达到配置值时，模型停止推理。


<Tabs>
<Tab zoneid="wPGKirGjYI" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seed-2-1-pro-260628",
    "messages": [
        {
            "role": "user",
            "content": "你好"
        }
    ],
    "max_tokens": 1024
  }'
```



* 按需替换 Model ID，查询 Model ID 请参见 [模型列表](https://www.volcengine.com/docs/82379/1330310)。


</Tab>
<Tab zoneid="M2h0xjKepF" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# Install SDK:  pip install 'volcengine-python-sdk[ark]'
from volcenginesdkarkruntime import Ark 

# 初始化Ark客户端
client = Ark(
    # The base URL for model invocation
    base_url="https://ark.cn-beijing.volces.com/api/v3", 
    # Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'), 
)

completion = client.chat.completions.create(
    # Replace with Model ID
    model = "doubao-seed-2-1-pro-260628",
    messages=[
        {"role": "system", "content": "你是 AI 人工智能助手"},
        {"role": "user", "content": "常见的十字花科植物有哪些？"},
    ],
    # 设置模型最大输出长度为 1024 token，您可按需进行调整
    max_tokens=1024,
)
print(completion.choices[0].message.content)
```



</Tab>
<Tab zoneid="bpluZOe4NV" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "io"
    "os"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        os.Getenv("ARK_API_KEY"),
        // The base URL for model invocation
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    
    ctx := context.Background()

    fmt.Println("----- standard request -----")
    req := model.CreateChatCompletionRequest{
        // Replace with Model ID
       Model: "doubao-seed-2-1-pro-260628",
       Messages: []*model.ChatCompletionMessage{
          {
             Role: model.ChatMessageRoleSystem,
             Content: &model.ChatCompletionMessageContent{
                StringValue: volcengine.String("你是 AI 人工智能助手"),
             },
          },
          {
             Role: model.ChatMessageRoleUser,
             Content: &model.ChatCompletionMessageContent{
                StringValue: volcengine.String("常见的十字花科植物有哪些？"),
             },
          },
       },
       MaxTokens: volcengine.Int(1024), // 设置最大输出长度为 1024 token
    }

    resp, err := client.CreateChatCompletion(ctx, req)
    if err != nil {
       fmt.Printf("standard chat error: %v\n", err)
       return
    }
    fmt.Println(*resp.Choices[0].Message.Content.StringValue)
}
```



</Tab>
<Tab zoneid="rARFyhEi55" title="Java">
<TabTitle>Java</TabTitle>

```java
package com.ark.sample;

import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionRequest;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessage;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessageRole;
import com.volcengine.ark.runtime.service.ArkService;
import java.util.ArrayList;
import java.util.List;

public class ChatCompletionsExample {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // The base URL for model invocation
        ArkService service = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();
        System.out.println("----- standard request -----");
        final List<ChatMessage> messages = new ArrayList<>();
        final ChatMessage systemMessage = ChatMessage.builder().role(ChatMessageRole.SYSTEM).content("你是 AI 人工智能助手").build();
        final ChatMessage userMessage = ChatMessage.builder().role(ChatMessageRole.USER).content("常见的十字花科植物有哪些？").build();
        messages.add(systemMessage);
        messages.add(userMessage);

        ChatCompletionRequest chatCompletionRequest = ChatCompletionRequest.builder()
               .model("doubao-seed-2-1-pro-260628")//Replace with Model ID
               .messages(messages)
               .maxTokens(1024)// 设置最大输出长度为 1024 token
               .build();
        service.createChatCompletion(chatCompletionRequest).getChoices().forEach(choice -> System.out.println(choice.getMessage().getContent()));
        // shutdown service
        service.shutdownExecutor();
    }
}
```



</Tab>
</Tabs>


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>



* <div data-tips="true" data-tips-type="tip"><strong>max_tokens</strong> 、 <strong>max_completion_tokens</strong> 不可同时设置，会直接报错。</div>


* <div data-tips="true" data-tips-type="tip"><a href="https://www.volcengine.com/docs/82379/1569618">Responses API</a> 不支持 <strong>max_tokens</strong> 字段。</div>



<span id="480730d0"></span>
## 控制思维链长度 [ 新增 ]

设置 **reasoning_effort** 调节深度思考的程度，间接控制思维链内容长度。当前提供4档：


* `minimal`：关闭思考，直接回答。

* `low`：轻量思考，侧重快速响应。

* `medium`：均衡模式，兼顾速度与深度。

* `high`：深度分析，处理复杂问题。

   与 **thinking.type** 关系：

* **thinking.type** 取值为`enabled`：支持配置 **reasoning_effort** 。当 **reasoning_effort** 取值为`minimal`时，则关闭思考，直接回答。

* **thinking.type** 取值为`disabled`： **reasoning_effort** 仅支持取值`minimal`。当 **reasoning_effort** 取值为`low`、`medium`、`high`时会报错。



<Tabs>
<Tab zoneid="H3xBAhuZDb" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seed-2-1-pro-260628",
     "messages": [
         {
             "role": "user",
             "content": [
                {
                    "image_url": {
                        "url": "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg"
                    },
                    "type": "image_url"
                },
                {
                    "text": "图片主要讲了什么?",
                    "type": "text"
                }
            ]
         }
     ],
     "thinking":{"type":"enabled"},
     "reasoning_effort": "low"
}'
```



</Tab>
<Tab zoneid="v4RVvru7FP" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# Install SDK:  pip install 'volcengine-python-sdk[ark]'
from volcenginesdkarkruntime import Ark 

client = Ark(
    # The base URL for model invocation
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    # Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'), 
    # Deep thinking takes longer; set a larger timeout, with 1,800 seconds or more recommended
    timeout=1800,
)

completion = client.chat.completions.create(
    # Replace with Model ID  .
    model = "doubao-seed-2-1-pro-260628",
    messages=[
        {
            "role": "user",
             "content": [                
                {"type": "image_url","image_url": {"url":  "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg"}},
                {"type": "text", "text": "图片主要讲了什么?"},
            ],
        }
    ],
    thinking={"type":"enabled"},
    reasoning_effort="low"
)

print(completion.choices[0])
```



</Tab>
<Tab zoneid="cshFlBOUB5" title="Go">
<TabTitle>Go</TabTitle>

```Go
package main

import (
    "context"
    "fmt"
    "os"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime/model"
    "github.com/volcengine/volcengine-go-sdk/volcengine"
)

func main() {
    client := arkruntime.NewClientWithApiKey(
        //通过 os.Getenv 从环境变量中获取 ARK_API_KEY
        os.Getenv("ARK_API_KEY"),
        // The base URL for model invocation  .
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"),
    )
    // 创建一个上下文，通常用于传递请求的上下文信息，如超时、取消等
    ctx := context.Background()
    contentParts := []*model.ChatCompletionMessageContentPart{
        // 第一张图片
        {
            Type: "image_url",
            ImageURL: &model.ChatMessageImageURL{
                URL: "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg",
            },
        },
        // 文本内容
        {
            Type: "text",
            Text: "图片主要讲了什么?",
        },
    }
    effort := model.ReasoningEffortLow
    req := model.CreateChatCompletionRequest{
        // Replace with Model ID
       Model: "doubao-seed-2-1-pro-260628",
       Messages: []*model.ChatCompletionMessage{
          {
             // 消息的角色为用户
             Role: model.ChatMessageRoleUser,
             Content: &model.ChatCompletionMessageContent{
                ListValue: contentParts, // 多类型内容使用ListValue
             },
          },
       },
       Thinking:        &model.Thinking{Type: model.ThinkingTypeEnabled},
        ReasoningEffort: &effort,
    }

    // 发送聊天完成请求，并将结果存储在 resp 中，将可能出现的错误存储在 err 中
    resp, err := client.CreateChatCompletion(ctx, req)
    if err != nil {
       // 若出现错误，打印错误信息并终止程序
       fmt.Printf("standard chat error: %v\n", err)
       return
    }
    // 打印聊天完成请求的响应结果
    fmt.Println(*resp.Choices[0].Message.Content.StringValue)
}
```



</Tab>
<Tab zoneid="wM4EngY75X" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.model.completion.chat.*;
import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionContentPart.*;
import com.volcengine.ark.runtime.service.ArkService;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import okhttp3.ConnectionPool;
import okhttp3.Dispatcher;

public class MultiImageSample {
  static String apiKey = System.getenv("ARK_API_KEY");
  static ConnectionPool connectionPool = new ConnectionPool(5, 1, TimeUnit.SECONDS);
  static Dispatcher dispatcher = new Dispatcher();
  static ArkService arkService = ArkService.builder()
       .dispatcher(dispatcher)
       .connectionPool(connectionPool)
       .baseUrl("https://ark.cn-beijing.volces.com/api/v3") // The base URL for model invocation  .
       .apiKey(apiKey)
       .build();

  public static void main(String[] args) throws Exception {

    List<ChatMessage> messagesForReqList = new ArrayList<>();

    // 构建消息内容
    List<ChatCompletionContentPart> contentParts = new ArrayList<>();

    // 第一张图片部分使用builder模式
    contentParts.add(ChatCompletionContentPart.builder()
         .type("image_url")
         .imageUrl(new ChatCompletionContentPartImageURL(
            "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg"))
         .build());

    contentParts.add(ChatCompletionContentPart.builder()
         .type("text")
         .text("图片主要讲了什么？")
         .build());

    messagesForReqList.add(ChatMessage.builder()
         .role(ChatMessageRole.USER)
         .multiContent(contentParts)
         .build());

    ChatCompletionRequest req = ChatCompletionRequest.builder()
         .model("doubao-seed-2-1-pro-260628") //Replace with Model ID  .
         .messages(messagesForReqList)
         .thinking(new ChatCompletionRequest.ChatCompletionRequestThinking("enabled"))
         .reasoningEffort("low")
         .build();

    arkService.createChatCompletion(req)
         .getChoices()
         .forEach(choice -> System.out.println(choice.getMessage().getContent()));
    // shutdown service after all requests are finished
    arkService.shutdownExecutor();
  }
}
```



</Tab>
<Tab zoneid="NGZ65hpELZ" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI 

client = OpenAI(
    # The base URL for model invocation  .
    base_url="https://ark.cn-beijing.volces.com/api/v3", 
    # Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'), 
)

completion = client.chat.completions.create(
    # Replace with Model ID  .
    model = "doubao-seed-2-1-pro-260628",
    messages=[
        {
            "role": "user",
             "content": [                
                {"type": "image_url","image_url": {"url":  "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg"}},
                {"type": "text", "text": "图片主要讲了什么?"},
            ],
        }
    ],
    extra_body={"thinking":{"type":"enabled"}},
    reasoning_effort="low"
)

print(completion.choices[0])
```



</Tab>
</Tabs>


完整代码及使用，请参见 [调节思考长度](https://www.volcengine.com/docs/82379/1956279#dc4c1547)（Responses API）、[调节思考长度](https://www.volcengine.com/docs/82379/1449737#fc5eac89)（ChatCompletion API）。

<span id="a8d2f4a8"></span>
# 上下文传递逻辑

<span id="41d0a095"></span>
## 多轮对话场景


<span aceTableMode="list" aceTableWidth="8,3"></span>
|流程图 |说明 |
|---|---|
|<span>![图片](https://arkdoc.tos-cn-beijing.volces.com/flowcharts/advanced-usage/context-management-02.svg) </span> |* 在每一轮对话过程中，深度思考模型会输出思维链内容（CoT）和最终回答（Answer）。<br><br>* 在下一轮对话中，之前输出的思维链内容不会被拼接到上下文中。<br><br>> 思维链内容展现的是模型处理问题的过程，包括将问题拆分为多个问题进行处理，生成多种回复综合得出更好回答等过程。 |


<span id="a0247227"></span>
## 工具调用场景

工具调用场景中开启深度思考后，思维链处理策略变更如下：


* 旧策略（doubao\-seed\-1.8 之前的模型）：开启深度思考后，会直接丢弃生成的思维链内容，思维链内容不参与后续轮次的推理。

* 新策略（doubao\-seed\-1.8 及部分迭代模型）：针对工具调用场景优化了深度思考的执行逻辑，平台会自主判断是否将思维链内容输入给模型，参与后续轮次的推理，保障结果输出连贯、准确、可解释。


策略变更会导致模型输入 tokens 增加，其中未输入给模型的思维链内容，不会计算 tokens 用量。


<span aceTableMode="list" aceTableWidth="8,3"></span>
|流程图 |说明 |
|---|---|
|<span>![图片](https://arkdoc.tos-cn-beijing.volces.com/flowcharts/advanced-usage/context-management-03.svg) </span> |* 回答问题 1 时（请求 1.1 \- 1.2），模型进行多次思考 + 工具调用后给出答案，方舟会输入完整上下文包括思维链内容给模型处理。<br><br>* 开始回答问题2时（请求 2.1），方舟会自行判断并删除之前上下文中的思维链，输入给模型。 |


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">推荐在 Responses API 中使用 previous_response_id，平台自动保存历史对话的上下文，并在多轮交互中回传给推理服务。</div>


请求示例如下：


<Tabs>
<Tab zoneid="vhG3lzSWOu" title="Chat API">
<TabTitle>Chat API</TabTitle>

**第一轮请求：触发工具调用**

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seed-2-0-lite-260215",
    "messages": [
        {
            "role": "system",
            "content": "你是人工智能助手。"
        },
        {
            "role": "user",
            "content": "今天北京天气怎么样"
        }
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "天气查询",
                "parameters": {
                    "properties": {
                        "location": {
                            "description": "地点的位置信息，例如北京、上海。",
                            "type": "string"
                        }
                    },
                    "required": [
                        "location"
                    ],
                    "type": "object"
                }
            }
        }
    ]
  }'
```


**第一轮响应：返回工具调用指令**

模型会返回`reasoning_content`、`tool_calls`等关键字段。

```Bash
{
    "choices": [
        {
            "finish_reason": "tool_calls",
            "index": 0,
            "logprobs": null,
            "message": {
                "content": "",
                "reasoning_content": "用户问今天北京天气怎么样，我需要调用get_weather工具，参数location填北京。检查一下，参数是必填的location，已经有了，所以直接调用工具就行。",
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "arguments": " {\"location\": \"北京\"}",
                            "name": "get_weather"
                        },
                        "id": "call_wiezxeyae8jzxl3jx8nhfgb5",
                        "type": "function"
                    }
                ]
            }
        }
    ],
    ...
 }
```


**第二轮请求：回传完整上下文并生成最终响应**

第二轮请求还需要回传思维链信息、工具调用结果，模型生成回答。

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -d '{
    "model": "doubao-seed-2-0-lite-260215",
    "messages": [
        {
            "role": "system",
            "content": "你是人工智能助手。"
        },
        {
            "role": "user",
            "content": "今天北京天气怎么样"
        },
        {
            "role": "assistant",
            "reasoning_content": "用户问今天北京天气怎么样，我需要调用get_weather工具，参数location填北京。检查一下，参数是必填的location，已经有了，所以直接调用工具就行。",
            "tool_calls": [
                {
                    "function": {
                        "arguments": " {\"location\": \"北京\"}",
                        "name": "get_weather"
                    },
                    "id": "call_wiezxeyae8jzxl3jx8nhfgb5",
                    "type": "function"
                }
            ]
        },
        {
            "role": "tool",
            "tool_call_id":"call_wiezxeyae8jzxl3jx8nhfgb5",
            "content": "5度"
        }
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "天气查询",
                "parameters": {
                    "properties": {
                        "location": {
                            "description": "地点的位置信息，例如北京、上海。",
                            "type": "string"
                        }
                    },
                    "required": [
                        "location"
                    ],
                    "type": "object"
                }
            }
        }
    ]
  }'
```



</Tab>
<Tab zoneid="EEzF8ib33U" title="Responses API">
<TabTitle>Responses API</TabTitle>

**第一轮请求：触发工具调用**

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
    -H "Authorization: Bearer $ARK_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "doubao-seed-2-0-lite-260215",      
        "input": [
            {
                "role": "system",
                "content": "你是人工智能助手."
            },
            {
                "role": "user",
                "content": "今天北京天气怎么样"
            }
        ],
        "thinking":{"type": "enabled"},
        "tools": [
            {
                "type": "function",
                "name": "get_weather",
                "description": "天气查询",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "地点的位置信息，例如北京、上海。",
                        }
                    },
                    "required": ["location"]
                }
            }
        ]
    }'
```


**第一轮响应：返回工具调用指令**

模型返回信息包含`id`、`call_id`、`arguments`等关键字段。

```Bash
{
    "created_at": 1766126702,
    "id": "resp_0217661267019147d8950efa0e2f7c9d9cc7a1cc971272cf4548c",
    "max_output_tokens": 32768,
    "model": "doubao-seed-2-0-lite-260215",
    "object": "response",
    "output": [
        {
            "id": "rs_02176612670248500000000000000000000ffffac154e10754f5c",
            "type": "reasoning",
            "summary": [
                {
                    "type": "summary_text",
                    "text": "用户问今天北京的天气怎么样，我需要调用get_weather工具，参数location是北京。按照格式要求来写函数调用。"
                }
            ],
            "status": "completed"
        },
        {
            "arguments": " {\"location\": \"北京\"}",
            "call_id": "call_t885uulopdd499rn0pioze7l",
            "name": "get_weather",
            "type": "function_call",
            "id": "fc_02176612670345400000000000000000000ffffac154e10a6753e",
            "status": "completed"
        }
    ],
    ....
 }
```


**第二轮请求：回传结果并生成最终响应**

传入上一轮 response_id、工具调用结果等信息，模型生成自然语言回答。

```Bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
    -H "Authorization: Bearer $ARK_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "doubao-seed-2-0-lite-260215",
        "input": [
            {
                "type": "function_call_output",
                "call_id": "call_t885uulopdd499rn0pioze7l",
                "output": "5度"
            }
        ],
        "previous_response_id": "resp_0217661267019147d8950efa0e2f7c9d9cc7a1cc971272cf4548c",
        "thinking":{"type": "enabled"},
        "tools": [
            {
                "type": "function",
                "name": "get_weather",
                "description": "天气查询",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "地点的位置信息，例如北京、上海。"
                        }
                    },
                    "required": ["location"]
                }
            }
        ]
    }'
```



</Tab>
</Tabs>


<span id="e9fab508"></span>
# 长度限制生效逻辑

模型输出的组成如下公式，模型的输出 = 模型的回答 + 模型的思维链（如有）


* **max_tokens** ：控制模型的回答长度，默认值 4096。如果触发长度限制，模型停止回答，并在返回结构体的 **finish_reason** 字段为 `length`。

* **max_completion_tokens** ：控制模型的回答、模型思维链总长度，如触发限制，模型停止回答，并在返回结构体的 **finish_reason** 字段为 `length`。如配置了 **max_completion_tokens** ，max_tokens默认值会失效，常用于超长文本输出或者控制模型返回长度。


<span id="13bc800b"></span>
## 仅配置 max_tokens（默认逻辑）

下面是各个对象的长度限制说明。


|对象 |关键参数 |说明 |可否配置 |
|---|---|---|---|
|问题 |最大输入长度 |`上下文窗口 - 思维链窗口`，与回答共享配额。<br><br>> 可理解为问答配额。 |模型规格，不可配置 |
|思维链 |思维链窗口 |独占，不共享，即单次请求如有未使用的配额也不共享给问题及回答。 |模型规格，不可配置 |
|回答 |最大回答长度 |最大回答长度，通过 **max_tokens** 参数配置。<br><br>另外随着输入长度增加，回答配额也会受 **最大输入长度（问答配额）**  剩余配额影响。<br><br>回答配额<br><br>=`min(最大回答长度, 最大输入长度-实际输入长度)`<br><br>=`min(最大回答长度, 上下文窗口-思维链窗口-实际输入长度)` |API字段，可配置 |
||最大输入长度 ||模型规格，不可配置 |


内容截断逻辑举例：模型A属性如下，上下文窗口 96k，思维链窗口 32k，最大输入长度(问答配额) 64k，配置最大回答长度 16k。


* 当用户输入的问题 56k，模型输出思维链16k，模型输出的回答达到8k时，`问题+回答 = 56k+8k = 64k`，触发 **最大输入长度（问答配额）**  限制，模型停止推理。

* 当用户输入的问题 22k，模型输出思维链16k，模型输出的回答达到16k时，触发 **最大回答长度** 限制，模型停止推理。

* 当用户输入的问题 22k，模型输出思维链32k，触发 **最大思维链长度** 限制，模型停止推理。


<span id="04191ca1"></span>
## 仅配置 **max_completion_tokens**


|影响/控制对象 |关键参数 |说明 |可否配置 |
|---|---|---|---|
|问题 |最大输入长度 |与回答共享配额，即未使用配额共享给回答内容 |模型规格，不可配置 |
|思维链 |最大输出长度 |与回答共享配额，即未使用的配额共享给回答。 |API字段，可配置 |
| |思维链窗口 |模型能够输出的最大思维链长度。 |模型规格，不可配置 |
|回答 |最大输出长度 |与思维链共享配额，即输出长度不可超过`最大输出长度-已输出的思维链内容长度` |API字段，可配置 |


内容截断逻辑举例：模型A属性如下，上下文窗口 96k，最大输入长度 64k，最大思维链长度 32k。配置最大输出长度（ **max_completion_tokens** ） 32k 后，最大回答长度（ **max_tokens** ）默认值(`4096`)限制失效：


* 当用户输入的内容长度 72k，触发 **最大输入长度** 限制，直接报错。

* 当模型输出的内容超过 32k，触发 **最大思维链长度** 限制，模型停止推理。

* 当用户输入的问题长度 26k，模型输出的思维链长度 16k，模型输出的回答长度达到 16k 时，`思维链长度+回答长度=16k+16k=32k`，触发 **最大输出长度** 限制，模型停止推理。


&nbsp;



