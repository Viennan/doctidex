<span id="01a681e5"></span>
# 快速调用

完成首次 API 调用，请参见 [快速入门](https://www.volcengine.com/docs/82379/1399008)


<Tabs>
<Tab zoneid="M34XQp2HPR" title="Python">
<TabTitle>Python</TabTitle>

```Python
import os
from volcenginesdkarkruntime import Ark

client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    # Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'),
)

response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input="hello", # Replace with your prompt
    # thinking={"type": "disabled"}, #  Manually disable deep thinking
)
print(response)
```



</Tab>
<Tab zoneid="SJOrjdvAnW" title="Curl">
<TabTitle>Curl</TabTitle>

```Bash
# Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
      "model": "doubao-seed-2-1-pro-260628",
      "input": "hello"
  }'
```



</Tab>
<Tab zoneid="TZ6OvmPTyM" title="Go">
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
        Model: "doubao-seed-2-1-pro-260628",
        Input: &responses.ResponsesInput{Union: &responses.ResponsesInput_StringValue{StringValue: "hello"}}, // Replace with your prompt
        // Thinking: &responses.ResponsesThinking{Type: responses.ThinkingType_disabled.Enum()}, // Manually disable deep thinking
    })
    if err != nil {
        fmt.Printf("response error: %v\n", err)
        return
    }
    fmt.Println(resp)
}
```



</Tab>
<Tab zoneid="oaIjmZCgqK" title="Java">
<TabTitle>Java</TabTitle>

```Java
package com.ark.sample;

import com.volcengine.ark.runtime.service.ArkService;
import com.volcengine.ark.runtime.model.responses.request.*;
import com.volcengine.ark.runtime.model.responses.response.ResponseObject;

public class demo {
    public static void main(String[] args) {
        // Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
        String apiKey = System.getenv("ARK_API_KEY");
        // The base URL for model invocation
        ArkService arkService = ArkService.builder().apiKey(apiKey).baseUrl("https://ark.cn-beijing.volces.com/api/v3").build();

        CreateResponsesRequest request = CreateResponsesRequest.builder()
                .model("doubao-seed-2-1-pro-260628")
                .input(ResponsesInput.builder().stringValue("hello").build()) // Replace with your prompt
                // .thinking(ResponsesThinking.builder().type(ResponsesConstants.THINKING_TYPE_DISABLED).build()) //  Manually disable deep thinking
                .build();

        ResponseObject resp = arkService.createResponse(request);
        System.out.println(resp);

        arkService.shutdownExecutor();
    }
}
```



</Tab>
<Tab zoneid="ke0iX3FnLh" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI

client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    # Get API Key: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
    api_key=os.getenv('ARK_API_KEY'),
)

response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",
    input="hello", # Replace with your prompt
    extra_body={
        # "thinking": {"type": "disabled"}, #  Manually disable deep thinking
    },
)

print(response)
```



</Tab>
</Tabs>


<span id="fc299dc6"></span>
# 浏览模型

