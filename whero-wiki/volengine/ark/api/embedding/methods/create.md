`POST https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal` [运行](https://api.volcengine.com/api-explorer/?action=EmbeddingsMultimodal&data=%7B%7D&groupName=%E5%90%91%E9%87%8F%E5%8C%96%20API&query=%7B%7D&serviceCode=ark&version=2024-01-01)

当您需通过语义来处理视频、图像和文本，如以图搜图、语义检索等，可以调用多模态向量化服务，将视频、图像和文本转化为向量，来分析其语义关系。本文为您提供接口的参数详细说明供您查阅。


<Tabs>
<Tab zoneid="tm7UL3iVmy" title="快速入口">
<TabTitle>快速入口</TabTitle>

<span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_2abecd05ca2779567c6d32f0ddc7874d.png) </span> [模型列表](https://www.volcengine.com/docs/82379/1330310?lang=zh#ee5ec35c) <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_a5fdd3028d35cc512a10bd71b982b6eb.png) </span> [模型计费](https://www.volcengine.com/docs/82379/1099320#%E6%96%87%E6%9C%AC%E5%90%91%E9%87%8F%E6%A8%A1%E5%9E%8B) <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_afbcf38bdec05c05089d5de5c3fd8fc8.png) </span> [API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D)

<span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_f45b5cd5863d1eed3bc3c81b9af54407.png) </span> [接口文档](https://www.volcengine.com/docs/82379/1523520) <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_1609c71a747f84df24be1e6421ce58f0.png) </span> [常见问题](https://www.volcengine.com/docs/82379/1359411) <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_bef4bc3de3535ee19d0c5d6c37b0ffdd.png) </span> [开通模型](https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement?LLM=%7B%7D&OpenTokenDrawer=false)


</Tab>
<Tab zoneid="pb0Q1Vkjhc" title="鉴权说明">
<TabTitle>鉴权说明</TabTitle>

本接口支持 API Key 鉴权，详见[鉴权认证方式](https://www.volcengine.com/docs/82379/1298459)。

> 如需使用 Access Key 来鉴权，推荐使用 SDK 的方式，具体请参见 [SDK概述](https://www.volcengine.com/docs/82379/1302007)。


</Tab>
</Tabs>



---



<span id="request-parameters"></span>
## 请求参数

> 跳转 [响应参数](https://www.volcengine.com/docs/82379/1523520#response-parameters)


<span id="request-body"></span>
### 请求体


---



**model** `string` `必选`

您需要调用的模型的 ID （Model ID），[开通模型服务](https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement?LLM=%7B%7D&OpenTokenDrawer=false)，并[查询 Model ID](https://www.volcengine.com/docs/82379/1330310) 。

您也可通过 Endpoint ID 来调用模型，获得限流、计费类型（前付费/后付费）、运行状态查询、监控、安全等高级能力，可参考[获取 Endpoint ID](https://www.volcengine.com/docs/82379/1099522)。


---



**input** `object[]` `必选`

需要向量化的内容列表。列表元素支持文本信息和图片信息以及视频信息。

不同模型的支持情况不同，详情请查询[文档](https://www.volcengine.com/docs/82379/1409291?lang=zh)。


属性

**文本信息** `object`

输入给模型转化为向量的内容，文本内容部分。


属性


---



input.**type** `string` `必选`

输入内容的类型，此处应为 `text`。


---



input.**text** `string` `必选`

输入给模型的文本内容。

单条文本以 utf\-8 编码，长度不超过模型的最大输入 token 数。



---



**图片信息** `object`

输入给模型转化成向量的内容，图片信息部分。

传入图片需要满足的条件请参见[文档](https://www.volcengine.com/docs/82379/1409291?lang=zh#a256838b)。


属性


---



input.**type** `string` `必选`

输入内容的类型，此处应为 `image_url`。


---



input.**image_url** `object` `必选`

输入给模型的图片对象。


属性


---



input.image_url.**url** `string` `必选`

图片信息，可以是图片URL或图片Base64编码。


* 图片URL：请确保图片URL可被访问。

* Base64编码：请遵循此格式`data:image/{图片格式};base64,{图片Base64编码}`。




---



**视频信息** `object`

输入给模型转化成向量的内容，视频信息部分。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">传入视频需要满足以下条件：</div>



* <div data-tips="true" data-tips-type="tip">格式：<code>.mp4</code>、<code>.avi</code>、 <code>.mov</code>，视频格式需小写。</div>


* <div data-tips="true" data-tips-type="tip">传入 Base64 编码时使用：<a href="https://www.volcengine.com/docs/82379/1362931?lang=zh#477e51ce">Base64 编码输入</a>。</div>


* <div data-tips="true" data-tips-type="tip">单视频文件需在 50MB 以内。</div>


* <div data-tips="true" data-tips-type="tip">暂不支持对视频文件中的音频信息进行理解。</div>




---



input.**type** `string` `必选`

输入内容的类型，此处应为 `video_url`。


---



input.**video_url** `object` `必选`

输入给模型的视频对象。


属性

input.video_url.**url** `string` `必选`

支持传入视频链接或视频的Base64编码。具体使用请参见[文档](https://www.volcengine.com/docs/82379/1362931?lang=zh#477e51ce)。


---



input.video_url.**fps** `number`

取值范围：`[0.2, 5]`。

每秒钟从视频中抽取指定数量的图像。取值越高，对于视频中画面变化理解越精细；取值越低，对于视频中画面变化感知减弱，但是使用的 token 花费少，速度也更快。该参数会直接影响视频 embedding 的抽帧数量与 token 消耗。


---



input.video_url.**max_video_tokens** `integer`

取值范围：`[10240, 204800]`。

视频最大 tokens 数，值越大保留的视频信息越多。该参数用于控制视频抽帧后最多送入模型的 token 数；超过此值时，会按帧数上限截断。


---



input.video_url.**min_frame_tokens** `integer`

取值范围：`[16, 128]`。

单帧最小 tokens 数，用于控制单帧压缩的下限。值越小，允许对单帧进行更大的压缩，但单帧细节下降；若单帧 token 过少，也会影响最终向量表征质量。


---



input.video_url.**max_frame_tokens** `integer`

取值范围：`[128, 640]`，且必须大于等于 `min_frame_tokens`。

单帧最大 tokens 数，用于控制单帧质量的上限。值越大，允许对单帧保留更多的细节；该参数会与 `max_video_tokens` 一起控制单帧和整体的 token 消耗。


---



input.video_url.**min_frames** `integer`

取值范围：`[5, 16]`。

最小抽帧数，用于保证短视频具备足够的处理帧数。若 `fps` 字段抽帧总数小于 `min_frames`，则优先按照 `min_frames` 配置要求抽帧，以避免极短视频抽不到帧。



&nbsp;

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>



* <div data-tips="true" data-tips-type="tip">视频自定义抽帧参数 <code>fps</code>、<code>max_video_tokens</code>、<code>min_frame_tokens</code>、<code>max_frame_tokens</code>、<code>min_frames</code> 均为可选参数。</div>


* <div data-tips="true" data-tips-type="tip">仅 <code>doubao-embedding-vision-251215</code> 及后续版本支持这些参数。</div>


* <div data-tips="true" data-tips-type="tip">这些字段不传时，会根据模型对应的抽帧策略使用<a href="https://www.volcengine.com/docs/82379/1895586?lang=zh#203baa92">默认值</a>。</div>


* <div data-tips="true" data-tips-type="tip">抽帧策略会综合这些参数协同生效：按 <code>fps</code> 抽帧后，每帧按 <code>max_frame_tokens</code> 控制 token 上限，总 token 数不超过 <code>max_video_tokens</code>，实际抽帧数不低于 <code>min_frames</code>。</div>


* <div data-tips="true" data-tips-type="tip">抽帧数量会直接影响视频 embedding 的 token 消耗，但并非帧数越多效果越好；若单帧 token 过少，视频 embedding 质量也会下降。</div>


* <div data-tips="true" data-tips-type="tip">建议结合 <code>max_video_tokens</code> 与 <code>min_frame_tokens</code> 进行权衡，在控制总 token 消耗的同时，保证单帧保留足够信息。</div>


* <div data-tips="true" data-tips-type="tip">当视频时长极短且 <code>fps</code> 过低，导致抽帧后实际帧数为 <code>0</code> 时，会以 <code>min_frames</code> 兜底，保证至少有帧送入编码器。</div>




---



**encoding_format** `string / null` `默认值 float`

取值范围： `float`、`base64`、`null`。

embedding 返回的格式。


---



**dimensions** `integer` `默认值 2048`

取值范围： `1024` 或 `2048`。

用于指定输出的向量维度。


---



**instructions** `string`

推理提示词，用户传入时直接使用，未传入时按输入模态生成默认值。详情请参见 [配置instructions](https://www.volcengine.com/docs/82379/1409291?lang=zh#96894c46)。


---



**sparse_embedding** `object`

稀疏向量开关配置，仅纯文本输入支持配置此字段。


属性


---



sparse_embedding.**type** `string` `默认值 disabled`

取值范围：`enabled`、`disabled`。

用于控制是否输出稀疏向量。


* `disabled`：仅输出稠密向量。

* `enabled`：同时输出稠密向量和稀疏向量。



---



**multi_embedding** `object`

多向量（multi\-vector）输出配置，控制是否输出多向量及其压缩方式。

开启后，每个输入除返回稠密向量外，额外返回一组 token 级别的向量（二维数组）。


属性


---



multi_embedding.**type** `string` `默认值 disabled`

取值范围：`enabled`、`disabled`。

多向量输出开关。


* `type="disabled"`：不输出多向量。

* `type="enabled"`：在稠密向量基础上，额外返回 `data.multi_embedding`。



---



multi_embedding.**compression** `string`

多向量的压缩方式，仅在 `type="enabled"` 时生效。传入后，`data.multi_embedding` 会返回压缩并 base64 编码后的字符串，可显著降低传输体积，客户端需按解码协议还原。

取值范围：`blosc2`、`zstd`。


* `blosc2`：专门为数字数组优化的，同样的向量能压得更小、更省带宽。

* `zstd`：通用高速压缩方式，几乎所有语言都有现成解码库，接入简单、解压快。


&nbsp;

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>



* <div data-tips="true" data-tips-type="tip"><code>multi_embedding.type="disabled"</code> 时，<code>compression</code> 字段会被忽略。</div>


* <div data-tips="true" data-tips-type="tip"><code>multi_embedding.type="enabled"</code> 且 <code>compression</code> 不传时，表示返回未压缩的二维数组。</div>


* <div data-tips="true" data-tips-type="tip"><code>multi_embedding</code> 可以与 <code>sparse_embedding</code> 同时开启，但 <code>sparse_embedding</code> 仍仅支持纯文本输入。</div>


* <div data-tips="true" data-tips-type="tip"><code>multi_embedding</code> 不允许传空对象 <code>{}</code>，否则会返回 400 <code>MissingParameter</code>。</div>


* <div data-tips="true" data-tips-type="tip">压缩与 <code>encoding_format</code> 是两个正交维度：<code>compression</code> 控制 <code>multi_embedding</code> 的压缩方式，<code>encoding_format</code> 控制向量字段整体的响应序列化格式。</div>



<span id="response-parameters"></span>
## 响应参数

> 跳转 [请求参数](https://www.volcengine.com/docs/82379/1523520#request-parameters)



---



**id** `string`

本次请求的唯一标识 。


---



**model** `string`

本次请求实际使用的模型名称和版本。


---



**created** `integer`

本次请求创建时间的 Unix 时间戳（秒）。


---



**object** `string`

固定为 `list`。


---



**data** `object`

本次请求的算法输出内容。


属性


---



data.**embedding** `float[]`

对应内容的向量化结果。


---



data.**sparse_embedding**`array`

稀疏向量，仅sparse_embedding.type="enabled"时返回；每个成员为`{"index": 维度索引, "value": 非零值}`结构，仅返回非零元素。


---



data.**multi_embedding** `float[][] / string`

多向量，仅 `multi_embedding.type="enabled"` 时返回。


* 未开启压缩时，返回 `float[][]`，外层表示 token 维度，内层表示每个 token 的子向量。

* 开启 `compression=blosc2/zstd` 时，返回经过压缩并 Base64 编码后的字符串。



---



data.**object** `string`

固定为 `embedding`。


&nbsp;

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">当 <code>data.multi_embedding</code> 以压缩字符串返回时，客户端应按以下规则解码：</div>



1. <div data-tips="true" data-tips-type="tip">对返回的 Base64 字符串进行解码，并按 <code>compression</code> 指定的算法解压。</div>


2. <div data-tips="true" data-tips-type="tip">将解压后的二进制数据按 <code>fp16</code>（2 字节，小端序）解析为一维数组。</div>


3. <div data-tips="true" data-tips-type="tip">按 <code>[num_tokens, dimensions]</code> 将一维数组重塑为二维数组。</div>



<div data-tips="true" data-tips-type="tip">压缩返回场景下，响应不会单独返回 <code>shape</code> 或 <code>dtype</code> 字段。</div>



---



**usage** `object`

本次请求的 token 用量。


属性


---



usage.**prompt_tokens** `integer`

输入内容 token 数量。


---



usage.**total_tokens** `integer`

本次请求消耗的总 token 数量（输入 + 输出）。


---



usage.**prompt_tokens_details** `object`

输入的内容使用 token 量的细节信息。


属性


---



usage.prompt_tokens_details.**text_tokens** `integer`

输入内容中，文本内容对应的 token 量，以及视频内容时间轴产生的 token 量。

为保证模型效果，当图片或视频传入时，会生成少量的预设文本 token，产生额外的 **text_tokens**。


---



usage.prompt_tokens_details.**image_tokens** `integer`

输入内容中，图片内容以及视频内容抽帧图片对应的 token 量。





