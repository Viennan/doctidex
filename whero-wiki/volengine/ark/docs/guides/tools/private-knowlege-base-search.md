私域知识库搜索工具 Knowledge Search 支持通过 Responses API 调用直接获取企业私域知识库中的信息（如内部文档、产品手册、行业资料等），适用于需基于企业专属数据解答问题的场景（如内部培训问答、产品功能咨询、行业方案查询等）。工具通过模型自动判断是否需要调用私域知识库，支持与自定义 Function、MCP 等工具混合使用，当前仅支持旗舰版知识库。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">测试期间调用此工具需要增加 header '<code>ark-beta-knowledge-search: true</code>'，调用方式请参见<a href="https://www.volcengine.com/docs/82379/1873396#a6673793">快速开始</a>。</div>


<span id="520b9a86"></span>
# **核心功能**


* **精准私域检索** ：仅检索企业已授权私域知识库，保障数据安全性，适用于内部敏感信息查询场景。

* **灵活参数配置** ：支持设置搜索结果数量、关键词并行数、结果重排、获取切片中图片等参数，适配不同查询需求（如精准查询需减少结果数量，全面查询需增加关键词并行数）。


<span id="5a5a3639"></span>
# **注意事项**


*  **【重要】计费与 Tokens 说明** ：一轮搜索可能发起多个关键词并行查询，可通过返回参数`usage.tool_usage`和`usage.tool_usage_details`查看具体消耗情况。

* **Function 命名冲突** ：若用户自定义 Function 与`knowledge_search`重名，无需特殊配置，由模型根据问题场景自动判断调用哪个工具。

* **搜索改写限制** ：当前暂不支持通过参数设置改写后问题的个数，需通过`system prompt`或`instructions`控制（例如要求“每次仅生成 1 个核心搜索关键词”）。

* **知识库版本限制** ：仅支持 **旗舰版知识库** ，标准版知识库暂不支持。

* **错误信息** ：暂不支持`caching`参数，使用该参数会返回 400 错误信息。


<span id="186f4304"></span>
# **准备工作**

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">方舟平台的新用户？获取 API Key 及 开通模型等准备工作，请参见 <a href="https://www.volcengine.com/docs/82379/1399008">快速入门</a>。</div>


使用 Knowledge Search 私域知识库搜索工具前，必须完成以下准备工作。

<span id="5c62cdd1"></span>
## **1. 完成服务授权**

需先为工具授予访问知识库的权限，支持两种授权方式：


<Tabs>
<Tab zoneid="gkRIkYvRjC" title="方式 1：项目授权（推荐）">
<TabTitle>方式 1：项目授权（推荐）</TabTitle>

当前支持项目维度的快捷授权，为项目授权后，方舟服务即可访问该项目下的所有知识库。

打开控制台的[项目授权](https://console.volcengine.com/ark/region:ark+cn-beijing/projectManagement?tab=Project)页面，并为需要授权的项目点击**授权**。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">控制台默认显示<code>default</code>项目。如需为其他项目授权，请先在页面顶部切换项目。</div>


<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/c7f8d19be8944743a7ad9e0c0da1f8c1~tplv-goo7wpa0wc-image.image) </span>


</Tab>
<Tab zoneid="pRR15q2a7u" title="方式 2：IAM 授权">
<TabTitle>方式 2：IAM 授权</TabTitle>

