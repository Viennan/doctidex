Image Process（图像处理）工具支持通过 Responses API 调用对输入图片执行画点、画线、旋转、缩放、框选或裁剪关键区域等基础操作，适用于需要模型通过视觉处理提升图片理解的场景（例如图文内容分析、物体定位标注、多轮视觉推理等）。工具通过模型自动判断图像处理逻辑，支持与自定义函数混合使用，且可处理多轮视觉输入（即上一轮输出的图片作为下一轮的输入）。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">当前处于 Beta 测试阶段，测试期间免费使用。</div>


<div data-tips="true" data-tips-type="tip">测试期间，调用此工具需要增加 header <code>ark-beta-image-process: true</code>，调用方式请参见<a href="https://www.volcengine.com/docs/82379/1798161#demo">功能演示</a>。</div>


<span id="a7eb296f"></span>
## 核心功能


* 丰富的图像处理工具：支持启用或禁用画点（Point）、框选（Grounding）、缩放（Zoom）、旋转（Rotate）等子功能，满足不同视觉处理需求。

* 支持多轮图像处理：复杂视觉任务（如多步缩放+旋转）支持多轮工具调用，上一轮输出图片自动作为下一轮输入（例：image0→image1→image2）。

* 支持混合调用：可与用户自定义函数混合使用。（暂不支持与 Web Search 联网内容插件混合调用）

* 兼容多种图片格式：支持 Base64 编码的 .gif、.jpg、.jpeg 等主流图片格式，但对图片规格有明确限制，详见。


<span id="demo"></span>
## 功能演示

以下示例代码演示了图像处理工具的各项功能。实际调用时，请将 `<ARK_API_KEY>` 替换为您的实际 API Key。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">方舟平台的新用户？获取 API Key 及 开通模型等准备工作，请参见 <a href="https://www.volcengine.com/docs/82379/1399008">快速入门</a>。</div>


<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">提示词支持图片和文字混排，但图文顺序可能对模型的输出效果产生影响。如果提示词由多张图片和一段文字构成，建议将文字放在提示词末尾。</div>


<span id="20fd65fa"></span>
### 示例一：缩放（Zoom）工具

以下代码展示了在视觉问答场景下，如何启用缩放（zoom）工具，让模型在放大图片后读取前方路牌文字，并以流式方式实时返回答案。


<Tabs>
<Tab zoneid="HAxBU3sKHn" title="cURL">
<TabTitle>cURL</TabTitle>

```Bash
curl --location 'https://ark.cn-beijing.volces.com/api/v3/responses' \
--header 'Authorization: Bearer <ARK_API_KEY>' \
--header 'Content-Type: application/json' \
--header 'ark-beta-image-process: true' \
--data '{
    "model": "doubao-seed-2-0-lite-260215",
    "stream": true,
    "tools": [
        {
            "type": "image_process",
            "point": {
                "type": "disabled"
            },
            "grounding": {
                "type": "disabled"
            },
            "zoom": {
                "type": "enabled"  // 启用 zoom（缩放）工具
            },
            "rotate": {
                "type": "disabled"
            }
        }
    ],
    "input": [
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"
                },
                {
                    "type": "input_text",
                    "text": "前方路牌写了什么？"
                }
            ]
        }
    ]
}'
```



</Tab>
<Tab zoneid="EaLql4fanX" title="Python">
<TabTitle>Python</TabTitle>

```Python
from volcenginesdkarkruntime import Ark
import os

# 从环境变量获取 API 密钥，配置方法见：https://www.volcengine.com/docs/82379/1399008

api_key = os.getenv('ARK_API_KEY')

# 初始化客户端，配置 API 地址与工具启用头

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# 发起图像处理请求

response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    tools=[
        {
            "type": "image_process",
            "point": {
                "type": "disabled"
            },
            "grounding": {
                "type": "disabled"
            },
            "zoom": {
                "type": "enabled"
            },
            "rotate": {
                "type": "disabled"
            }
        }
    ],
    input=[
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"  # 输入图片 URL
                },
                {
                    "type": "input_text",
                    "text": "前方路牌写了什么？"  # 系统提示文本
                }
            ]
        }
    ],
    extra_headers={"ark-beta-image-process": "true"},
    stream=True  # 启用流式响应，实时获取处理结果
)

# 打印流式响应结果

for chunk in response:
    if hasattr(chunk, 'delta'):
        print(chunk.delta, end="", flush=True)

```



