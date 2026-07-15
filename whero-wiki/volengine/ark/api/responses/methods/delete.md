`DELETE https://ark.cn-beijing.volces.com/api/v3/responses/{response_id}`

本文介绍如何删除指定 ID 的模型请求。


<Tabs>
<Tab zoneid="Ptp9ccIa" title="鉴权说明">
<TabTitle>鉴权说明</TabTitle>

本接口仅支持 API Key 鉴权，请在 [获取 API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey) 页面，获取长效 API Key。


</Tab>
<Tab zoneid="IHExglzX" title="快速入门">
<TabTitle>快速入门</TabTitle>

<span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_2abecd05ca2779567c6d32f0ddc7874d.png) </span>[模型列表](https://www.volcengine.com/docs/82379/1330310)    <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_a5fdd3028d35cc512a10bd71b982b6eb.png) </span>[模型计费](https://www.volcengine.com/docs/82379/1544106)     <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_57d0bca8e0d122ab1191b40101b5df75.png) </span>[Responses API 教程](https://www.volcengine.com/docs/82379/1585128)    <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_57d0bca8e0d122ab1191b40101b5df75.png) </span>[上下文缓存教程](https://www.volcengine.com/docs/82379/1585128)    <span>![图片](https://portal.volccdn.com/obj/volcfe/cloud-universal-doc/upload_afbcf38bdec05c05089d5de5c3fd8fc8.png) </span>[API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D)


</Tab>
</Tabs>


<span id="rABtNeWs"></span>
## 请求参数

<span id="vZ8meUIu"></span>
### 路径参数


---



**response_id** `string` <span data-api-tag="require|yM0oK2">必选</span>

待删除请求的id。

&nbsp;

<span id="11E4X5If"></span>
## 响应参数


---



**id** `string`

待删除请求的id。


---



**object** `string`

固定为 `response`。


---



**deleted** `boolean`

取值范围：


* `true`：删除成功。

* `false`：未删除成功。

