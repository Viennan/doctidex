万相-文生视频模型支持**多模态输入**（文本/图像/音频），可生成最长15秒、分辨率为1080P的视频。

-   **基础能力**：支持整数级视频时长（2～15 秒）、指定视频分辨率（480P/720P/1080P）、智能改写prompt、添加水印。
    
-   **音频能力**：支持自动配音，或传入自定义音频文件，实现声画同步。**（wan2.7/wan2.6/wan2.5）**
    
-   **多镜头叙事**：支持生成包含多个镜头的视频，在镜头切换的同时保持主体一致。**（wan2.7/wan2.6）**
    

## **快速开始**

| **输入提示词** | **输出视频（多镜头，有声视频）** |
| --- | --- |
| **第1个镜头**大远景开篇，镜头从接近地面的低机位开始向前移动，镜头沿草原方向推进，同时向上移动，将视角从贴地逐渐抬升至略高位置，使猎豹从左侧进入画面并与前方逃窜的羚羊共同处于同一追逐路径中，建立清晰的前后空间关系。 **第2个镜头**向下移动回到接近地面高度，并沿猎豹运动方向向右移动，与其保持侧向平行关系进行稳定跟随，主体始终处于画面中部偏左位置，背景产生连续横向位移效果，在这一阶段镜头运动保持稳定一段时间以强化速度感与空间连续性。 **第3个镜头**在维持向右移动的同时，沿猎豹运动路径内侧做小幅弧线移动，使画面产生轻微绕行变化但始终保持与主体同向。 **第4个镜头**逐渐减缓横向移动速度并过渡为机位相对稳定，同时执行变焦推进，将视觉焦点逐步压缩至猎豹与羚羊之间不断缩短的距离上。 **第5个镜头**再次向前移动并轻微向下移动，贴近地面逼近两者之间的空间，在猎豹前肢逼近羚羊后方的临界位置停住，形成强烈压迫感与张力，同时配合逐渐增强的交响配乐、持续加密的鼓点、风声与踏地声推进节奏，并在最后阶段压低音乐仅保留环境声与节奏声形成短暂停顿。 |     |

在调用前，先[获取API Key](https://help.aliyun.com/zh/model-studio/get-api-key)，再[配置API Key到环境变量](https://help.aliyun.com/zh/model-studio/configure-api-key-through-environment-variables)。通过SDK进行调用，请[安装DashScope SDK](https://help.aliyun.com/zh/model-studio/install-sdk)。

## Python SDK

**重要**

请确保 DashScope Python SDK 版本**不低于** `**1.25.16**`，再运行以下代码。

若版本过低，可能会触发 “url error, please check url!” 等错误。请参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import os
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope

# 以下为北京地域URL，各地域的URL不同，获取URL：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
dashscope.base_http_api_url = 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1'
# 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
api_key = os.getenv("DASHSCOPE_API_KEY", "YOUR_API_KEY")

print('please wait...')
rsp = VideoSynthesis.call(api_key=api_key,
                          model='wan2.7-t2v-2026-06-12',
                          prompt='第1个镜头 大远景开篇，镜头从接近地面的低机位开始向前移动，镜头沿草原方向推进，同时向上移动，将视角从贴地逐渐抬升至略高位置，使猎豹从左侧进入画面并与前方逃窜的羚羊共同处于同一追逐路径中，建立清晰的前后空间关系。 第2个镜头 向下移动回到接近地面高度，并沿猎豹运动方向向右移动，与其保持侧向平行关系进行稳定跟随，主体始终处于画面中部偏左位置，背景产生连续横向位移效果，在这一阶段镜头运动保持稳定一段时间以强化速度感与空间连续性。 第3个镜头 在维持向右移动的同时，沿猎豹运动路径内侧做小幅弧线移动，使画面产生轻微绕行变化但始终保持与主体同向。 第4个镜头 逐渐减缓横向移动速度并过渡为机位相对稳定，同时执行变焦推进，将视觉焦点逐步压缩至猎豹与羚羊之间不断缩短的距离上。 第5个镜头 再次向前移动并轻微向下移动，贴近地面逼近两者之间的空间，在猎豹前肢逼近羚羊后方的临界位置停住，形成强烈压迫感与张力，同时配合逐渐增强的交响配乐、持续加密的鼓点、风声与踏地声推进节奏，并在最后阶段压低音乐仅保留环境声与节奏声形成短暂停顿。',
                          resolution="720P",
                          ratio="16:9",
                          duration=15,
                          prompt_extend=True,
                          watermark=True)
print(rsp)
if rsp.status_code == HTTPStatus.OK:
    print("video_url:", rsp.output.video_url)
else:
    print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))
```

## Java SDK

**重要**

请确保 DashScope Java SDK 版本**不低于** `**2.22.14**`，再运行以下代码。

若版本过低，可能会触发 “url error, please check url!” 等错误。请参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesis;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisParam;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisResult;
import com.alibaba.dashscope.exception.ApiException;
import com.alibaba.dashscope.exception.InputRequiredException;
import com.alibaba.dashscope.exception.NoApiKeyException;
import com.alibaba.dashscope.utils.JsonUtils;
import com.alibaba.dashscope.utils.Constants;

public class Text2Video {

    static {
        // 以下为北京地域url，各地域的URL不同，获取URL：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
        Constants.baseHttpApiUrl = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1";
    }

    // 若没有配置环境变量，请用百炼API Key将下行替换为：apiKey="sk-xxx"
    // 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    static String apiKey = System.getenv("DASHSCOPE_API_KEY");

    public static void text2video() throws ApiException, NoApiKeyException, InputRequiredException {
        VideoSynthesis vs = new VideoSynthesis();
        VideoSynthesisParam param =
                VideoSynthesisParam.builder()
                        .apiKey(apiKey)
                        .model("wan2.7-t2v-2026-06-12")
                        .prompt("第1个镜头 大远景开篇，镜头从接近地面的低机位开始向前移动，镜头沿草原方向推进，同时向上移动，将视角从贴地逐渐抬升至略高位置，使猎豹从左侧进入画面并与前方逃窜的羚羊共同处于同一追逐路径中，建立清晰的前后空间关系。 第2个镜头 向下移动回到接近地面高度，并沿猎豹运动方向向右移动，与其保持侧向平行关系进行稳定跟随，主体始终处于画面中部偏左位置，背景产生连续横向位移效果，在这一阶段镜头运动保持稳定一段时间以强化速度感与空间连续性。 第3个镜头 在维持向右移动的同时，沿猎豹运动路径内侧做小幅弧线移动，使画面产生轻微绕行变化但始终保持与主体同向。 第4个镜头 逐渐减缓横向移动速度并过渡为机位相对稳定，同时执行变焦推进，将视觉焦点逐步压缩至猎豹与羚羊之间不断缩短的距离上。 第5个镜头 再次向前移动并轻微向下移动，贴近地面逼近两者之间的空间，在猎豹前肢逼近羚羊后方的临界位置停住，形成强烈压迫感与张力，同时配合逐渐增强的交响配乐、持续加密的鼓点、风声与踏地声推进节奏，并在最后阶段压低音乐仅保留环境声与节奏声形成短暂停顿。")
                        .duration(15)
                        .resolution("720P")
                        .ratio("16:9")
                        .promptExtend(true)
                        .watermark(true)
                        .build();
        System.out.println("please wait...");
        VideoSynthesisResult result = vs.call(param);
        System.out.println(JsonUtils.toJson(result));
    }

    public static void main(String[] args) {
        try {
            text2video();
        } catch (ApiException | NoApiKeyException | InputRequiredException e) {
            System.out.println(e.getMessage());
        }
        System.exit(0);
    }
}
```