</Tab>
<Tab zoneid="e0yZWPVtuH" title="OpenAI Python SDK">
<TabTitle>OpenAI Python SDK</TabTitle>

```Python
from openai import OpenAI
import os

# 从环境变量获取API密钥，配置方法见：https://www.volcengine.com/docs/82379/1399008
api_key = os.getenv('ARK_API_KEY')

# 初始化客户端，配置API地址与工具启用头
client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
    default_headers={"ark-beta-image-process": "true"}
)

# 发起图像处理请求
response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    tools=[
        {
            "type": "image_process",
            "point": {
                "type": "disabled"
            },
            "grounding": {
                "type": "disabled"
            },
            "zoom": {
                "type": "enabled" # 启用缩放（zoom）工具
            },
            "rotate": {
                "type": "disabled"
            }
        }
    ],
    input=[
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"  # 输入图片 URL
                },
                {
                    "type": "input_text",
                    "text": "前方路牌写了什么？"  # 系统提示文本
                }
            ]
        }
    ],
    stream=True  # 启用流式响应，实时获取处理结果
)

# 打印流式响应结果
for chunk in response:
    if hasattr(chunk, 'delta'):
        print(chunk.delta, end="", flush=True)
```



</Tab>
<Tab zoneid="QUR3nghhuS" title="OpenAI Go SDK">
<TabTitle>OpenAI Go SDK</TabTitle>

```Go
package main
import (
    "context"
    "fmt"
    "github.com/openai/openai-go/v3"
    "github.com/openai/openai-go/v3/option"
    "github.com/openai/openai-go/v3/responses"
)
func main() {
    client: = openai.NewClient(option.WithBaseURL("https://ark.cn-beijing.volces.com/api/v3"))
    ctx: = context.Background()
    tools: = [] map[string] any {
        {
            "type": "image_process",
            "point": {
                "type": "disabled"
            },
            "grounding": {
                "type": "disabled"
            },
            "zoom": {
                "type": "enabled" // 启用缩放（zoom）工具
            },
            "rotate": {
                "type": "disabled"
            }
        }
    }
    stream: = client.Responses.NewStreaming(ctx, responses.ResponseNewParams {
        Input: responses.ResponseNewParamsInputUnion {
            OfInputItemList: [] responses.ResponseInputItemUnionParam {
                {
                    OfInputMessage: & responses.ResponseInputItemMessageParam {
                        Role: string(responses.ResponseInputMessageItemRoleUser),
                        Content: [] responses.ResponseInputContentUnionParam {
                            {
                                OfInputImage: & responses.ResponseInputImageParam {
                                    ImageURL: openai.String("https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"),
                                },
                            }, {
                                OfInputText: & responses.ResponseInputTextParam {
                                    Text: "前方路牌写了什么？",
                                },
                            },
                        },
                    },
                },
            }
        },
        Model: "doubao-seed-2-0-lite-260215",
    }, option.WithJSONSet("tools", tools), option.WithHeaderAdd("ark-beta-image-process", "true"))
    for stream.Next() {
        data: = stream.Current()
        fmt.Println(data.RawJSON())
    }
    if stream.Err() != nil {
        panic(stream.Err())
    }
}

```



</Tab>
<Tab zoneid="SwXeUtDNNo" title="效果演示">
<TabTitle>效果演示</TabTitle>

<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/54abc77a5e9f4095956cfe602695c503~tplv-goo7wpa0wc-image.image) </span>


</Tab>
</Tabs>


<span id="3b1f0d0f"></span>
### 示例二：画点（Point）工具

以下代码展示了如何启用画点（point）工具，让模型在视觉问答中进行计数，并以流式方式返回答案。


<Tabs>
<Tab zoneid="VbVD3binL5" title="cURL">
<TabTitle>cURL</TabTitle>

```Bash
curl --location 'https://ark.cn-beijing.volces.com/api/v3/responses' \
--header 'Authorization: Bearer <ARK_API_KEY>' \
--header 'Content-Type: application/json' \
--header 'ark-beta-image-process: true' \
--data '{
    "model": "doubao-seed-2-0-lite-260215",
    "stream": true,
    "tools": [
        {
            "type": "image_process",
            "point": {
                "type": "enabled"  // 启用画点（point）工具
            },
            "grounding": {
                "type": "disabled"
            },
            "zoom": {
                "type": "disabled"
            },
            "rotate": {
                "type": "disabled"
            }
        }
    ],
    "input": [
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_2.jpg"
                },
                {
                    "type": "input_text",
                    "text": "数一数有多少颗草莓？"
                }
            ]
        }
    ]
}'
```



