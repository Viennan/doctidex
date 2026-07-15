当您使用官方 SDK 时，设置自定义header等典型的使用，可以参考本说明。

<span id="243f3c5f"></span>
## 设置超时&重试次数

当您的网络环境不稳定或者响应时间较长的场景，可以设置超时和重试次数，以提高服务可用性。


* 超时设置（`timeout`）：适用于对响应时间较长的场景（如深度思考模型回复问题时间较长），避免请求时间超时导致服务中断，这里推荐30分钟（1800秒）。

   * Python SDK：默认 60秒 连接超时（建立网络连接的最大等待时间），600 秒 socket 超时（连接建立后的数据传输超时）。

   * Java SDK：默认 60秒 连接超时，600 秒 socket 超时。

   * Go SDK：默认 600s 端到端的总超时（从请求发起至响应接收的总超时）。

* 重试次数（`max_retries`）：适用于网络不稳定场景，自动重试因瞬时故障（如网络波动）失败的请求，默认2次，即请求失败默认会再重试2次，您可以按需配置。



<Tabs>
<Tab zoneid="CjExd4dvfZ" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# 通过命令安装方舟SDK pip install 'volcengine-python-sdk[ark]' .
from volcenginesdkarkruntime import Ark 

client = Ark(
    api_key=os.environ.get("ARK_API_KEY"),
    # 设置服务响应超时时间，单位秒，推荐1800秒及以上
    timeout=1800,
    # 设置重试次数
    max_retries=2,
    # The base URL for model invocation .
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)
```



</Tab>
<Tab zoneid="FbQE1kqwOO" title="Go">
<TabTitle>Go</TabTitle>

```Go
import (
    "os"
    "time"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
)

client := arkruntime.NewClientWithApiKey(
    os.Getenv("ARK_API_KEY"),
    arkruntime.WithTimeout(30*time.Minute), //设置后端处理完本次请求的整体超时时间，单位分钟，推荐30分钟及以上
    arkruntime.WithRetryTimes(2), //设置最大重试次数
    arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"), // The base URL for model invocation .
)
```



</Tab>
<Tab zoneid="nTbuLgUVwK" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.example;

import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionRequest;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessage;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessageRole;
import com.volcengine.ark.runtime.service.ArkService;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

public class ChatCompletionsExample {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        ArkService service = ArkService
                .builder()
                .baseUrl("https://ark.cn-beijing.volces.com/api/v3") // The base URL for model invocation .
                .apiKey(apiKey)
                .timeout(Duration.ofSeconds(1800))// 设置后端处理完请求的超时时间，单位秒，推荐为1800秒及以上
                .connectTimeout(Duration.ofSeconds(20))// 设置连接超时时间为20秒
                .retryTimes(2)// 设置重试次数为2次
                .build();
        final List<ChatMessage> messages = new ArrayList<>();
        final ChatMessage userMessage = ChatMessage.builder().role(ChatMessageRole.USER).content("你好")
                .build();
        messages.add(userMessage);

        ChatCompletionRequest chatCompletionRequest = ChatCompletionRequest.builder()
                .model("doubao-seed-2-1-pro-260628") //Replace with Model ID .
                .messages(messages)
                .build();

        service.createChatCompletion(chatCompletionRequest).getChoices()
                .forEach(choice -> System.out.println(choice.getMessage().getContent()));
        // shutdown service
        service.shutdownExecutor();
    }
}
```



</Tab>
</Tabs>


<span id="fa44b913"></span>
## 使用Access Key鉴权

当需要通过火山引擎云服务的标准鉴权体系（Access Key/Secret Key）认证时使用。