## curl

**步骤1：创建任务获取任务ID**

```
curl --location 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wan2.7-t2v-2026-06-12",
    "input": {
        "prompt": "第1个镜头 大远景开篇，镜头从接近地面的低机位开始向前移动，镜头沿草原方向推进，同时向上移动，将视角从贴地逐渐抬升至略高位置，使猎豹从左侧进入画面并与前方逃窜的羚羊共同处于同一追逐路径中，建立清晰的前后空间关系。 第2个镜头 向下移动回到接近地面高度，并沿猎豹运动方向向右移动，与其保持侧向平行关系进行稳定跟随，主体始终处于画面中部偏左位置，背景产生连续横向位移效果，在这一阶段镜头运动保持稳定一段时间以强化速度感与空间连续性。 第3个镜头 在维持向右移动的同时，沿猎豹运动路径内侧做小幅弧线移动，使画面产生轻微绕行变化但始终保持与主体同向。 第4个镜头 逐渐减缓横向移动速度并过渡为机位相对稳定，同时执行变焦推进，将视觉焦点逐步压缩至猎豹与羚羊之间不断缩短的距离上。 第5个镜头 再次向前移动并轻微向下移动，贴近地面逼近两者之间的空间，在猎豹前肢逼近羚羊后方的临界位置停住，形成强烈压迫感与张力，同时配合逐渐增强的交响配乐、持续加密的鼓点、风声与踏地声推进节奏，并在最后阶段压低音乐仅保留环境声与节奏声形成短暂停顿。"
    },
    "parameters": {
        "resolution": "720P",
        "ratio": "16:9",
        "prompt_extend": true,
        "watermark": true,
        "duration": 15
    }
}'
```

**步骤2：根据任务ID获取结果**

将`{task_id}`完整替换为上一步接口返回的`task_id`的值。`task_id`查询有效期为24小时。

```
curl -X GET https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/tasks/{task_id} \
--header "Authorization: Bearer $DASHSCOPE_API_KEY"
```

**示例代码：wan2.6及早期模型**

## Python SDK

**重要**

请确保 DashScope Python SDK 版本**不低于** `**1.25.16**`，再运行以下代码。

若版本过低，可能会触发 “url error, please check url!” 等错误。请参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import os
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope

# 以下为北京地域URL，各地域的URL不同，获取URL：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
dashscope.base_http_api_url = 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1'
# 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
api_key = os.getenv("DASHSCOPE_API_KEY", "YOUR_API_KEY")

print('please wait...')
rsp = VideoSynthesis.call(api_key=api_key,
                          model='wan2.6-t2v',
                          prompt='一段紧张刺激的侦探追查故事，展现电影级叙事能力。第1个镜头[0-3秒] 全景：雨夜的纽约街头，霓虹灯闪烁，一位身穿黑色风衣的侦探快步行走。 第2个镜头[3-6秒] 中景：侦探进入一栋老旧建筑，雨水打湿了他的外套，门在他身后缓缓关闭。 第3个镜头[6-9秒] 特写：侦探的眼神坚毅专注，远处传来警笛声，他微微皱眉思考。 第4个镜头[9-12秒] 中景：侦探在昏暗走廊中小心前行，手电筒照亮前方。 第5个镜头[12-15秒] 特写：侦探发现关键线索，脸上露出恍然大悟的表情。',
                          size="1280*720",
                          duration=15,
                          shot_type="multi",
                          prompt_extend=True,
                          watermark=True)
print(rsp)
if rsp.status_code == HTTPStatus.OK:
    print("video_url:", rsp.output.video_url)
else:
    print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))
```

## Java SDK

**重要**

请确保 DashScope Java SDK 版本**不低于** `**2.22.14**`，再运行以下代码。

若版本过低，可能会触发 “url error, please check url!” 等错误。请参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesis;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisParam;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisResult;
import com.alibaba.dashscope.exception.ApiException;
import com.alibaba.dashscope.exception.InputRequiredException;
import com.alibaba.dashscope.exception.NoApiKeyException;
import com.alibaba.dashscope.utils.JsonUtils;
import com.alibaba.dashscope.utils.Constants;

public class Text2Video {

    static {
        // 以下为北京地域url，各地域的URL不同，获取URL：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
        Constants.baseHttpApiUrl = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1";
    }

    // 若没有配置环境变量，请用百炼API Key将下行替换为：apiKey="sk-xxx"
    // 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    static String apiKey = System.getenv("DASHSCOPE_API_KEY");

    public static void text2video() throws ApiException, NoApiKeyException, InputRequiredException {
        VideoSynthesis vs = new VideoSynthesis();
        VideoSynthesisParam param =
                VideoSynthesisParam.builder()
                        .apiKey(apiKey)
                        .model("wan2.6-t2v")
                        .prompt("一段紧张刺激的侦探追查故事，展现电影级叙事能力。第1个镜头[0-3秒] 全景：雨夜的纽约街头，霓虹灯闪烁，一位身穿黑色风衣的侦探快步行走。 第2个镜头[3-6秒] 中景：侦探进入一栋老旧建筑，雨水打湿了他的外套，门在他身后缓缓关闭。 第3个镜头[6-9秒] 特写：侦探的眼神坚毅专注，远处传来警笛声，他微微皱眉思考。 第4个镜头[9-12秒] 中景：侦探在昏暗走廊中小心前行，手电筒照亮前方。 第5个镜头[12-15秒] 特写：侦探发现关键线索，脸上露出恍然大悟的表情。")
                        .duration(15)
                        .size("1280*720")
                        .shotType("multi")
                        .promptExtend(true)
                        .watermark(true)
                        .build();
        System.out.println("please wait...");
        VideoSynthesisResult result = vs.call(param);
        System.out.println(JsonUtils.toJson(result));
    }

    public static void main(String[] args) {
        try {
            text2video();
        } catch (ApiException | NoApiKeyException | InputRequiredException e) {
            System.out.println(e.getMessage());
        }
        System.exit(0);
    }
}
```