</Tab>
<Tab zoneid="rgz3wScrEY" title="Python">
<TabTitle>Python</TabTitle>

```Python
from volcenginesdkarkruntime import Ark
import os

# 从环境变量获取 API 密钥，配置方法见：https://www.volcengine.com/docs/82379/1399008

api_key = os.getenv('ARK_API_KEY')

# 初始化客户端，配置 API 地址与工具启用头

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# 发起图像处理请求

response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    tools=[
        {
            "type": "image_process",
            "point": {
                "type": "enabled" # 启用画点（point）工具
            },
            "grounding": {
                "type": "disabled"
            },
            "zoom": {
                "type": "disabled"
            },
            "rotate": {
                "type": "disabled"
            }
        }
    ],
    input=[
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_2.jpg"  # 输入图片 URL
                },
                {
                    "type": "input_text",
                    "text": "数一数有多少颗草莓？"  # 系统提示文本
                }
            ]
        }
    ],
    extra_headers={"ark-beta-image-process": "true"},
    stream=True  # 启用流式响应，实时获取处理结果
)

# 打印流式响应结果

for chunk in response:
    if hasattr(chunk, 'delta'):
        print(chunk.delta, end="", flush=True)

```



</Tab>
<Tab zoneid="HPs5ONuyP1" title="OpenAI Python SDK">
<TabTitle>OpenAI Python SDK</TabTitle>

```Python
from openai import OpenAI
import os

# 从环境变量获取API密钥，配置方法见：https://www.volcengine.com/docs/82379/1399008
api_key = os.getenv('ARK_API_KEY')

# 初始化客户端，配置API地址与工具启用头
client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
    default_headers={"ark-beta-image-process": "true"}
)

# 发起图像处理请求
response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    tools=[
        {
            "type": "image_process",
            "point": {
                "type": "enabled" # 启用画点（point）工具
            },
            "grounding": {
                "type": "disabled"
            },
            "zoom": {
                "type": "disabled"
            },
            "rotate": {
                "type": "disabled"
            }
        }
    ],
    input=[
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_2.jpg"  # 输入图片 URL
                },
                {
                    "type": "input_text",
                    "text": "数一数有多少颗草莓？"  # 系统提示文本
                }
            ]
        }
    ],
    stream=True  # 启用流式响应，实时获取处理结果
)

# 打印流式响应结果
for chunk in response:
    if hasattr(chunk, 'delta'):
        print(chunk.delta, end="", flush=True)
```



</Tab>
<Tab zoneid="aISxoDHGnw" title="OpenAI Go SDK">
<TabTitle>OpenAI Go SDK</TabTitle>

```Go
package main
import (
    "context"
    "fmt"
    "github.com/openai/openai-go/v3"
    "github.com/openai/openai-go/v3/option"
    "github.com/openai/openai-go/v3/responses"
)
func main() {
    client: = openai.NewClient(option.WithBaseURL("https://ark.cn-beijing.volces.com/api/v3"))
    ctx: = context.Background()
    tools: = [] map[string] any {
        {
            "type": "image_process",
            "point": {
                "type": "enabled"  // 启用画点（point）工具
            },
            "grounding": {
                "type": "disabled"
            },
            "zoom": {
                "type": "disabled"
            },
            "rotate": {
                "type": "disabled"
            }
        }
    }
    stream: = client.Responses.NewStreaming(ctx, responses.ResponseNewParams {
        Input: responses.ResponseNewParamsInputUnion {
            OfInputItemList: [] responses.ResponseInputItemUnionParam {
                {
                    OfInputMessage: & responses.ResponseInputItemMessageParam {
                        Role: string(responses.ResponseInputMessageItemRoleUser),
                        Content: [] responses.ResponseInputContentUnionParam {
                            {
                                OfInputImage: & responses.ResponseInputImageParam {
                                    ImageURL: openai.String("https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_2.jpg"),
                                },
                            }, {
                                OfInputText: & responses.ResponseInputTextParam {
                                    Text: "数一数有多少颗草莓？",
                                },
                            },
                        },
                    },
                },
            }
        },
        Model: "doubao-seed-2-0-lite-260215",
    }, option.WithJSONSet("tools", tools), option.WithHeaderAdd("ark-beta-image-process", "true"))
    for stream.Next() {
        data: = stream.Current()
        fmt.Println(data.RawJSON())
    }
    if stream.Err() != nil {
        panic(stream.Err())
    }
}

```