完整模型列表：[模型列表](https://www.volcengine.com/docs/82379/1330310)


<columns>
<columnsItem zoneid="G2n0KcmiF2">


<card mode="container" href="https://console.volcengine.com/ark/region:ark+cn-beijing/model/detail?Id=doubao-seed-2-1-pro" img="https://arkdoc.tos-cn-beijing.volces.com/images/get-started/vision.png" >

**Doubao Seed 2.1**

豆包旗舰级 Agent 通用模型

面向生产级任务，全面升级编程、智能体与多模态能力

</card>



</columnsItem>
<columnsItem zoneid="XYKNFsg2MU">


<card mode="container" href="https://console.volcengine.com/ark/region:ark+cn-beijing/model/detail?Id=doubao-seed-evolving" img="https://arkdoc.tos-cn-beijing.volces.com/images/get-started/doubao-seed-1.6-vision.png" >

**Doubao Seed Evolving**

Seed 最新 Coding&Agent 模型

周级迭代，持续进化 Coding 与 Agent 能力

</card>



</columnsItem>
<columnsItem zoneid="NBATjTuYKp">


<card mode="container" href="https://console.volcengine.com/ark/region:ark+cn-beijing/model/detail?Id=doubao-seedance-2-0" img="https://ark-project.tos-cn-beijing.volces.com/doc_model/banner_video_generation.png" >

**Doubao Seedance 2.0**

豆包最强视频生成模型

极致拟真的视听稳定，赋予创作者如同导演般的掌控权

</card>



</columnsItem>
</columns>


<span id="bfd5f286"></span>
# 基础使用

了解模型使用方法、限制以及常见场景的示例代码。


<columns>
<columnsItem zoneid="NijQQNA8EP">


<card mode="section" href="/docs/82379/1449737" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/deep-thinking.svg" iconsize="m" horizontal="true" >

深度思考

先思考再回答，质量显著提升

</card>




<card mode="section" href="/docs/82379/1362931" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/image-understanding.svg" iconsize="m" horizontal="true" >

图片理解

接收图片，根据图片信息回复

</card>




<card mode="section" href="/docs/82379/1895586" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/video-understanding.svg" iconsize="m" horizontal="true" >

视频理解

接收视频，根据视频信息回复

</card>




<card mode="section" href="/docs/82379/1902647" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/document-understanding.svg" iconsize="m" horizontal="true" >

文档理解

接收 PDF，根据文档信息回复

</card>



</columnsItem>
<columnsItem zoneid="Sud7lBTzcT">


<card mode="section" href="/docs/82379/2298881" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/video-generation.svg" iconsize="m" horizontal="true" >

视频生成

生成高清流畅的影视级视频

</card>




<card mode="section" href="/docs/82379/1824121" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/image-generation.svg" iconsize="m" horizontal="true" >

图片生成

基于图文，生成高质量图片

</card>




<card mode="section" href="/docs/82379/1756990" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/web-search.svg" iconsize="m" horizontal="true" >

联网搜索

联网获取实时知识

</card>




<card mode="section" href="/docs/82379/1262342" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/function-calling.svg" iconsize="m" horizontal="true" >

函数调用

调用自定义工具，增强模型能力

</card>



</columnsItem>
</columns>


<span id="238fb521"></span>
# 进阶使用

了解如何拓展模型能力、提升性能、降低成本


<columns>
<columnsItem zoneid="RhfMSo5ZWn">


<card mode="section" href="/docs/82379/1359497" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/prefill.svg" iconsize="m" horizontal="true" >

续写模式

预填部分 \`assistant\` 消息内容，引导和控制模型输出

</card>




<card mode="section" href="/docs/82379/1616136" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/grounding.svg" iconsize="m" horizontal="true" >

视觉定位

在图片中找到对应的目标，并返回目标的坐标

</card>




<card mode="section" href="/docs/82379/1885708" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/file-api.svg" iconsize="m" horizontal="true" >

文件输入

使用 File API 上传并预处理视频、图片、PDF

</card>




<card mode="section" href="/docs/82379/1874993" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/3D-generation.svg" iconsize="m" horizontal="true" >

3D 生成

快速生成具备多边形面片与 PBR 材质的高精度 3D 资产

</card>



</columnsItem>
<columnsItem zoneid="WEt502X8FV">


<card mode="section" href="/docs/82379/1399517" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/batch.svg" iconsize="m" horizontal="true" >

批量推理

大幅提升吞吐，降低成本，适合无需即时响应的任务

</card>




<card mode="section" href="/docs/82379/1602228" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/context-caching.svg" iconsize="m" horizontal="true" >

上下文缓存

缓存固定上下文，减少重复计算开销，降低成本

</card>




<card mode="section" href="/docs/82379/1827534" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/MCP.svg" iconsize="m" horizontal="true" >

云部署 MCP

调用各类垂直领域 MCP 工具，增强模型能力

</card>




<card mode="section" href="/docs/82379/1584296" icon="https://ark-project.tos-cn-beijing.volces.com/doc_model/svg/gui.svg" iconsize="m" horizontal="true" >

GUI 任务处理

在计算机等真实 GUI 环境中完成自动化任务

</card>



</columnsItem>
</columns>