## curl

**步骤1：创建任务获取任务ID**

```
curl --location 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wan2.6-t2v",
    "input": {
        "prompt": "一段紧张刺激的侦探追查故事，展现电影级叙事能力。第1个镜头[0-3秒] 全景：雨夜的纽约街头，霓虹灯闪烁，一位身穿黑色风衣的侦探快步行走。 第2个镜头[3-6秒] 中景：侦探进入一栋老旧建筑，雨水打湿了他的外套，门在他身后缓缓关闭。 第3个镜头[6-9秒] 特写：侦探的眼神坚毅专注，远处传来警笛声，他微微皱眉思考。 第4个镜头[9-12秒] 中景：侦探在昏暗走廊中小心前行，手电筒照亮前方。 第5个镜头[12-15秒] 特写：侦探发现关键线索，脸上露出恍然大悟的表情。"
    },
    "parameters": {
        "size": "1280*720",
        "prompt_extend": true,
        "watermark": true,
        "duration": 15,
        "shot_type":"multi"
    }
}'
```

**步骤2：根据任务ID获取结果**

将`{task_id}`完整替换为上一步接口返回的`task_id`的值。`task_id`查询有效期为24小时。

```
curl -X GET https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/tasks/{task_id} \
--header "Authorization: Bearer $DASHSCOPE_API_KEY"
```

**输出示例**

> `video_url` 有效期24小时，请及时下载视频。

```
{
    "request_id": "c1209113-8437-424f-a386-xxxxxx",
    "output": {
        "task_id": "966cebcd-dedc-4962-af88-xxxxxx",
        "task_status": "SUCCEEDED",
        "video_url": "https://dashscope-result-sh.oss-accelerate.aliyuncs.com/xxx.mp4?Expires=xxx",
         ...
    },
    ...
}
```

## **适用范围**

-   各地域支持的模型有所差异，且资源相互独立。各地域支持的模型请参见[百炼控制台](https://bailian.console.aliyun.com/cn-beijing?tab=model#/model-market)。
    
-   调用时，确保**模型、Endpoint URL 和 API Key 均属于同一地域**，跨地域调用将会失败。
    

**说明**

本文的示例代码适用于**北京地域**。

## **核心能力**

### **制作多镜头视频**

**支持模型**：`wan2.7系列、wan2.6系列模型`。

**功能介绍**：模型可自动进行分镜切换，例如从全景切换到特写，制作MV等场景。

**参数设置**：

-   **wan2.7**：无需设置 `shot_type`，可以在 `prompt` 中用自然语言描述镜头结构（如使用时间戳分镜描述）。若 `prompt` 中未包含任何镜头结构描述，模型将分析语义内容，自行决策输出单镜头或多镜头视频。
    
-   **wan2.6**：`shot_type` 必须设为 `"multi"`，且 `prompt_extend` 必须设为 `true`（开启智能改写以优化分镜描述）。
    

| **输入提示词** | **输出视频（wan2.7）** |
| --- | --- |
| 展现未来科技与自然和谐共存的美好愿景。 第1个镜头\\[0-2秒\\] 未来城市的空中花园全景，悬浮植物在微风中摇曳。 第2个镜头\\[2-4秒\\] 机器人园丁正在精心修剪植物，动作精准而优雅。 第3个镜头\\[4-7秒\\] 阳光透过透明穹顶洒下，照亮整个花园，展现科技与自然的完美融合。 第4个镜头\\[7-10秒\\] 镜头拉远，展现整个未来城市的壮观景象，空中花园只是其中的一部分。 |     |
| 这是一段以硬核对决为核心的武侠电影片段，在正午烈日照射的石板空地上，两名男子相对冲刺。一人出掌攻击，被对手旋身以手臂硬抗，相撞的冲击力震散地面微尘。随后两人在极小空间内拳掌疾速交错，一人腾空连环重踢，迫使对手双臂交叉抵挡并向后滑行数米，在石面磨出清晰白痕。最终两人分立两端，在剧烈呼吸中死死锁定对方。画面呈现出锐利光影下的写实动作质感，营造出从强力爆发到肃杀对峙的基调。 |     |
| 这是一段以“青春期暗恋试探”为核心的校园电影片段。夕阳斜照操场，两人并肩而立，男同学抱着篮球，目光躲闪地问：“下周的联欢会，你要参加吗？”女同学摆弄着鬓角碎发，试探性地回道：“如果……你也去的话，我就去。”听到回答，男同学喉结滚动，嘴角虽强行压抑却仍牵动出欣喜，只能望着远方强装镇定。画面呈现清透自然的暖色调，营造出细腻而克制的青春初恋基调。 |     |

## Python SDK

> 请确保 DashScope Python SDK 版本不低于 `1.25.16`，可参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import os
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope

# 以下为北京地域URL，各地域的URL不同，获取URL：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
dashscope.base_http_api_url = 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1'

# 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
# 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
api_key = os.getenv("DASHSCOPE_API_KEY")

def sample_async_call_t2v():
    # 异步调用，返回一个task_id
    rsp = VideoSynthesis.async_call(api_key=api_key,
                                    model='wan2.7-t2v-2026-06-12',
                                    prompt='展现未来科技与自然和谐共存的美好愿景。 第1个镜头[0-2秒] 未来城市的空中花园全景，悬浮植物在微风中摇曳。 第2个镜头[2-4秒] 机器人园丁正在精心修剪植物，动作精准而优雅。 第3个镜头[4-7秒] 阳光透过透明穹顶洒下，照亮整个花园，展现科技与自然的完美融合。 第4个镜头[7-10秒] 镜头拉远，展现整个未来城市的壮观景象，空中花园只是其中的一部分。',
                                    resolution='720P',
                                    ratio='16:9',
                                    duration=10,
                                    prompt_extend=True,
                                    watermark=True,
                                    negative_prompt="",
                                    seed=12345)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print("task_id: %s" % rsp.output.task_id)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))

    # 等待异步任务结束
    rsp = VideoSynthesis.wait(task=rsp, api_key=api_key)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print(rsp.output.video_url)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))