</Tab>
<Tab zoneid="igXRV7E7fe" title="效果演示">
<TabTitle>效果演示</TabTitle>

<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/cecc489854ed4f4e8a5476f5e92cacfa~tplv-goo7wpa0wc-image.image) </span>


</Tab>
</Tabs>


<span id="grounding_example"></span>
### 示例三：框选（Grounding）工具

以下代码展示了如何启用框选（grounding）工具，让模型框选出图中的特定目标，并以流式方式返回答案。


<Tabs>
<Tab zoneid="CY2jL5tETI" title="cURL">
<TabTitle>cURL</TabTitle>

```Bash
curl --location 'https://ark.cn-beijing.volces.com/api/v3/responses' \
--header 'Authorization: Bearer <ARK_API_KEY>' \
--header 'Content-Type: application/json' \
--header 'ark-beta-image-process: true' \
--data '{
    "model": "doubao-seed-2-0-lite-260215",
    "stream": true,
    "tools": [
        {
            "type": "image_process",
            "point": {
                "type": "disabled"
            },
            "grounding": {
                "type": "enabled"  // 启用框选（grounding）工具
            },
            "zoom": {
                "type": "disabled"
            },
            "rotate": {
                "type": "disabled"
            }
        }
    ],
    "input": [
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"
                },
                {
                    "type": "input_text",
                    "text": "帮我框选出图中的路牌。"
                }
            ]
        }
    ]
}'
```



</Tab>
<Tab zoneid="metbOeJ6k4" title="Python">
<TabTitle>Python</TabTitle>

```Python
from volcenginesdkarkruntime import Ark
import os

# 从环境变量获取 API 密钥，配置方法见：https://www.volcengine.com/docs/82379/1399008

api_key = os.getenv('ARK_API_KEY')

# 初始化客户端，配置 API 地址与工具启用头

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# 发起图像处理请求

response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    tools=[
        {
            "type": "image_process",
            "point": {
                "type": "disabled"
            },
            "grounding": {
                "type": "enabled" # 启用框选（grounding）工具
            },
            "zoom": {
                "type": "disabled"
            },
            "rotate": {
                "type": "disabled"
            }
        }
    ],
    input=[
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"  # 输入图片 URL
                },
                {
                    "type": "input_text",
                    "text": "帮我框选出图中的路牌。"  # 系统提示文本
                }
            ]
        }
    ],
    extra_headers={"ark-beta-image-process": "true"},
    stream=True  # 启用流式响应，实时获取处理结果
)

# 打印流式响应结果

for chunk in response:
    if hasattr(chunk, 'delta'):
        print(chunk.delta, end="", flush=True)

```



</Tab>
<Tab zoneid="zq4Tt5g8s8" title="OpenAI Python SDK">
<TabTitle>OpenAI Python SDK</TabTitle>

```Python
from openai import OpenAI
import os

# 从环境变量获取API密钥，配置方法见：https://www.volcengine.com/docs/82379/1399008
api_key = os.getenv('ARK_API_KEY')

# 初始化客户端，配置API地址与工具启用头
client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
    default_headers={"ark-beta-image-process": "true"}
)

# 发起图像处理请求
response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    tools=[
        {
            "type": "image_process",
            "point": {
                "type": "disabled"
            },
            "grounding": {
                "type": "enabled" # 启用框选（grounding）工具
            },
            "zoom": {
                "type": "disabled"
            },
            "rotate": {
                "type": "disabled"
            }
        }
    ],
    input=[
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"  # 输入图片 URL
                },
                {
                    "type": "input_text",
                    "text": "帮我框选出图中的路牌。"  # 系统提示文本
                }
            ]
        }
    ],
    stream=True  # 启用流式响应，实时获取处理结果
)

# 打印流式响应结果
for chunk in response:
    if hasattr(chunk, 'delta'):
        print(chunk.delta, end="", flush=True)
```



</Tab>
<Tab zoneid="GCiuXt1Hyi" title="OpenAI Go SDK">
<TabTitle>OpenAI Go SDK</TabTitle>

