`GET https://ark.cn-beijing.volces.com/api/v3/files?after={after}&limit={limit}&purpose={purpose}&order={order}&scope_id={scope_id}`

获取文件列表。

<span id="l9Iu16WF"></span>
## 请求参数

> 跳转 [响应参数](https://www.volcengine.com/docs/82379/1870407#nby1fJFs)


<span id="eB97NMCI"></span>
### Query 参数

> 在 URL String 中传入。



---



**after** `string/ null`

返回该文件 ID 之后的文件。


---



**limit** `integer` `默认值：100`

取值范围： 1 ~ 100。

控制单次返回的最大文件数。


---



**purpose** `string`

按文件用途进行筛选，仅返回具有指定用途的文件。


---



**order** `string` `默认值：desc`

按照文件created_at的时间戳顺序，控制文件的排序方式。


* asc：按照正序排列。

* desc：按照倒序排列。



---



**scope_id** `string`

作用域 ID。当前仅支持传入会话 ID（Session ID），指定后仅返回该会话下的文件。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">注意</div>



* <div data-tips="true" data-tips-type="tip">仅适用于 <a href="https://www.volcengine.com/docs/82379/2553713">Managed Agents</a> 场景，可查询挂载至指定会话内的文件资源，包含用户挂载到该会话中的文件副本与 Agent 生成的输出文件；</div>


* <div data-tips="true" data-tips-type="tip">参数取值必须为合法有效的会话 ID。</div>



<span id="nby1fJFs"></span>
## 响应参数

> 跳转 [请求参数](https://www.volcengine.com/docs/82379/1870407#l9Iu16WF)


返回本次响应对应的文件列表。

**object** `string`

固定为`list`。


---



**data** `object[] / null`

文件的列表，与上传文件时的请求参数字段结构完全一致。


---



**first_id** `string`

列表中第一条数据的 ID。


---



**has_more** `boolean`

标识是否还有更多数据未返回。


* true：存在未返回的数据。

* false：已返回全部数据。



---



**last_id** `string`

列表中最后一条数据的 ID。