1. 打开[新建自定义策略](https://console.volcengine.com/iam/policymanage/policy/new)页面，输入策略名称，并点击 **JSON 编辑器**标签页。

2. 将以下代码中的`<YourAccountID>`替换为您的真实账号 ID，并将这段代码粘贴至 **JSON 编辑器**标签页的文本框中。

   ```JSON
   {
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "vikingdb:*"
         ],
         "Resource": [
           "trn:ark:*:<YourAccountID>:knowledgebase/*",
         ]
       }
     ]
   }
   ```
   

3. 在页面底部点击**提交**。

4. 打开[角色管理](https://console.volcengine.com/iam/identitymanage/role)页面，新增角色，可以命名为`ArkAccessRole_项目名称`，并为该角色授予上一步创建的自定义策略。


</Tab>
</Tabs>


<span id="1a9b1ddd"></span>
## **2. 准备知识库**


* 需提前开通 **旗舰版知识库** （暂不支持标准版知识库），并完成知识库构建与数据上传，操作指南详见[创建知识库](https://www.volcengine.com/docs/82379/1261885)。

* 计费说明：私域知识库搜索的收费标准详见[知识库计费](https://www.volcengine.com/docs/82379/1263336)。

* 配额限制：知识库使用配额详见[知识库配额说明](https://www.volcengine.com/docs/82379/1343907)，需确保配额充足以避免调用失败。


<span id="a6673793"></span>
# **快速开始**

以下示例代码中，均需将`<ARK_API_KEY>`替换为实际 API Key，将`<knowledge_resource_id>`替换为授权的知识库 ID。


<Tabs>
<Tab zoneid="ZepcT2sv3k" title="cURL">
<TabTitle>cURL</TabTitle>

```Plain
curl --location 'https://ark.cn-beijing.volces.com/api/v3/responses' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <ARK_API_KEY>' \
--header 'ark-beta-knowledge-search: true' \
--data '{
    "model": "doubao-seed-2-1-pro-260628",
    "stream": true,
    "thinking": {
        "type": "disabled"  # 关闭模型思考，直接调用知识库搜索
    },
    "tools": [
        {
            "type": "knowledge_search",
            "knowledge_resource_id": "<knowledge_resource_id>",  # 替换为实际知识库ID
            "limit": 2,  # 最多返回2条搜索结果
            "ranking_options": {
                "get_attachment_link": true  # 获取图片临时下载链接
            }
        }
    ],
    "input": [
        {
            "role": "user",
            "content": "机票选择页面中，如何选择该航班不同价格的机票？"  # 用户问题
        }
    ],
    "max_tool_calls": 1  # 仅调用1轮知识库搜索
}'
```



</Tab>
<Tab zoneid="OJFczYSCo7" title="OpenAI SDK">
<TabTitle>OpenAI SDK</TabTitle>

```Python
import os
from openai import OpenAI

# 从环境变量获取API密钥，配置方法见：https://www.volcengine.com/docs/82379/1399008
api_key = os.getenv('ARK_API_KEY')

# 初始化客户端
client = OpenAI(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
    default_headers={"ark-beta-knowledge-search": "true"}  # 启用私域知识库搜索
)

# 发起知识库搜索请求
response = client.responses.create(
    model="doubao-seed-2-1-pro-260628",  # 替换为支持的模型
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "应用实验室里有类似实时视频理解的agent demo么？"  # 用户问题
                }
            ]
        }
    ],
    tools=[
        {
            "type": "knowledge_search",
            "knowledge_resource_id": "<knowledge_resource_id>",  # 替换为实际知识库ID
            "limit": 10,  # 最多返回10条搜索结果
        }
    ],
    stream=True,  # 启用流式响应，实时获取结果
    extra_body={"thinking": {"type": "auto"}}  # 模型自动判断是否需要搜索
)

# 处理流式响应
for chunk in response:
    if hasattr(chunk, 'delta'):
        print(chunk.delta, end="", flush=True)
```



</Tab>
</Tabs>


<span id="b0120dd9"></span>
# **参数说明**

详情请参见[创建 Responses 模型请求](https://www.volcengine.com/docs/82379/1569618)。

<span id="f9b9e3de"></span>
# **支持模型列表**

Knowledge Search 工具支持的模型请参考[私域知识库搜索工具](https://www.volcengine.com/docs/82379/1330310#f44ceef7)。

<span id="c9d3ed5d"></span>
# 附录：搜索模式系统提示词样例

```Plaintext
# 定义系统提示词
system_prompt = """
你是豆包个人助手，负责解答用户的各种问题。你的主要职责是：
1. **信息准确性守护者**：确保提供的信息准确无误。
2. **搜索成本优化师**：在信息准确性和搜索成本之间找到最佳平衡。
# 任务说明
## 1. 知识库意图判断
当用户提出的问题涉及以下情况时，需使用 `knowledge_search` 进行私域知识搜索：
- **企业知识**：问题有关于火山方舟、大模型、responses API
## 2. 知识库搜索后回答
- 在回答中，优先使用已搜索到的资料。
- 回复结构应清晰，使用序号、分段等方式帮助用户理解。
## 3. 引用已搜索资料
- 当使用知识库搜索的资料时，在正文中明确引用来源，引用格式为：
`[1]  (URL地址)`。
## 4. 总结与参考资料
- 在回复的最后，列出所有已参考的资料。格式为：
1. [资料标题](URL地址1)
2. [资料标题](URL地址2)
"""
```