```Go
package main
import (
    "context"
    "fmt"
    "github.com/openai/openai-go/v3"
    "github.com/openai/openai-go/v3/option"
    "github.com/openai/openai-go/v3/responses"
)
func main() {
    client := openai.NewClient(option.WithBaseURL("https://ark.cn-beijing.volces.com/api/v3"))
    ctx := context.Background()
    tools := []map[string]any{
        {
            "type": "image_process",
            "point": map[string]string{
                "type": "disabled",
            },
            "grounding": map[string]string{
                "type": "enabled", // 启用框选（grounding）工具
            },
            "zoom": map[string]string{
                "type": "disabled",
            },
            "rotate": map[string]string{
                "type": "disabled",
            },
        },
    }
    stream := client.Responses.NewStreaming(ctx, responses.ResponseNewParams{
        Input: responses.ResponseNewParamsInputUnion{
            OfInputItemList: []responses.ResponseInputItemUnionParam{
                {
                    OfInputMessage: &responses.ResponseInputItemMessageParam{
                        Role: openai.F(responses.ResponseInputMessageItemRoleUser),
                        Content: openai.F([]responses.ResponseInputContentUnionParam{
                            {
                                OfInputImage: &responses.ResponseInputImageParam{
                                    ImageURL: openai.String("https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"),
                                },
                            }, {
                                OfInputText: &responses.ResponseInputTextParam{
                                    Text: openai.F("帮我框选出图中的路牌。"),
                                },
                            },
                        }),
                    },
                },
            },
        },
        Model: openai.F("doubao-seed-2-0-lite-260215"),
    }, option.WithJSONSet("tools", tools), option.WithHeaderAdd("ark-beta-image-process", "true"))
    for stream.Next() {
        data := stream.Current()
        fmt.Println(data.RawJSON())
    }
    if stream.Err() != nil {
        panic(stream.Err())
    }
}

```



</Tab>
</Tabs>


<span id="rotate_example"></span>
### 示例四：旋转（Rotate）工具

以下代码展示了如何启用旋转（rotate）工具，让模型对图像进行旋转操作，并以流式方式返回答案。


<Tabs>
<Tab zoneid="UlSbgSabia" title="cURL">
<TabTitle>cURL</TabTitle>

```Bash
curl --location 'https://ark.cn-beijing.volces.com/api/v3/responses' \
--header 'Authorization: Bearer <ARK_API_KEY>' \
--header 'Content-Type: application/json' \
--header 'ark-beta-image-process: true' \
--data '{
    "model": "doubao-seed-2-0-lite-260215",
    "stream": true,
    "tools": [
        {
            "type": "image_process",
            "point": {
                "type": "disabled"
            },
            "grounding": {
                "type": "disabled"
            },
            "zoom": {
                "type": "disabled"
            },
            "rotate": {
                "type": "enabled"  // 启用旋转（rotate）工具
            }
        }
    ],
    "input": [
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"
                },
                {
                    "type": "input_text",
                    "text": "帮我把图片顺时针旋转90度。"
                }
            ]
        }
    ]
}'
```



</Tab>
<Tab zoneid="v9oP2Eawwx" title="Python">
<TabTitle>Python</TabTitle>

```Python
from volcenginesdkarkruntime import Ark
import os

# 从环境变量获取 API 密钥，配置方法见：https://www.volcengine.com/docs/82379/1399008

api_key = os.getenv('ARK_API_KEY')

# 初始化客户端，配置 API 地址与工具启用头

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
)

# 发起图像处理请求

response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    tools=[
        {
            "type": "image_process",
            "point": {
                "type": "disabled"
            },
            "grounding": {
                "type": "disabled"
            },
            "zoom": {
                "type": "disabled"
            },
            "rotate": {
                "type": "enabled" # 启用旋转（rotate）工具
            }
        }
    ],
    input=[
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"  # 输入图片 URL
                },
                {
                    "type": "input_text",
                    "text": "帮我把图片顺时针旋转 90 度。"  # 系统提示文本
                }
            ]
        }
    ],
    extra_headers={"ark-beta-image-process": "true"},
    stream=True  # 启用流式响应，实时获取处理结果
)

# 打印流式响应结果

for chunk in response:
    if hasattr(chunk, 'delta'):
        print(chunk.delta, end="", flush=True)

```



</Tab>
<Tab zoneid="CtItybsq2J" title="OpenAI Python SDK">
<TabTitle>OpenAI Python SDK</TabTitle>