if __name__ == '__main__':
    sample_async_call_t2v()
```

## Java SDK

> 请确保 DashScope Java SDK 版本不低于 `2.22.14`，可参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesis;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisParam;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisResult;
import com.alibaba.dashscope.exception.ApiException;
import com.alibaba.dashscope.exception.InputRequiredException;
import com.alibaba.dashscope.exception.NoApiKeyException;
import com.alibaba.dashscope.utils.JsonUtils;
import com.alibaba.dashscope.utils.Constants;

public class Text2Video {
    static {
        // 以下为北京地域url，各地域的url不同，获取url：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
        Constants.baseHttpApiUrl = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1";
    }

    // 若没有配置环境变量，请用百炼API Key将下行替换为：apiKey="sk-xxx"
    // 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    static String apiKey = System.getenv("DASHSCOPE_API_KEY");

    public static void text2video() throws ApiException, NoApiKeyException, InputRequiredException {
        VideoSynthesis vs = new VideoSynthesis();
        VideoSynthesisParam param =
                VideoSynthesisParam.builder()
                        .apiKey(apiKey)
                        .model("wan2.7-t2v-2026-06-12")
                        .prompt("展现未来科技与自然和谐共存的美好愿景。 第1个镜头[0-2秒] 未来城市的空中花园全景，悬浮植物在微风中摇曳。 第2个镜头[2-4秒] 机器人园丁正在精心修剪植物，动作精准而优雅。 第3个镜头[4-7秒] 阳光透过透明穹顶洒下，照亮整个花园，展现科技与自然的完美融合。 第4个镜头[7-10秒] 镜头拉远，展现整个未来城市的壮观景象，空中花园只是其中的一部分。")
                        .negativePrompt("")
                        .resolution("720P")
                        .ratio("16:9")
                        .duration(10)
                        .promptExtend(true)
                        .watermark(true)
                        .seed(12345)
                        .build();
        // 异步调用
        VideoSynthesisResult task = vs.asyncCall(param);
        System.out.println(JsonUtils.toJson(task));
        System.out.println("please wait...");

        //获取结果
        VideoSynthesisResult result = vs.wait(task, apiKey);
        System.out.println(JsonUtils.toJson(result));
    }

    public static void main(String[] args) {
        try {
            text2video();
        } catch (ApiException | NoApiKeyException | InputRequiredException e) {
            System.out.println(e.getMessage());
        }
        System.exit(0);
    }
}
```

## curl

**步骤1：创建任务获取任务ID**

```
curl --location 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wan2.7-t2v-2026-06-12",
    "input": {
        "prompt": "展现未来科技与自然和谐共存的美好愿景。 第1个镜头[0-2秒] 未来城市的空中花园全景，悬浮植物在微风中摇曳。 第2个镜头[2-4秒] 机器人园丁正在精心修剪植物，动作精准而优雅。 第3个镜头[4-7秒] 阳光透过透明穹顶洒下，照亮整个花园，展现科技与自然的完美融合。 第4个镜头[7-10秒] 镜头拉远，展现整个未来城市的壮观景象，空中花园只是其中的一部分。"
    },
    "parameters": {
        "resolution": "720P",
        "ratio": "16:9",
        "watermark": true,
        "prompt_extend": true,
        "duration": 10
    }
}'
```

**步骤2：根据任务ID获取结果**

将`{task_id}`完整替换为上一步接口返回的`task_id`的值。`task_id`查询有效期为24小时。

```
curl -X GET https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/tasks/{task_id} \
--header "Authorization: Bearer $DASHSCOPE_API_KEY"
```

**示例代码：wan2.6模型**

## Python SDK

> 请确保 DashScope Python SDK 版本不低于 `1.25.16`，可参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import os
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope

# 以下为北京地域URL，各地域的URL不同，获取URL：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
dashscope.base_http_api_url = 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1'

# 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
# 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
api_key = os.getenv("DASHSCOPE_API_KEY")

def sample_async_call_t2v():
    # 异步调用，返回一个task_id
    rsp = VideoSynthesis.async_call(api_key=api_key,
                                    model='wan2.6-t2v',
                                    prompt='展现未来科技与自然和谐共存的美好愿景。 第1个镜头[0-2秒] 未来城市的空中花园全景，悬浮植物在微风中摇曳。 第2个镜头[2-4秒] 机器人园丁正在精心修剪植物，动作精准而优雅。 第3个镜头[4-7秒] 阳光透过透明穹顶洒下，照亮整个花园，展现科技与自然的完美融合。 第4个镜头[7-10秒] 镜头拉远，展现整个未来城市的壮观景象，空中花园只是其中的一部分。',
                                    size='1280*720',
                                    duration=10,
                                    shot_type='multi',
                                    prompt_extend=True,
                                    watermark=True,
                                    negative_prompt="",
                                    seed=12345)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print("task_id: %s" % rsp.output.task_id)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))

    # 等待异步任务结束
    rsp = VideoSynthesis.wait(task=rsp, api_key=api_key)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print(rsp.output.video_url)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))


if __name__ == '__main__':
    sample_async_call_t2v()
```

## Java SDK

> 请确保 DashScope Java SDK 版本不低于 `2.22.14`，可参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesis;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisParam;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisResult;
import com.alibaba.dashscope.exception.ApiException;
import com.alibaba.dashscope.exception.InputRequiredException;
import com.alibaba.dashscope.exception.NoApiKeyException;
import com.alibaba.dashscope.utils.JsonUtils;
import com.alibaba.dashscope.utils.Constants;

public class Text2Video {
    static {
        // 以下为北京地域url，各地域的url不同，获取url：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
        Constants.baseHttpApiUrl = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1";
    }

    // 若没有配置环境变量，请用百炼API Key将下行替换为：apiKey="sk-xxx"
    // 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    static String apiKey = System.getenv("DASHSCOPE_API_KEY");

    public static void text2video() throws ApiException, NoApiKeyException, InputRequiredException {
        VideoSynthesis vs = new VideoSynthesis();
        VideoSynthesisParam param =
                VideoSynthesisParam.builder()
                        .apiKey(apiKey)
                        .model("wan2.6-t2v")
                        .prompt("展现未来科技与自然和谐共存的美好愿景。 第1个镜头[0-2秒] 未来城市的空中花园全景，悬浮植物在微风中摇曳。 第2个镜头[2-4秒] 机器人园丁正在精心修剪植物，动作精准而优雅。 第3个镜头[4-7秒] 阳光透过透明穹顶洒下，照亮整个花园，展现科技与自然的完美融合。 第4个镜头[7-10秒] 镜头拉远，展现整个未来城市的壮观景象，空中花园只是其中的一部分。")
                        .negativePrompt("")
                        .size("1280*720")
                        .duration(10)
                        .shotType("multi")
                        .promptExtend(true)
                        .watermark(true)
                        .seed(12345)
                        .build();
        // 异步调用
        VideoSynthesisResult task = vs.asyncCall(param);
        System.out.println(JsonUtils.toJson(task));
        System.out.println("please wait...");

        //获取结果
        VideoSynthesisResult result = vs.wait(task, apiKey);
        System.out.println(JsonUtils.toJson(result));
    }

    public static void main(String[] args) {
        try {
            text2video();
        } catch (ApiException | NoApiKeyException | InputRequiredException e) {
            System.out.println(e.getMessage());
        }
        System.exit(0);
    }
}
```