> 使用 Access Key 鉴权的实现原理是通过接口 [GetApiKey](https://www.volcengine.com/docs/82379/1262825) 获取临时 API Key 进行鉴权，此接口限流较低，务必使用单例模式进行请求，避免因限流导致鉴权失败，可参考[单例请求](https://www.volcengine.com/docs/82379/1544136#063cdc02)。



<Tabs>
<Tab zoneid="hEtI79q9WV" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# 通过命令安装方舟SDK pip install 'volcengine-python-sdk[ark]' .
from volcenginesdkarkruntime import Ark 
client = Ark(
    ak=os.environ.get("VOLC_ACCESSKEY"),
    sk=os.environ.get("VOLC_SECRETKEY"),
    # The base URL for model invocation .
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)
```



</Tab>
<Tab zoneid="xHavFzFFaZ" title="Go">
<TabTitle>Go</TabTitle>

```Go
import (
    "os"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
)

client := arkruntime.NewClientWithAkSk(
        os.Getenv("VOLC_ACCESSKEY"),
        os.Getenv("VOLC_SECRETKEY"),        
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"), // The base URL for model invocation .
)
```



</Tab>
<Tab zoneid="dtYaedTsTY" title="Java">
<TabTitle>Java</TabTitle>

```Java
import com.volcengine.ark.runtime.service.ArkService;

public class CreateArkClientExample1 {
    public static void main(String[] args) {
        String ak = System.getenv("VOLC_ACCESSKEY");
        String sk = System.getenv("VOLC_SECRETKEY");
        ArkService service = ArkService.builder().ak(ak).sk(sk)
                // The base URL for model invocation .
                .baseUrl("https://ark.cn-beijing.volces.com/api/v3")
                .build();
    }
    // do your operation...
}
```



</Tab>
</Tabs>


<span id="c8e7ffaf"></span>
## 设置自定义 header

自定义的 `header` 字段采用键值对（key\-value）结构，以对象形式呈现，具体格式示例如下：

```JSON
{
    "key1": "value1",
    "key2": "value2",
    ...,
    "keyN": "valueN"
}
```


可以用于传递额外信息，如配置 ID来串联日志，使能数据加密能力。支持该字段的接口有 [对话（Chat） API](https://www.volcengine.com/docs/82379/1494384)、[批量（Chat）API](https://www.volcengine.com/docs/82379/1528783)，下面是典型示例。

<span id="7493fbd5"></span>
### 问题定位

您可以在请求时，为多个请求设置 **key** 为 `X-Client-Request-Id`， **value** 配置为自定义的 ID，并提供 ID 给方舟售后团队，为您串联客户端和服务端日志，方便问题定位。


<Tabs>
<Tab zoneid="Icm9m64ow7" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# 通过命令安装方舟SDK pip install 'volcengine-python-sdk[ark]' .
from volcenginesdkarkruntime import Ark 

client = Ark(
    api_key=os.environ.get("ARK_API_KEY"),
    # The base URL for model invocation .
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

completion = client.chat.completions.create(
    # Replace with Model ID .
    model = "doubao-seed-2-1-pro-260628",
    messages = [
        {"role": "user", "content": "Hello"},
    ],
    # 自定义request id
    extra_headers={"X-Client-Request-Id": "My-Request-Id"}
)
print(completion.choices[0].message.content)
```



</Tab>
<Tab zoneid="JRvKv1r1O6" title="Go">
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
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"), // The base URL for model invocation .
    )
    ctx := context.Background()
    req := model.CreateChatCompletionRequest{
        Model: "doubao-seed-2-1-pro-260628", //Replace with Model ID .
        Messages: []*model.ChatCompletionMessage{
            {
                Role: model.ChatMessageRoleUser,
                Content: &model.ChatCompletionMessageContent{
                    StringValue: volcengine.String("Hello"),
                },
            },
        },
    }


    // 自定义request id
    resp, err := client.CreateChatCompletion(
        ctx,
        req,
        arkruntime.WithCustomHeader(model.ClientRequestHeader, "my-request-id"), // 自定义请求头
    )
    if err != nil {
        fmt.Printf("standard chat error: %v\n", err)
        return
    }
    fmt.Println(*resp.Choices[0].Message.Content.StringValue)
}
```



</Tab>
<Tab zoneid="bLq6iuSxVn" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.example;

import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionRequest;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessage;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessageRole;
import com.volcengine.ark.runtime.service.ArkService;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

public class ChatCompletionsExample3 {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // The base URL for model invocation .
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();
        final List<ChatMessage> messages = new ArrayList<>();
        final ChatMessage userMessage = ChatMessage.builder().role(ChatMessageRole.USER).content("常见的十字花科植物有哪些？").build();
        messages.add(userMessage);
        ChatCompletionRequest chatCompletionRequest = ChatCompletionRequest.builder()
                .model("doubao-seed-2-1-pro-260628") //Replace with Model ID .
                .messages(messages)
                .build();
        // 使用自定义的请求头
        arkService.createChatCompletion(chatCompletionRequest, new HashMap<String, String>(){{put(Const.CLIENT_REQUEST_HEADER, "my_request_id");}}).getChoices().forEach(choice -> System.out.println(choice.getMessage().getContent()));
        // shutdown service
        arkService.shutdownExecutor();
    }
}
```