```Python
from openai import OpenAI
import os

# 从环境变量获取API密钥，配置方法见：https://www.volcengine.com/docs/82379/1399008
api_key = os.getenv('ARK_API_KEY')

# 初始化客户端，配置API地址与工具启用头
client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
    default_headers={"ark-beta-image-process": "true"}
)

# 发起图像处理请求
response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    tools=[
        {
            "type": "image_process",
            "point": {
                "type": "disabled"
            },
            "grounding": {
                "type": "disabled"
            },
            "zoom": {
                "type": "disabled"
            },
            "rotate": {
                "type": "enabled" # 启用旋转（rotate）工具
            }
        }
    ],
    input=[
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"  # 输入图片 URL
                },
                {
                    "type": "input_text",
                    "text": "帮我把图片顺时针旋转90度。"  # 系统提示文本
                }
            ]
        }
    ],
    stream=True  # 启用流式响应，实时获取处理结果
)

# 打印流式响应结果
for chunk in response:
    if hasattr(chunk, 'delta'):
        print(chunk.delta, end="", flush=True)
```



</Tab>
<Tab zoneid="gbhvb6eDrf" title="OpenAI Go SDK">
<TabTitle>OpenAI Go SDK</TabTitle>

```Go
package main
import (
    "context"
    "fmt"
    "github.com/openai/openai-go/v3"
    "github.com/openai/openai-go/v3/option"
    "github.com/openai/openai-go/v3/responses"
)
func main() {
    client := openai.NewClient(option.WithBaseURL("https://ark.cn-beijing.volces.com/api/v3"))
    ctx := context.Background()
    tools := []map[string]any{
        {
            "type": "image_process",
            "point": map[string]string{
                "type": "disabled",
            },
            "grounding": map[string]string{
                "type": "disabled",
            },
            "zoom": map[string]string{
                "type": "disabled",
            },
            "rotate": map[string]string{
                "type": "enabled", // 启用旋转（rotate）工具
            },
        },
    }
    stream := client.Responses.NewStreaming(ctx, responses.ResponseNewParams{
        Input: responses.ResponseNewParamsInputUnion{
            OfInputItemList: []responses.ResponseInputItemUnionParam{
                {
                    OfInputMessage: &responses.ResponseInputItemMessageParam{
                        Role: openai.F(responses.ResponseInputMessageItemRoleUser),
                        Content: openai.F([]responses.ResponseInputContentUnionParam{
                            {
                                OfInputImage: &responses.ResponseInputImageParam{
                                    ImageURL: openai.String("https://ark-project.tos-cn-beijing.volces.com/doc_image/image_process_1.jpg"),
                                },
                            }, {
                                OfInputText: &responses.ResponseInputTextParam{
                                    Text: openai.F("帮我把图片顺时针旋转 90 度。"),
                                },
                            },
                        }),
                    },
                },
            },
        },
        Model: openai.F("doubao-seed-2-0-lite-260215"),
    }, option.WithJSONSet("tools", tools), option.WithHeaderAdd("ark-beta-image-process", "true"))
    for stream.Next() {
        data := stream.Current()
        fmt.Println(data.RawJSON())
    }
    if stream.Err() != nil {
        panic(stream.Err())
    }
}

```



</Tab>
</Tabs>


<span id="4b0812aa"></span>
## 支持的模型

参见[工具调用能力](https://www.volcengine.com/docs/82379/1330310#f44ceef7)。

<span id="5e431888"></span>
## 计费说明


* **公测期间** ：暂时免费使用，无额外收费。

* 我们将会提前 2 周通过官方渠道告知具体收费标准，保障您的使用权益。


<span id="notice"></span>
## 注意事项


* **函数命名冲突** ：若用户自定义函数与 `image_process` 重名，由模型自行判断调用何种工具（无需额外配置）。

* **图片规格限制** （超出规格将导致处理失败）：

   * 文件体积 ≤ 10MB

   * 总像素 ≤ 36000000 像素

   * 图片宽和高的长度 \> 14 像素

   * 长宽比 < 150:1

* **文件格式支持情况** ：

   * **支持** .gif、.jpg、.jpeg、.png、.webp、.bmp、.tiff、.ico、.icns、.jp2 格式。

   * **不支持** .dib、.sgi、.heic、.heif 格式。

* **功能限制** ：

   * 当前不支持与 Web Search（联网内容插件）工具混合使用，也不支持通过 `tool_choice` 参数指定调用 image_process。

   * 暂不支持 `caching` 参数，使用该参数会返回 400 错误信息。

* **Tokens 消费提示** ：多轮图像处理会增加 Tokens 消费（上一轮图片输入会计入下一轮 Tokens），需注意调用成本。