## curl

**步骤1：创建任务获取任务ID**

```
curl --location 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wan2.6-t2v",
    "input": {
        "prompt": "展现未来科技与自然和谐共存的美好愿景。 第1个镜头[0-2秒] 未来城市的空中花园全景，悬浮植物在微风中摇曳。 第2个镜头[2-4秒] 机器人园丁正在精心修剪植物，动作精准而优雅。 第3个镜头[4-7秒] 阳光透过透明穹顶洒下，照亮整个花园，展现科技与自然的完美融合。 第4个镜头[7-10秒] 镜头拉远，展现整个未来城市的壮观景象，空中花园只是其中的一部分。"
    },
    "parameters": {
        "size": "1280*720",
        "prompt_extend": true,
        "watermark": true,
        "duration": 10,
        "shot_type": "multi"
    }
}'
```

**步骤2：根据任务ID获取结果**

将`{task_id}`完整替换为上一步接口返回的`task_id`的值。`task_id`查询有效期为24小时。

```
curl -X GET https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/tasks/{task_id} \
--header "Authorization: Bearer $DASHSCOPE_API_KEY"
```

### **实现声画同步**

**支持模型**：`wan2.7系列、wan2.6系列、wan2.5系列模型`。

**功能介绍**：让照片中的人物“开口说话”或唱歌，嘴型与音频匹配。更多示例请参见[视频声音生成](https://help.aliyun.com/zh/model-studio/text-to-video-prompt#df26af6f91bkq)。

**参数设置：**

-   **传入音频文件**：传入 `audio_url`。模型会根据音频文件对齐口型。
    
-   **自动配音**：默认输出有声视频，无需传入 `audio_url`。模型会根据画面自动生成背景音效、音乐或人声。
    

| **输入示例** | **输出视频（有声视频）** |
| --- | --- |
| **输入提示词**：一幅史诗级可爱的场景。一只小巧可爱的卡通小猫将军，身穿细节精致的金色盔甲，头戴一个稍大的头盔，勇敢地站在悬崖上。他骑着一匹虽小但英勇的战马，说：“青海长云暗雪山，孤城遥望玉门关。黄沙百战穿金甲，不破楼兰终不还”。悬崖下方，一支由老鼠组成的、数量庞大、无穷无尽的军队正带着临时制作的武器向前冲锋。这是一个戏剧性的、大规模的战斗场景，灵感来自中国古代的战争史诗。远处的雪山上空，天空乌云密布。整体氛围是“可爱”与“霸气”的搞笑和史诗般的融合。 **输入音频**： |     |

## Python SDK

> 请确保 DashScope Python SDK 版本不低于 `1.25.16`，可参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import os
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope

# 以下为北京地域URL，各地域的URL不同，获取URL：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
dashscope.base_http_api_url = 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1'

# 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
# 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
api_key = os.getenv("DASHSCOPE_API_KEY")

def sample_async_call_t2v():
    # 异步调用，返回一个task_id
    rsp = VideoSynthesis.async_call(api_key=api_key,
                                    model='wan2.7-t2v-2026-06-12',
                                    prompt='一幅史诗级可爱的场景。一只小巧可爱的卡通小猫将军，身穿细节精致的金色盔甲，头戴一个稍大的头盔，勇敢地站在悬崖上。他骑着一匹虽小但英勇的战马，说：”青海长云暗雪山，孤城遥望玉门关。黄沙百战穿金甲，不破楼兰终不还。”。悬崖下方，一支由老鼠组成的、数量庞大、无穷无尽的军队正带着临时制作的武器向前冲锋。这是一个戏剧性的、大规模的战斗场景，灵感来自中国古代的战争史诗。远处的雪山上空，天空乌云密布。整体氛围是”可爱”与”霸气”的搞笑和史诗般的融合。',
                                    audio_url='https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250923/hbiayh/%E4%BB%8E%E5%86%9B%E8%A1%8C.mp3',
                                    resolution='720P',
                                    ratio='16:9',
                                    duration=10,
                                    prompt_extend=True,
                                    watermark=True,
                                    negative_prompt=””,
                                    seed=12345)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print("task_id: %s" % rsp.output.task_id)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))

    # 等待异步任务结束
    rsp = VideoSynthesis.wait(task=rsp, api_key=api_key)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print(rsp.output.video_url)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))


if __name__ == '__main__':
    sample_async_call_t2v()
```

## Java SDK

> 请确保 DashScope Java SDK 版本不低于 `2.22.14`，可参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesis;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisParam;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisResult;
import com.alibaba.dashscope.exception.ApiException;
import com.alibaba.dashscope.exception.InputRequiredException;
import com.alibaba.dashscope.exception.NoApiKeyException;
import com.alibaba.dashscope.utils.JsonUtils;
import com.alibaba.dashscope.utils.Constants;

public class Text2Video {
    static {
        // 以下为北京地域url，各地域的url不同，获取url：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
        Constants.baseHttpApiUrl = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1";
    }

    // 若没有配置环境变量，请用百炼API Key将下行替换为：apiKey="sk-xxx"
    // 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    static String apiKey = System.getenv("DASHSCOPE_API_KEY");

    public static void text2video() throws ApiException, NoApiKeyException, InputRequiredException {
        VideoSynthesis vs = new VideoSynthesis();
        VideoSynthesisParam param =
                VideoSynthesisParam.builder()
                        .apiKey(apiKey)
                        .model(“wan2.7-t2v-2026-06-12”)
                        .prompt(“一幅史诗级可爱的场景。一只小巧可爱的卡通小猫将军，身穿细节精致的金色盔甲，头戴一个稍大的头盔，勇敢地站在悬崖上。他骑着一匹虽小但英勇的战马，说：”青海长云暗雪山，孤城遥望玉门关。黄沙百战穿金甲，不破楼兰终不还。”。悬崖下方，一支由老鼠组成的、数量庞大、无穷无尽的军队正带着临时制作的武器向前冲锋。这是一个戏剧性的、大规模的战斗场景，灵感来自中国古代的战争史诗。远处的雪山上空，天空乌云密布。整体氛围是”可爱”与”霸气”的搞笑和史诗般的融合。”)
                        .audioUrl(“https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250923/hbiayh/%E4%BB%8E%E5%86%9B%E8%A1%8C.mp3”)
                        .negativePrompt(“”)
                        .resolution(“720P”)
                        .ratio(“16:9”)
                        .duration(10)
                        .promptExtend(true)
                        .watermark(true)
                        .seed(12345)
                        .build();
        // 异步调用
        VideoSynthesisResult task = vs.asyncCall(param);
        System.out.println(JsonUtils.toJson(task));
        System.out.println("please wait...");

        //获取结果
        VideoSynthesisResult result = vs.wait(task, apiKey);
        System.out.println(JsonUtils.toJson(result));
    }

    public static void main(String[] args) {
        try {
            text2video();
        } catch (ApiException | NoApiKeyException | InputRequiredException e) {
            System.out.println(e.getMessage());
        }
        System.exit(0);
    }
}
```