</Tab>
</Tabs>


<span id="23274b89"></span>
### 加密数据

为了保证推理会话数据的传输安全，你可以为在线推理的会话数据加密。使能能力后，SDK 会对推理会话的内容进行加密。

> 更多能力介绍和原理信息请参考[推理会话数据应用层加密方案](https://www.volcengine.com/docs/82379/1389905)。


* 版本要求：

   * Python SDK：需要保证 SDK 版本 `volcengine-python-sdk` `1.0.104`及以上。参考[升级 Python SDK](https://www.volcengine.com/docs/82379/1541595#d6b883b8)获得 SDK 的最新版本。

   * Java SDK：需要保证 SDK 版本 `volcengine-java-sdk-ark-runtime` `0.2.50`及以上。参考[升级 Java SDK](https://www.volcengine.com/docs/82379/1541595#4ab4182d)获得 SDK 的最新版本。

* 能力支持：

   * 仅支持文本生成模型和视觉理解图片理解模型请求。

   * 图片仅支持 Base64 图片加密， URL 图片无法加密。

   * 仅支持官方 Python SDK、Java SDK 的 [Chat API](https://www.volcengine.com/docs/82379/1494384) 。

   * 支持单轮、多轮会话，支持流式、非流式，同步、异步调用。



<Tabs>
<Tab zoneid="YhCaDnPs2I" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# 通过命令安装方舟SDK pip install 'volcengine-python-sdk[ark]' .
from volcenginesdkarkruntime import Ark 

client = Ark(
    api_key=os.environ.get("ARK_API_KEY"),
    # The base URL for model invocation .
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

completion = client.chat.completions.create(
    # Replace with Model ID .
    model = "doubao-seed-2-1-pro-260628",
    messages = [
        {"role": "user", "content": "Hello"},
    ],
    #按下述代码设置自定义header，免费开启推理会话应用层加密
    extra_headers={'x-is-encrypted': 'true'}
)
print(completion.choices[0].message.content)
```



</Tab>
<Tab zoneid="oKM982qQlE" title="Java">
<TabTitle>Java</TabTitle>

在 `pom.xml` 文件中增加以下配置：

```XML
<dependencies>
    <!-- BouncyCastle 核心加密库（bcpkix依赖此包） -->
    <dependency>
        <groupId>org.bouncycastle</groupId>
        <artifactId>bcprov-jdk18on</artifactId>
        <version>1.78.1</version>
    </dependency>
    <!-- 包含PEMParser的模块（处理PEM格式证书） -->
    <dependency>
        <groupId>org.bouncycastle</groupId>
        <artifactId>bcpkix-jdk18on</artifactId>
        <version>1.78.1</version>
    </dependency>
</dependencies>
```


代码示例如下：

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionRequest;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessage;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessageRole;
import com.volcengine.ark.runtime.service.ArkService;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.HashMap;

public class ChatCompletionsExample {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        ArkService service = ArkService
                .builder()
                .apiKey(apiKey)
                .timeout(Duration.ofSeconds(1800)) // Set the backend request processing timeout in seconds, recommended to be 1800 seconds or longer
                .connectTimeout(Duration.ofSeconds(20)) // Set the connection timeout to 20 seconds
                .retryTimes(2)// Set the retry count to 2
                .build();
        final List<ChatMessage> messages = new ArrayList<>();
        final ChatMessage userMessage = ChatMessage.builder().role(ChatMessageRole.USER).content("Hello")
                .build();
        messages.add(userMessage);

        ChatCompletionRequest chatCompletionRequest = ChatCompletionRequest.builder()
                .model("doubao-seed-2-1-pro-260628") //Replace with Model ID
                .messages(messages)
                .build();

        // Set custom headers with the code below to enable application-layer encryption for inference sessions at no cost
        Map<String, String> customHeaders = new HashMap<>();
        customHeaders.put("x-is-encrypted", "true");
        service.createChatCompletion(chatCompletionRequest, customHeaders).getChoices()
                .forEach(choice -> System.out.println(choice.getMessage().getContent()));
        // shutdown service
        service.shutdownExecutor();
    }
}
```



</Tab>
</Tabs>


<span id="d5f5495b"></span>
### 开启数据上报

为了便于快速排查和定位问题，你可以在 Responses API 请求的 header 中增加`"X-Fornax-Trace: true"`开启数据上报。支持统计分析的数据见[分析统计](https://www.volcengine.com/docs/82379/1182403#db0a7d46)。

> 该能力限时免费提供使用。


* 版本要求：如果请求上报未生效，需升级 SDK 到最新版本。

* 能力支持：仅支持 [Responses API](https://www.volcengine.com/docs/82379/1569618)。



<Tabs>
<Tab zoneid="Kd8dERivY2" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=os.getenv('ARK_API_KEY'),
)

response = client.responses.create(
    model="<Endpoint_ID>",
    input="hello",
    extra_headers={'X-Fornax-Trace': 'true'}
)
print(response)
```



</Tab>
<Tab zoneid="DUCQFc42QW" title="Go">
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

    resp, err := client.CreateResponses(ctx, &responses.ResponsesRequest{
        Model: "<Endpoint_ID>",
        Input: &responses.ResponsesInput{Union: &responses.ResponsesInput_StringValue{StringValue: "hello"}},
    }, arkruntime.WithCustomHeader("X-Fornax-Trace", "true"))
    if err != nil {
        fmt.Printf("response error: %v\n", err)
        return
    }
    fmt.Println(resp)
}
```



</Tab>
<Tab zoneid="jubWps5tdT" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;
import java.util.HashMap;
import java.util.Map;

public class demo {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // The base URL for model invocation
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("<Endpoint_ID>")
                .input(ResponsesInput.builder().stringValue("hello").build())  
                .build();
        Map<String, String> customHeaders = new HashMap<>();
        customHeaders.put("X-Fornax-Trace", "true");
        ResponseObject resp = arkService.createResponse(request, customHeaders);
        System.out.println(resp);

        arkService.shutdownExecutor();
    }
}
```



</Tab>
</Tabs>


<span id="063cdc02"></span>
## 单例请求

请使用单例方式请求模型服务，勿重复创建实例导致额外资源消耗。


<Tabs>
<Tab zoneid="SmPOvEjnFK" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# 通过命令安装方舟SDK pip install 'volcengine-python-sdk[ark]' .
from volcenginesdkarkruntime import Ark 

client = Ark(
    # Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.environ.get("ARK_API_KEY"), 
    # The base URL for model invocation .
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)

# 请求1
completion = client.chat.completions.create(
    model="doubao-seed-2-1-pro-260628",
    messages=[
        {"role": "user", "content": "Nice day"},
    ],
)
print(completion.choices[0].message.content)


# 请求2
completion = client.chat.completions.create(
    model="doubao-seed-2-1-pro-260628",
    messages=[
        {"role": "user", "content": "Hello"},
    ],
)
print(completion.choices[0].message.content)
```



</Tab>
<Tab zoneid="kgXZPZuiN7" title="Go">
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
        os.Getenv("ARK_API_KEY"),
        arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"), // The base URL for model invocation .
    )
    ctx := context.Background()
    // 第一次请求
    req1 := model.CreateChatCompletionRequest{
       // Replace with Model ID .
       Model: "doubao-seed-2-1-pro-260628",
       Messages: []*model.ChatCompletionMessage{
          {
             Role: model.ChatMessageRoleUser,
             Content: &model.ChatCompletionMessageContent{
                StringValue: volcengine.String("Nice day"),
             },
          },
       },
    }

    resp1, err := client.CreateChatCompletion(ctx, req1)
    if err != nil {
       fmt.Printf("standard chat error: %v\n", err)
       return
    }
    fmt.Println(*resp1.Choices[0].Message.Content.StringValue)

    // 第二次请求
    req2 := model.CreateChatCompletionRequest{
       // Replace with Model ID .
       Model: "doubao-seed-2-1-pro-260628",
       Messages: []*model.ChatCompletionMessage{
          {
             Role: model.ChatMessageRoleUser,
             Content: &model.ChatCompletionMessageContent{
                StringValue: volcengine.String("Hello"),
             },
          },
       },
    }

    resp2, err := client.CreateChatCompletion(ctx, req2)
    if err != nil {
       fmt.Printf("standard chat error: %v\n", err)
       return
    }
    fmt.Println(*resp2.Choices[0].Message.Content.StringValue)
}
```



</Tab>
<Tab zoneid="eGRAghoO1R" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.example;

import com.volcengine.ark.runtime.model.completion.chat.ChatCompletionRequest;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessage;
import com.volcengine.ark.runtime.model.completion.chat.ChatMessageRole;
import com.volcengine.ark.runtime.service.ArkService;
import java.util.ArrayList;
import java.util.List;

public class ChatCompletionsExample4 {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        // The base URL for model invocation .
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();
        
        // 第一次请求
        final List<ChatMessage> messages1 = new ArrayList<>();
        final ChatMessage userMessage1 = ChatMessage.builder().role(ChatMessageRole.USER).content("今天天气不错？").build();
        messages1.add(userMessage1);
        ChatCompletionRequest chatCompletionRequest1 = ChatCompletionRequest.builder()
                .model("doubao-seed-2-1-pro-260628")// Replace with Model ID .
                .messages(messages1)
                .build();
        arkService.createChatCompletion(chatCompletionRequest1).getChoices().forEach(choice -> System.out.println(choice.getMessage().getContent()));
        // 第二次请求
        final List<ChatMessage> messages2 = new ArrayList<>();
        final ChatMessage userMessage2 = ChatMessage.builder().role(ChatMessageRole.USER).content("你好").build();
        messages2.add(userMessage2);
        ChatCompletionRequest chatCompletionRequest2 = ChatCompletionRequest.builder()
                .model("doubao-seed-2-1-pro-260628")// Replace with Model ID .
                .messages(messages2)
                .build();
        arkService.createChatCompletion(chatCompletionRequest2).getChoices().forEach(choice -> System.out.println(choice.getMessage().getContent()));
        // shutdown service
        arkService.shutdownExecutor();
    }
}
```



</Tab>
</Tabs>


<span id="065e9d3e"></span>
## 设置Base Url

初始化时 `Ark`、`AsyncArk`实例时，默认无需配置`base_url`参数，当需要连接非默认区域的服务端点时使用，示例如下。


<Tabs>
<Tab zoneid="QfzO8pvZET" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
# 通过命令安装方舟SDK pip install 'volcengine-python-sdk[ark]' .
from volcenginesdkarkruntime import Ark

client = Ark(
    api_key=os.environ.get("ARK_API_KEY"),
    # The base URL for model invocation .
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)
```



</Tab>
<Tab zoneid="mDKvg4JbWj" title="Go">
<TabTitle>Go</TabTitle>

```Go
import (
    "os"
    "github.com/volcengine/volcengine-go-sdk/service/arkruntime"
)

client := arkruntime.NewClientWithApiKey(
    os.Getenv("ARK_API_KEY"),
    arkruntime.WithBaseUrl("https://ark.cn-beijing.volces.com/api/v3"), // The base URL for model invocation .
)
```



</Tab>
<Tab zoneid="FjrIB5enFO" title="Java">
<TabTitle>Java</TabTitle>

```Java
import com.volcengine.ark.runtime.service.ArkService;

public class CreateArkClientExample {
    public static void main(String[] args) {
        String apiKey = System.getenv("ARK_API_KEY");
        ArkService service = ArkService.builder()
            .apiKey(apiKey)
            .baseUrl("https://ark.cn-beijing.volces.com/api/v3") // The base URL for model invocation .
            .build();
    }

    // do your operation...
}
```



</Tab>
</Tabs>




