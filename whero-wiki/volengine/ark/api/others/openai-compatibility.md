为方便您集成和使用，火山方舟模型 API 会尽可能兼容 OpenAI API。修改 `base url`、`model` 、`api_key`等少量配置，轻松将方舟模型服务集成到您已有的系统中。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">社区第三方 SDK 不由火山引擎团队维护，本文仅供参考。</div>


<span id="509924d1"></span>
# 前提条件

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">方舟平台的新用户？获取 API Key 及 开通模型等准备工作，请参见 <a href="https://www.volcengine.com/docs/82379/1399008">快速入门</a>。</div>


<span id="fe0e81ca"></span>
# OpenAI SDK


* Python版本：3.7及以上。

* OpenAI SDK：1.0版本及以上，安装命令：


```Python
pip install --upgrade "openai>=1.0"
```


<span id="0569f4fe"></span>
## 快速开始示例

```Python
from openai import OpenAI
import os

client = OpenAI(   
    # The base URL for model invocation
    base_url="https://ark.cn-beijing.volces.com/api/v3",   
    # Replace with your API Key
    api_key=os.environ.get("ARK_API_KEY"), 
)

completion = client.chat.completions.create(
    # Replace with Model ID
    model="doubao-seed-2-1-pro-260628", 
    messages = [
        {"role": "user", "content": "Hello"},
    ],
)
print(completion.choices[0].message.content)
```


<span id="922db236"></span>
## 设置额外字段

传入OpenAI SDK中不支持的字段，可以通过 **extra_body** 字典传入，如开关模型是否深度思考的 **thinking** 字段。

```Python
from openai import OpenAI
import os

client = OpenAI(   
    # The base URL for model invocation 
    base_url="https://ark.cn-beijing.volces.com/api/v3",  
    # Replace with your API Key 
    api_key=os.environ.get("ARK_API_KEY"), 
)

completion = client.chat.completions.create(
    # Replace with Model ID
    model="doubao-seed-2-1-pro-260628", 
    messages = [
        {"role": "user", "content": "Hello"},
    ],
    extra_body={
         "thinking": {
             "type": "disabled", # 不使用深度思考能力
             # "type": "enabled", # 使用深度思考能力
         }
     }
)
print(completion.choices[0].message.content)
```


<span id="1cd60a34"></span>
## 设置自定义header

可以用于传递额外信息，如配置 ID来串联日志，使能数据加密能力。

```Python
from openai import OpenAI
import os

client = OpenAI(   
    # The base URL for model invocation
    base_url="https://ark.cn-beijing.volces.com/api/v3",  
    # Replace with your API Key
    api_key=os.environ.get("ARK_API_KEY"), 
)

completion = client.chat.completions.create(
    # Replace with Model ID
    model="doubao-seed-2-1-pro-260628", 
    messages = [
        {"role": "user", "content": "Hello"},
    ],
    # 自定义request id
    extra_headers={"X-Client-Request-Id": "202406251728190000B7EA7A9648AC08D9"}
)
print(completion.choices[0].message.content)
```


<span id="ab87fab7"></span>
## 向量化 Embedding

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>



* <div data-tips="true" data-tips-type="warning">文本向量化模型已经逐步下线，建议您使用多模态向量化模型。</div>


* <div data-tips="true" data-tips-type="warning"><a href="https://www.volcengine.com/docs/82379/1330310#ee5ec35c">向量化能力</a>模型不支持 OpenAI API ，请使用 方舟 SDK，详细请参见 <a href="https://www.volcengine.com/docs/82379/1409291">向量化</a>。</div>



<span id="697a06ce"></span>
# LangChain OpenAI SDK

安装 LangChain OpenAI SDK：

```Python
pip install langchain-openai
```


<span id="2bcdd714"></span>
## 示例代码

```Python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import os

llm = ChatOpenAI(
    # Replace with your API Key     
    openai_api_key=os.environ.get("ARK_API_KEY"), 
    # The base URL for model invocation
    openai_api_base="https://ark.cn-beijing.volces.com/api/v3",   
    # Replace with Model ID
    model="doubao-seed-2-1-pro-260628", 
)

template = """Question: {question}

Answer: Let's think step by step."""

prompt = PromptTemplate.from_template(template)

question = "What NFL team won the Super Bowl in the year Justin Beiber was born?"

llm_chain = prompt | llm

print(llm_chain.invoke(question))
```