## curl

**步骤1：创建任务获取任务ID**

```
curl --location 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wan2.7-t2v-2026-06-12",
    "input": {
        "prompt": "一幅史诗级可爱的场景。一只小巧可爱的卡通小猫将军，身穿细节精致的金色盔甲，头戴一个稍大的头盔，勇敢地站在悬崖上。他骑着一匹虽小但英勇的战马，说：”青海长云暗雪山，孤城遥望玉门关。黄沙百战穿金甲，不破楼兰终不还。”。悬崖下方，一支由老鼠组成的、数量庞大、无穷无尽的军队正带着临时制作的武器向前冲锋。这是一个戏剧性的、大规模的战斗场景，灵感来自中国古代的战争史诗。远处的雪山上空，天空乌云密布。整体氛围是”可爱”与”霸气”的搞笑和史诗般的融合。",
        "audio_url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250923/hbiayh/%E4%BB%8E%E5%86%9B%E8%A1%8C.mp3"
    },
    "parameters": {
        "resolution": "720P",
        "ratio": "16:9",
        "watermark": true,
        "prompt_extend": true,
        "duration": 10
    }
}'
```

**步骤2：根据任务ID获取结果**

将`{task_id}`完整替换为上一步接口返回的`task_id`的值。`task_id`查询有效期为24小时。

```
curl -X GET https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/tasks/{task_id} \
--header "Authorization: Bearer $DASHSCOPE_API_KEY"
```

**示例代码：wan2.6模型**

## Python SDK

> 请确保 DashScope Python SDK 版本不低于 `1.25.16`，可参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import os
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope

# 以下为北京地域URL，各地域的URL不同，获取URL：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
dashscope.base_http_api_url = 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1'

# 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
# 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
api_key = os.getenv("DASHSCOPE_API_KEY")

def sample_async_call_t2v():
    # 异步调用，返回一个task_id
    rsp = VideoSynthesis.async_call(api_key=api_key,
                                    model='wan2.6-t2v',
                                    prompt='一幅史诗级可爱的场景。一只小巧可爱的卡通小猫将军，身穿细节精致的金色盔甲，头戴一个稍大的头盔，勇敢地站在悬崖上。他骑着一匹虽小但英勇的战马，说："青海长云暗雪山，孤城遥望玉门关。黄沙百战穿金甲，不破楼兰终不还。"。悬崖下方，一支由老鼠组成的、数量庞大、无穷无尽的军队正带着临时制作的武器向前冲锋。这是一个戏剧性的、大规模的战斗场景，灵感来自中国古代的战争史诗。远处的雪山上空，天空乌云密布。整体氛围是"可爱"与"霸气"的搞笑和史诗般的融合。',
                                    audio_url='https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250923/hbiayh/%E4%BB%8E%E5%86%9B%E8%A1%8C.mp3',
                                    size='1280*720',
                                    duration=10,
                                    prompt_extend=True,
                                    watermark=True,
                                    negative_prompt="",
                                    seed=12345)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print("task_id: %s" % rsp.output.task_id)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))

    # 等待异步任务结束
    rsp = VideoSynthesis.wait(task=rsp, api_key=api_key)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print(rsp.output.video_url)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))


if __name__ == '__main__':
    sample_async_call_t2v()
```

## Java SDK

> 请确保 DashScope Java SDK 版本不低于 `2.22.14`，可参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesis;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisParam;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisResult;
import com.alibaba.dashscope.exception.ApiException;
import com.alibaba.dashscope.exception.InputRequiredException;
import com.alibaba.dashscope.exception.NoApiKeyException;
import com.alibaba.dashscope.utils.JsonUtils;
import com.alibaba.dashscope.utils.Constants;

public class Text2Video {
    static {
        // 以下为北京地域url，各地域的url不同，获取url：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
        Constants.baseHttpApiUrl = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1";
    }

    // 若没有配置环境变量，请用百炼API Key将下行替换为：apiKey="sk-xxx"
    // 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    static String apiKey = System.getenv("DASHSCOPE_API_KEY");

    public static void text2video() throws ApiException, NoApiKeyException, InputRequiredException {
        VideoSynthesis vs = new VideoSynthesis();
        VideoSynthesisParam param =
                VideoSynthesisParam.builder()
                        .apiKey(apiKey)
                        .model("wan2.6-t2v")
                        .prompt("一幅史诗级可爱的场景。一只小巧可爱的卡通小猫将军，身穿细节精致的金色盔甲，头戴一个稍大的头盔，勇敢地站在悬崖上。他骑着一匹虽小但英勇的战马，说："青海长云暗雪山，孤城遥望玉门关。黄沙百战穿金甲，不破楼兰终不还。"。悬崖下方，一支由老鼠组成的、数量庞大、无穷无尽的军队正带着临时制作的武器向前冲锋。这是一个戏剧性的、大规模的战斗场景，灵感来自中国古代的战争史诗。远处的雪山上空，天空乌云密布。整体氛围是"可爱"与"霸气"的搞笑和史诗般的融合。")
                        .audioUrl("https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250923/hbiayh/%E4%BB%8E%E5%86%9B%E8%A1%8C.mp3")
                        .negativePrompt("")
                        .size("1280*720")
                        .duration(10)
                        .promptExtend(true)
                        .watermark(true)
                        .seed(12345)
                        .build();
        // 异步调用
        VideoSynthesisResult task = vs.asyncCall(param);
        System.out.println(JsonUtils.toJson(task));
        System.out.println("please wait...");

        //获取结果
        VideoSynthesisResult result = vs.wait(task, apiKey);
        System.out.println(JsonUtils.toJson(result));
    }

    public static void main(String[] args) {
        try {
            text2video();
        } catch (ApiException | NoApiKeyException | InputRequiredException e) {
            System.out.println(e.getMessage());
        }
        System.exit(0);
    }
}
```

## curl

**步骤1：创建任务获取任务ID**

```
curl --location 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wan2.6-t2v",
    "input": {
        "prompt": "一幅史诗级可爱的场景。一只小巧可爱的卡通小猫将军，身穿细节精致的金色盔甲，头戴一个稍大的头盔，勇敢地站在悬崖上。他骑着一匹虽小但英勇的战马，说："青海长云暗雪山，孤城遥望玉门关。黄沙百战穿金甲，不破楼兰终不还。"。悬崖下方，一支由老鼠组成的、数量庞大、无穷无尽的军队正带着临时制作的武器向前冲锋。这是一个戏剧性的、大规模的战斗场景，灵感来自中国古代的战争史诗。远处的雪山上空，天空乌云密布。整体氛围是"可爱"与"霸气"的搞笑和史诗般的融合。",
        "audio_url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250923/hbiayh/%E4%BB%8E%E5%86%9B%E8%A1%8C.mp3"
    },
    "parameters": {
        "size": "1280*720",
        "watermark": true,
        "prompt_extend": true,
        "duration": 10
    }
}'
```

**步骤2：根据任务ID获取结果**

将`{task_id}`完整替换为上一步接口返回的`task_id`的值。`task_id`查询有效期为24小时。

```
curl -X GET https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/tasks/{task_id} \
--header "Authorization: Bearer $DASHSCOPE_API_KEY"
```

### **生成无声视频**

**支持模型**：`wan2.2系列模型`、`wanx2.1系列模型`。

**功能介绍**：适用于无需音频的纯视觉展示场景，如动态海报、无声短视频等。

**参数设置**：wan2.2及以下版本模型，默认生成无声视频，无需额外配置。

| **输入提示词** | **输出视频（无声视频）** |
| --- | --- |
| 边缘光，低对比度，中近景，日光，左侧重构图，干净的单人镜头，暖色调，柔光，晴天光，侧光，白天，一个年轻的女孩坐在高草丛生的田野中，两条毛发蓬松的小毛驴站在她身后。女孩大约十一二岁，穿着简单的碎花裙子，头发扎成两条麻花辫，脸上带着纯真的笑容。她双腿交叉坐下，双手轻轻抚弄身旁的野花。小毛驴体型健壮，耳朵竖起，好奇地望着镜头方向。阳光洒在田野上，营造出温暖自然的画面感。 |     |

## Python SDK

> 请确保 DashScope Python SDK 版本不低于 `1.25.16`，可参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import os
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope

# 以下为北京地域URL，各地域的URL不同，获取URL：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
dashscope.base_http_api_url = 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1'

# 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
# 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
api_key = os.getenv("DASHSCOPE_API_KEY")

def sample_async_call_t2v():
    # 异步调用，返回一个task_id
    rsp = VideoSynthesis.async_call(api_key=api_key,
                                    model='wan2.2-t2v-plus',
                                    prompt='边缘光，低对比度，中近景，日光，左侧重构图，干净的单人镜头，暖色调，柔光，晴天光，侧光，白天，一个年轻的女孩坐在高草丛生的田野中，两条毛发蓬松的小毛驴站在她身后。女孩大约十一二岁，穿着简单的碎花裙子，头发扎成两条麻花辫，脸上带着纯真的笑容。她双腿交叉坐下，双手轻轻抚弄身旁的野花。小毛驴体型健壮，耳朵竖起，好奇地望着镜头方向。阳光洒在田野上，营造出温暖自然的画面感。',
                                    prompt_extend=True,
                                    size='832*480',
                                    negative_prompt="",
                                    watermark=True,
                                    seed=12345)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print("task_id: %s" % rsp.output.task_id)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))

    # 等待异步任务结束
    rsp = VideoSynthesis.wait(task=rsp, api_key=api_key)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print(rsp.output.video_url)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' % (rsp.status_code, rsp.code, rsp.message))


if __name__ == '__main__':
    sample_async_call_t2v()
```

## Java SDK

> 请确保 DashScope Java SDK 版本不低于 `2.22.14`，可参考[安装SDK](https://help.aliyun.com/zh/model-studio/install-sdk)进行更新。

```
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesis;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisParam;
import com.alibaba.dashscope.aigc.videosynthesis.VideoSynthesisResult;
import com.alibaba.dashscope.exception.ApiException;
import com.alibaba.dashscope.exception.InputRequiredException;
import com.alibaba.dashscope.exception.NoApiKeyException;
import com.alibaba.dashscope.utils.JsonUtils;
import com.alibaba.dashscope.utils.Constants;

public class Text2Video {
    static {
        // 以下为北京地域url，各地域的url不同，获取url：https://help.aliyun.com/zh/model-studio/text-to-video-api-reference
        Constants.baseHttpApiUrl = "https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1";
    }

    // 若没有配置环境变量，请用百炼API Key将下行替换为：apiKey="sk-xxx"
    // 各地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    static String apiKey = System.getenv("DASHSCOPE_API_KEY");

    public static void text2video() throws ApiException, NoApiKeyException, InputRequiredException {
        VideoSynthesis vs = new VideoSynthesis();
        VideoSynthesisParam param =
                VideoSynthesisParam.builder()
                        .apiKey(apiKey)
                        .model("wan2.2-t2v-plus")
                        .prompt("边缘光，低对比度，中近景，日光，左侧重构图，干净的单人镜头，暖色调，柔光，晴天光，侧光，白天，一个年轻的女孩坐在高草丛生的田野中，两条毛发蓬松的小毛驴站在她身后。女孩大约十一二岁，穿着简单的碎花裙子，头发扎成两条麻花辫，脸上带着纯真的笑容。她双腿交叉坐下，双手轻轻抚弄身旁的野花。小毛驴体型健壮，耳朵竖起，好奇地望着镜头方向。阳光洒在田野上，营造出温暖自然的画面感。")
                        .size("832*480")
                        .promptExtend(true)
                        .watermark(true)
                        .seed(12345)
                        .build();
        // 异步调用
        VideoSynthesisResult task = vs.asyncCall(param);
        System.out.println(JsonUtils.toJson(task));
        System.out.println("please wait...");

        //获取结果
        VideoSynthesisResult result = vs.wait(task, apiKey);
        System.out.println(JsonUtils.toJson(result));
    }

    public static void main(String[] args) {
        try {
            text2video();
        } catch (ApiException | NoApiKeyException | InputRequiredException e) {
            System.out.println(e.getMessage());
        }
        System.exit(0);
    }
}
```

## curl

**步骤1：创建任务获取任务ID**

```
curl --location 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
    -H 'X-DashScope-Async: enable' \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "wan2.2-t2v-plus",
    "input": {
        "prompt": "边缘光，低对比度，中近景，日光，左侧重构图，干净的单人镜头，暖色调，柔光，晴天光，侧光，白天，一个年轻的女孩坐在高草丛生的田野中，两条毛发蓬松的小毛驴站在她身后。女孩大约十一二岁，穿着简单的碎花裙子，头发扎成两条麻花辫，脸上带着纯真的笑容。她双腿交叉坐下，双手轻轻抚弄身旁的野花。小毛驴体型健壮，耳朵竖起，好奇地望着镜头方向。阳光洒在田野上，营造出温暖自然的画面感。"
    },
    "parameters": {
        "size": "832*480",
        "prompt_extend": true,
        "watermark": true
    }
}'
```

**步骤2：根据任务ID获取结果**

将`{task_id}`完整替换为上一步接口返回的`task_id`的值。`task_id`查询有效期为24小时。

```
curl -X GET https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/tasks/{task_id} \
--header "Authorization: Bearer $DASHSCOPE_API_KEY"
```

## 如何传入音频

-   **音频数量**：1个。
    
-   **输入方式**：
    
    -   **公网 URL**：支持 HTTP 或 HTTPS 协议。
        
    -   **临时URL**：支持OSS协议，必须通过[上传文件获取临时 URL](https://help.aliyun.com/zh/model-studio/get-temporary-file-url)。
        

## **输出视频**

-   **视频个数量**：1个。
    
-   **视频规格**：格式为MP4。具体请参见[视频规格](#06f39eafa2dwt)。
    
-   **视频URL有效期**：**24小时**。
    
-   **视频尺寸**：
    
    -   wan2.7通过 `resolution`（分辨率档位）和 `ratio`（宽高比）指定；
        
    -   wan2.6及早期模型通过 `size` 指定。
        

## **计费与限流**

-   模型免费额度和计费单价请参见[模型价格](https://help.aliyun.com/zh/model-studio/model-pricing#ba6f7744d5e0o)。
    
-   模型限流请参见[万相系列](https://help.aliyun.com/zh/model-studio/rate-limit#a729d7b6bar7y)。
    
-   计费说明：
    
    -   输入不计费，输出计费。按成功生成的 **视频秒数** 计费。
        
    -   模型调用失败或处理错误不产生任何费用，也不消耗[免费额度](https://help.aliyun.com/zh/model-studio/new-free-quota)。
        
    -   文生视频还支持[节省计划](https://help.aliyun.com/zh/model-studio/billing-for-model-studio#b0a1f8c35b9wo)。
        

## **API文档**

[文生视频API参考](https://help.aliyun.com/zh/model-studio/text-to-video-api-reference)

## **常见问题**

#### **Q: 从 wan2.6 升级到 wan2.7，代码需要改哪些地方？**

-   **分辨率控制**：wan2.7 不再使用 `size` 字段，改为通过 `resolution`（分辨率档位，如 720P、1080P）和 `ratio`（宽高比，如 16:9、9:16）组合指定。
    
-   **多镜头**：wan2.7 不再支持 `shot_type` 字段，可直接在 prompt 中用自然语言描述镜头结构。具体为：
    
    -   多镜头：输入“生成多镜头视频” 或使用时间戳描述分镜（如 “第1个镜头\[0-3秒\] 全景：雨夜的纽约街头”）
        
    -   单镜头：输入“生成单镜头视频”。
        
    -   若 `prompt` 中未包含上述指令，模型将自行理解语义 ，动态决定生成单镜头或多镜头视频。
        

/\*表格图片设置为块元素（独占一行），居中展示，鼠标放在图片上可以点击查看原图\*/ .unionContainer .markdown-body .image.break{ margin: 0px; display: inline-block; vertical-align: middle }

/\* 让引用上下间距调小，避免内容显示过于稀疏 \*/ .unionContainer .markdown-body blockquote { margin: 4px 0; } .aliyun-docs-content table.qwen blockquote { border-left: none; /\* 添加这一行来移除表格里的引用文字的左侧边框 \*/ padding: 0px; /\* 左侧内边距 \*/ margin: 0px; font-size: 14px } .aliyun-docs-content table.flagship tr:first-child td { background: linear-gradient(to right, #60a5fa, #2563eb) !important; color: white !important; }

/\* 1. 全局设置：让引用上下间距调小 \*/ .unionContainer .markdown-body blockquote { margin: 4px 0; } /\* 2. wan-video 表格内引用样式优化 \*/ .aliyun-docs-content table.wan-video blockquote { border-left: none; padding: 0px; margin: 0px; font-size: 14px; } /\* 3. wan-video 表格核心样式修改 \*/ /\* 第一步：去除表格外层所有的边框 \*/ .aliyun-docs-content table.wan-video { border: none !important; border-collapse: collapse !important; /\* 确保边框合并，防止双重边框 \*/ } /\* 第二步：针对表头容器、表体容器、每一行，强制去除上、左、右边框 \*/ /\* 这能解决“顶部横线仍然存在”的问题，因为有时边框是加在 tr 上的 \*/ .aliyun-docs-content table.wan-video thead, .aliyun-docs-content table.wan-video tbody, .aliyun-docs-content table.wan-video tr { border-top: none !important; border-left: none !important; border-right: none !important; } /\* 第三步：针对单元格（表头 th 和 内容 td） \*/ .aliyun-docs-content table.wan-video th, .aliyun-docs-content table.wan-video td { /\* 去除上边框：这会去掉表格最顶部的线，以及每一行单元格顶部的重叠线 \*/ border-top: none !important; /\* 去除左右边框：去掉竖线 \*/ border-left: none !important; border-right: none !important; /\* 确保保留下边框：这是唯一的横线来源 \*/ /\* 这里使用默认继承的颜色，如果线条消失，可手动指定颜色，如: 1px solid #e3e4e6 \*/ } /\* 4. 其他样式（如旗舰版表格）保持不变 \*/ .aliyun-docs-content table.flagship tr:first-child td { background: linear-gradient(to right, #60a5fa, #2563eb) !important; color: white !important; }