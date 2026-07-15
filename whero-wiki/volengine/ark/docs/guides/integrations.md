方舟 API 兼容 OpenAI 和 Anthropic 接口协议，支持在三方工具中使用，可参考本文进行配置及使用。

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">对于个人开发场景，推荐订阅 <a href="https://www.volcengine.com/docs/82379/2366394">Agent Plan 套餐</a>，接入教程参见 <a href="https://www.volcengine.com/docs/82379/2373738">快速开始</a>。</div>



<card mode="container" align="left" >

<span id="793c3004"></span>
# **关于方舟 Agent Plan**

<span id="634735c0"></span>
## **方舟 Agent Plan 优势**

方舟 Agent Plan 是面向个人用户推出的订阅式大模型服务套餐包，新增支持全模态模型及专属 Harness，采用精细化积分计费模式，助力开启 Agent 场景的全新体验。

<span id="7988a33e"></span>
## **方舟 Agent Plan VS 方舟 API 调用**


* 计费方式



<span aceTableMode="list" aceTableWidth="1,4,3"></span>
|接入方式 |方舟 Agent Plan |方舟 API 调用 |
|---|---|---|
|计费方式 |订阅 Agent Plan 套餐，详见[套餐概览](https://www.volcengine.com/docs/82379/2366394)。<br><br><div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div><br><br><br><div data-tips="true" data-tips-type="tip">套餐优惠定价，token 单价更低，性价比高。</div><br> |按 Token 用量后付费 |



* 核心配置

   两种方式在支持模型、API Key、Base URL 上存在差异，配置时需注意区分。



<span aceTableMode="list" aceTableWidth="1,1,3,3"></span>
|接入方式 ||方舟 Agent Plan |方舟 API 调用 |
|---|---|---|---|
|支持模型 ||[支持模型及 Harness](https://www.volcengine.com/docs/82379/2366394#3d801f5f) |支持所有语言模型，可按需选择。 |
|API Key ||[专属 API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement?LLM=%7B%7D&advancedActiveKey=agentPlan) |[API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey) |
|Base URL |兼容 Anthropic 接口协议 |\`https://ark.cn-beijing.volces.com/api/plan\` |\`https://ark.cn-beijing.volces.com/api/compatible\` |
||兼容 OpenAI 接口协议 |\`https://ark.cn-beijing.volces.com/api/plan/v3\` |\`https://ark.cn-beijing.volces.com/api/v3\` |


</card>



<span id="46b8dd4f"></span>
# 生态兼容

为了满足开发者对 OpenAI API 和 Anthropic API 生态的使用需求，方舟 API 新增了对两类接口格式的适配支持，全面兼容主流大模型接口规范及相关工具生态。开发者无需修改核心代码，仅需切换 Base URL 与 API Key，即可实现跨平台模型调用与工具集成。

在配置三方工具时，需要配置的 Base URL 信息见下表。


<span aceTableMode="list" aceTableWidth="1,2,2"></span>
|接口协议 |Base URL |适用工具 |
|---|---|---|
|兼容 Anthropic 接口协议 |`https://ark.cn-beijing.volces.com/api/compatible` |Claude Code |
|兼容 OpenAI 接口协议 |`https://ark.cn-beijing.volces.com/api/v3` |Chatbox、Cherry Studio、OpenClaw（原 Clawdbot）、TRAE、Cline、Cursor、Kilo Code、Roo Code、OpenCode、Codex CLI 等。 |


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">在配置工具前，需要<a href="https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement?LLM=%7B%7D&OpenTokenDrawer=false">开通所需的模型服务</a>。</div>


<span id="54bbb3c5"></span>
# 接入 Chatbox

<span id="f8d4a451"></span>
## 安装步骤

通过 [Chatbox 官网](https://chatboxai.app/zh)下载并安装合适的版本，或直接 **启动网页版** 。

<span id="47f5a8a0"></span>
## 配置工具

打开 Chatbox 进入 Settings 页面。


1. 在 Model Provider 中单击添加提供商，其中 **API Mode** 选择 `OpenAI API Compatible`。

2. 提供商添加成功后，配置以下信息。

   * **API Key** ：[获取API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

   * **API Host** ：`https://ark.cn-beijing.volces.com/api/v3`

   * **API Path** ：`/chat/completions`

   * **Model** ：[选择模型并获取 Model ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)


配置完成后，就可以在输入框中输入需求，与模型进行交互。

<span id="fa588d0f"></span>
# 接入 Cherry Studio

<span id="e5089140"></span>
## 安装步骤

通过 [Cherry Studio 官网](https://www.cherry-ai.com/)下载并安装 Cherry Studio 客户端。

<span id="e816fe94"></span>
## 配置工具

打开 Cherry Studio 客户端，进入设置页面。


1. 在模型服务中点击添加提供商，其中 **提供商类型** 选择 `OpenAI`。

2. 提供商添加成功后，配置以下信息。

   * **API 密钥** ：[获取API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

   * **API 地址** ：`https://ark.cn-beijing.volces.com/api/v3`

   * **模型** ：点击添加模型，填写要使用的[模型 ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)


配置完成后，就可以在输入框中输入需求，与模型进行交互。

<span id="bdb533d9"></span>
# 接入 Codex CLI

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">对于个人开发场景，推荐订阅 <a href="https://www.volcengine.com/docs/82379/2366394">Agent Plan 套餐</a>，接入教程参见 <a href="https://www.volcengine.com/docs/82379/2373738">快速开始</a>。</div>


<span id="98ffdaf6"></span>
## 安装步骤

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">Coding Plan 支持 Responses API，可以使用最新版 Codex CLI。</div>


前提条件：安装 [Node.js 18 或更新版本](https://nodejs.org/en/download/)。

在命令行界面，执行以下命令安装 Codex CLI。

```Bash
npm i -g @openai/codex
```


安装结束后，执行以下命令检查版本。

```Bash
codex --version
```


<span id=".6YWN572u5bel5YW3"></span>
## 配置工具


1. 创建并打开 Codex 的配置文件。文件路径因系统而异，具体操作如下：



<Tabs>
<Tab zoneid="qfpQiATO5K" title="macOS/Linux">
<TabTitle>macOS/Linux</TabTitle>

macOS/Linux 系统 Codex 配置文件路径：`~/.codex/config.toml`。


1. 如果在主目录下没有`.codex`目录，执行以下命令创建目录。

   ```Bash
   mkdir -p ~/.codex
   ```
   

2. 创建并打开配置文件。

   ```Bash
   nano ~/.codex/config.toml
   ```
   


</Tab>
<Tab zoneid="UmGdPZCeTm" title="Windows">
<TabTitle>Windows</TabTitle>

Windows 系统 Codex 配置文件路径：`%USERPROFILE%\.codex\config.toml`。以 CMD 命令行方式为例，操作如下。


1. 如果当前用户目录下没有`.codex`目录，执行以下命令创建目录。

   ```Bash
   if not exist "%USERPROFILE%\.codex" mkdir "%USERPROFILE%\.codex"
   ```
   

2. 创建并打开配置文件。

   ```Bash
   notepad "%USERPROFILE%\.codex\config.toml"
   ```
   


</Tab>
</Tabs>



2. 编辑 `config.toml`，需关注的配置信息如下：

   * `<Model ID>`：按需选择模型并获取 [Model ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)。

   * `env_key`：设置的是环境变量名称，请不要直接修改 `ARK_API_KEY`，您需要在下一步设置该环境变量的值。

   ```Plain
   model = "<Model ID>"
   model_provider = "volcengine"
   
   [model_providers.volcengine]
   name = "volcengine"
   base_url = "https://ark.cn-beijing.volces.com/api/v3"
   env_key = "ARK_API_KEY"
   wire_api = "responses"
   ```
   

   <div data-tips="true" data-tips-type="warning" data-tips-is-title="true" data-wrapper-indent="1">注意   </div>
   

   * <div data-tips="true" data-tips-type="warning" data-wrapper-indent="1"><code>model_supports_reasoning_summaries = true</code>：开启推理能力。   </div>
   

   * <div data-tips="true" data-tips-type="warning" data-wrapper-indent="1"><code>model_reasoning_effort</code>：控制思考长度，可以设置为 <code>low</code>、<code>medium</code>、<code>high</code>。   </div>
   

   * <div data-tips="true" data-tips-type="warning" data-wrapper-indent="1">minimax\-m2.7、kimi\-k2.6、kimi\-k2.7\-code 不支持设置 <code>model_supports_reasoning_summaries = true</code>。   </div>
   

3. 配置环境变量，需要将 `ARK_API_KEY` 环境变量设置为 [API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)。

   
   <Tabs>
   <Tab zoneid="ueqMSTD6Ue" title="macOS / Linux">
   <TabTitle>macOS / Linux</TabTitle>
   
      1. 查看 Shell 类型。
   
         ```Bash
         echo $SHELL
         ```
         
   
      2. 将环境变量写入 Shell 配置文件，使其在新开终端时自动生效。
   
         * Zsh
   
            ```Bash
            # 需要将 YOUR_API_KEY 替换为 API Key。
            echo 'export ARK_API_KEY="YOUR_API_KEY"' >> ~/.zshrc
            source ~/.zshrc
            ```
            
   
         * Bash
   
            ```Bash
            # 需要将 YOUR_API_KEY 替换为 API Key。
            echo 'export ARK_API_KEY="YOUR_API_KEY"' >> ~/.bashrc
            source ~/.bashrc
            ```
            
   
   
   </Tab>
   <Tab zoneid="FlroubmW9C" title="Windows">
   <TabTitle>Windows</TabTitle>
   
      * CMD：环境变量设置完成后，新开 CMD 窗口生效。
   
         ```Bash
         # 需要将 YOUR_API_KEY 替换为 API Key。
         setx ARK_API_KEY "YOUR_API_KEY"
         # 新开窗口，检查环境变量是否生效
         echo %ARK_API_KEY%
         ```
         
   
      * PowerShell：环境变量设置完成后，新开 PowerShell 窗口生效。
   
         ```Bash
         # 需要将 YOUR_API_KEY 替换为 API Key。
         [Environment]::SetEnvironmentVariable("ARK_API_KEY", "YOUR_API_KEY", [EnvironmentVariableTarget]::User)
         # 新开窗口，检查环境变量是否生效
         echo $env:ARK_API_KEY
         ```
         
   
   
   </Tab>
   </Tabs>
   


<span id=".5byA5aeL5L2_55So"></span>
## 开始使用

执行以下命令启动 Codex CLI。

```Bash
codex
```


<span id="adcc555a"></span>
# 接入 Claude Code

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">对于个人开发场景，推荐订阅 <a href="https://www.volcengine.com/docs/82379/2366394">Agent Plan 套餐</a>，接入教程参见 <a href="https://www.volcengine.com/docs/82379/2373738">快速开始</a>。</div>


<span id="f2c6f75f"></span>
## 安装步骤

前提条件：


* 安装 [Node.js 18 或更新版本环境](https://nodejs.org/en/download/)。

* Windows 用户需安装 [Git for Windows](https://git-scm.com/download/win)。


在命令行界面，执行以下命令安装 Claude Code。

```Bash
npm install -g @anthropic-ai/claude-code
```


安装结束后，执行以下命令查看安装结果，若显示版本号则安装成功。

```Bash
claude --version
```


<span id="90f14e9f"></span>
## 配置工具

完成Claude Code安装后，配置以下信息。


* **ANTHROPIC_BASE_URL** ：`https://ark.cn-beijing.volces.com/api/compatible`

* **ANTHROPIC_AUTH_TOKEN** ：[获取API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

* **ANTHROPIC_MODEL** ：[选择模型并获取 Model ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)

   配置步骤如下：

1. 编辑或新增 `settings.json` 文件，需要替换配置信息中的以下信息：

   * `<ARK_API_KEY>`：替换为 [API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)。

   * `<Model_Name>`：替换为要使用的[模型 ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)。


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">不同系统配置文件路径不同，具体如下：</div>



* <div data-tips="true" data-tips-type="tip">macOS & Linux：<code>~/.claude/settings.json</code></div>


* <div data-tips="true" data-tips-type="tip">Windows：<code>C:\Users\<用户名>\.claude\settings.json</code></div>



下面以 `doubao-seed-2-1-pro-260628` 为例，配置如下：

```JSON
{
    "env": {
        "ANTHROPIC_AUTH_TOKEN": "<ARK_API_KEY>",
        "ANTHROPIC_BASE_URL": "https://ark.cn-beijing.volces.com/api/compatible",
        "ANTHROPIC_MODEL": "doubao-seed-2-1-pro-260628",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "doubao-seed-2-0-lite-260428",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "doubao-seed-2-1-pro-260628",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "doubao-seed-2-1-pro-260628",
        "CLAUDE_CODE_SUBAGENT_MODEL": "doubao-seed-2-1-pro-260628"
    }
}
```


<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>



* <div data-tips="true" data-tips-type="warning">推荐使用完整模型配置，并按任务复杂度选择模型：Haiku（轻量）、Sonnet（日常）、Opus（复杂）。</div>


* <div data-tips="true" data-tips-type="warning"><code>CLAUDE_CODE_SUBAGENT_MODEL</code> 建议与主模型保持一致。</div>


* <div data-tips="true" data-tips-type="warning"><code>ANTHROPIC_DEFAULT_HAIKU_MODEL</code> 建议设置为小尺寸模型，例如 <code>doubao-seed-2-0-lite-250428</code>，通常不会影响整体使用效果。</div>


2. 编辑或新增 `.claude.json` 文件，修改或新增 `hasCompletedOnboarding` 字段值为 true。


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">不同系统配置文件路径不同，具体如下：</div>



* <div data-tips="true" data-tips-type="tip">macOS & Linux：<code>~/.claude.json</code></div>


* <div data-tips="true" data-tips-type="tip">Windows：<code>C:\Users\<用户名>\.claude.json</code></div>



```JSON
{
  "hasCompletedOnboarding": true
}
```


保存配置文件后，在新的终端窗口执行后续命令。

<span id="e6679ac5"></span>
## 使用 CC Switch

CC Switch 是一款跨平台桌面应用，专为使用 AI 编程工具的开发者设计。它帮助你统一管理 Claude Code、Claude Desktop、Codex、Gemini CLI、OpenCode、OpenClaw 和 Hermes 等受管应用的配置。

<span id="3b9f1e4a"></span>
### 支持的平台


* Windows 10 及以上

* macOS 12 (Monterey) 及以上

* Linux Ubuntu 22.04+ / Debian 11+ / Fedora 34+（x64 / ARM64）


<span id="7d5c9b2a"></span>
### 安装

> 更多安装方式和详细说明请参考 [CC Switch 官方文档](https://github.com/farion1231/cc-switch)。



<Tabs>
<Tab zoneid="KKEHHwWJX9" title="macOS">
<TabTitle>macOS</TabTitle>

* **Homebrew（推荐）** ：

   ```Bash
   brew tap farion1231/ccswitch
   brew install --cask cc-switch
   ```
   

* **手动下载**：从 [Releases 页面](https://github.com/farion1231/cc-switch/releases) 下载 `.dmg`。


</Tab>
<Tab zoneid="kZN9WtmceR" title="Linux">
<TabTitle>Linux</TabTitle>

* **Arch 发行版**：

   ```Bash
   paru -S cc-switch-bin
   ```
   

* **其他发行版**：根据架构（Debian / Ubuntu）从 [Releases 页面](https://github.com/farion1231/cc-switch/releases) 下载 `.deb` / `.rpm`，或者下载 `.AppImage`（通用）。


</Tab>
<Tab zoneid="V5QZE27ZKP" title="Windows">
<TabTitle>Windows</TabTitle>

* 从 [Releases 页面](https://github.com/farion1231/cc-switch/releases) 下载 `.msi` 安装包或 `.zip` 绿色版。


</Tab>
</Tabs>


<span id="1a4f8c6e"></span>
### 添加供应商


1. 在 CC Switch 中添加供应商：

   1. 在主界面顶部图标栏选中 Claude Code 图标，点击右上角  **+**  进入添加新供应商。

   2. 选择 **自定义配置** ，填写以下信息：

      * **API Key** ：替换为您的 [API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

      * **请求地址** ： `https://ark.cn-beijing.volces.com/api/compatible`

   3. 展开高级选项，根据当前支持的模型范围，分别配置 Sonnet、Opus、Fable、Haiku 模型，可配置的模型见[选择模型并获取 Model ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)。

      <div data-tips="true" data-tips-type="warning" data-tips-is-title="true" data-wrapper-indent="2">注意      </div>
      

      <div data-tips="true" data-tips-type="warning" data-wrapper-indent="2">建议 Haiku 设置为小尺寸模型。      </div>
      

   4. 选择右下角 **添加** ，完成供应商配置。

2. 回到首页，点击右侧 **启用** 按钮，新开一个 Claude Code 会话使配置生效。


<span id="572e98de"></span>
## 使用 Claude Code


* 启动Claude Code：进入项目目录，执行`claude`命令，即可开始使用Claude Code。

   ```Bash
   cd my-project
   claude
   ```
   

* 模型状态验证：输入`/status`确认模型状态。


<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/88d72ac928024768928848a622755b6b~tplv-goo7wpa0wc-image.image) </span>

<span id="572e98de"></span>
## 使用 Claude Code IDE 插件


1. 安装 Claude Code 并配置好环境变量，具体参考[接入Claude Code](https://www.volcengine.com/docs/82379/2160841#adcc555a)。


Claude Code IDE 插件依赖 Claude Code CLI 工具，需先完成 Claude Code的安装及配置。

2. 安装并使用 IDE 插件。

> 因 IDE 插件会迭代演进，以下内容仅供参考，具体的安装及使用可参考 [Visual Studio Code](https://code.claude.com/docs/en/vs-code)、[JetBrains IDEs](https://code.claude.com/docs/en/jetbrains)。



<Tabs>
<Tab zoneid="m94FWm0AEk" title="Claude Code VSCode 插件">
<TabTitle>Claude Code VSCode 插件</TabTitle>

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">Claude Code VSCode 插件支持在 VSCode 及基于 VSCode 的 IDE（如 Cursor、Trae 等）中使用。</div>


<span id="e712c542"></span>
### 安装插件

打开 VSCode，在扩展市场搜索`claude code`进行安装。

<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/6c39c8cb4ec84f03bb0ca2444804eac7~tplv-goo7wpa0wc-image.image) </span>

<span id="24ce507c"></span>
### 配置环境变量


1. 安装完成后，点击 VSCode 右上角的 Claude Code 图标，进入 Claude Code 页面。


<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/388665c0f9ed47379faa5291e180a6b2~tplv-goo7wpa0wc-image.image) </span>


2. 在对话框中输入 `/config`回车进入 settings 配置页面。

3. 在 **Claude Code: Environment Variables** 区域单击 **Edit in settings.json**，修改`claudeCode.environmentVariables`、`claudeCode.selectedModel`。


<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">需要替换配置信息中的以下信息：</div>



* <div data-tips="true" data-tips-type="tip"><code><ARK_API_KEY></code>：替换为 <a href="https://console.volcengine.com/ark/region:ark+cn-beijing/apikey">API Key</a>。</div>


* <div data-tips="true" data-tips-type="tip"><code><Model_Name></code>：替换为上述支持的模型名称，如 doubao\-seed\-evolving。</div>



```JSON
...
"claudeCode.environmentVariables": [
    {
        "name": "ANTHROPIC_BASE_URL",
        "value": "https://ark.cn-beijing.volces.com/api/compatible"
    },
    {
        "name": "ANTHROPIC_AUTH_TOKEN",
        "value": "<ARK_API_KEY>"
    },
    {
        "name": "ANTHROPIC_MODEL",
        "value": "<Model_Name>"
    }
],
"claudeCode.selectedModel": "<Model_Name>",
...
```


保存配置信息后，即可开始使用 Claude Code。


</Tab>
<Tab zoneid="eMqQCVKyn0" title="Claude Code Jetbrains 插件">
<TabTitle>Claude Code Jetbrains 插件</TabTitle>

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">Claude Code Jetbrains 插件支持 Jetbrains 的系列 IDE 如 IntelliJ IDEA、PyCharm、WebStorm 等。</div>


<span id=".5a6J6KOF5o-S5Lu2"></span>
### 安装插件

打开 Jetbrains IDE，在插件市场搜索`claude code`进行安装。

<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/5859916985a34036bb41f5097ba58f6c~tplv-goo7wpa0wc-image.image) </span>

<span id=".5byA5aeL5L2_55So"></span>
### 开始使用

安装完成后，重启IDE后，单击Claude Code 图标，进入 Claude Code 页面开始使用。


</Tab>
</Tabs>


<span id="64a1f959"></span>
# 接入 OpenCode

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">对于个人开发场景，推荐订阅 <a href="https://www.volcengine.com/docs/82379/2366394">Agent Plan 套餐</a>，接入教程参见 <a href="https://www.volcengine.com/docs/82379/2373738">快速开始</a>。</div>


<span id="2fabead0"></span>
## 安装步骤

在命令行界面，执行以下命令安装 OpenCode。

```Bash
npm install -g opencode-ai
```


安装结束后，执行以下命令查看安装结果，若显示版本号则安装成功。

```Bash
opencode --version
```


<span id="9c68a77b"></span>
## 配置工具


1. 编辑OpenCode的配置文件，路径如下：

* macOS / Linux：~/.config/opencode/opencode.json

* Windows：C:\Users\您的用户名.config\opencode\opencode.json


以配置模型`doubao-seed-evolving`为例，配置信息如下。

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>



* <div data-tips="true" data-tips-type="tip">替换配置信息中的<a href="https://console.volcengine.com/ark/region:ark+cn-beijing/apikey"><ARK_API_KEY\></a>。</div>


* <div data-tips="true" data-tips-type="tip">按需选择模型并获取 <a href="https://www.volcengine.com/docs/82379/1330310#b318deb2">Model ID</a>。</div>



```JSON
    {
      "$schema": "https://opencode.ai/config.json",
      "provider": {
        "myprovider": {
          "npm": "@ai-sdk/openai-compatible",
          "name": "volcengine",
          "options": {
            "baseURL": "https://ark.cn-beijing.volces.com/api/v3",
            "apiKey": "<ARK_API_KEY>"
          },
          "models": {
        "doubao-seed-evolving": { 
          "name": "doubao-seed-evolving"
        }
          }
        }
      }
    }
```


<span id="0bcfc664"></span>
## 开始使用


1. 启动OpenCode：

   ```Bash
   opencode
   ```
   

2. 输入`/models`，选择配置的`doubao-seed-evolving`模型并在 OpenCode 中使用。


<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/7dbba85371b14b998a8ab8324e8d8bd2~tplv-goo7wpa0wc-image.image) </span>

<span id="0cfc8e87"></span>
# 接入 OpenClaw（原 Clawdbot）

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">对于个人开发场景，推荐订阅 <a href="https://www.volcengine.com/docs/82379/2366394">Agent Plan 套餐</a>，接入教程参见 <a href="https://www.volcengine.com/docs/82379/2373738">快速开始</a>。</div>


<span id="2754877f"></span>
## 安装步骤


1. 执行以下命令安装 OpenClaw。



<Tabs>
<Tab zoneid="BqP8wpUPb2" title="macOS">
<TabTitle>macOS</TabTitle>

```Bash
curl -fsSL https://openclaw.ai/install.sh | bash
```



</Tab>
<Tab zoneid="ckjPk2SRLP" title="Windows">
<TabTitle>Windows</TabTitle>

Windows PowerShell 环境下安装命令如下：

```Bash
iwr -useb https://openclaw.ai/install.ps1 | iex
```



</Tab>
</Tabs>



2. 根据提示信息完成 OpenClaw 配置，配置信息如下。

   <div data-tips="true" data-tips-type="warning" data-tips-is-title="true" data-wrapper-indent="1">注意   </div>
   

   <div data-tips="true" data-tips-type="warning" data-wrapper-indent="1">OpenClaw 在不断迭代，如果实际使用与以下配置存在差异，可以选择 "Skip" 或默认选项完成配置流程，后续可以参考文档配置并使用 Agent Plan。   </div>
   

   
   <span aceTableMode="table" aceTableWidth="3,3"></span>
   |提示信息 |配置 |
   |---|---|
   |I understand this is personal\-by\-default and shared/multi\-user use requires lock\-down. Continue? |选择 "Yes" |
   |Setup mode |选择 “QuickStart” |
   |Model/auth provider |选择 "Skip for now"，后续可以配置。 |
   |Default model |选择 "Keep current" |
   |Select channel (QuickStart) |选择 “Skip for now”，后续可以配置。 |
   |Search provider |选择 “Skip for now” |
   |Configure skills now? (recommended) |选择 “No”，后续可以配置。 |
   |Enable hooks? |选择 "Skip for now"。选择方式：按空格键选中选项，按回车键进入下一步。 |
   |How do you want to hatch your bot? |选择 "Hatch in Terminal"。 |
   


<span id="28931850"></span>
## 配置工具

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning"><code>glm-5.2</code>、<code>deepseek-v4-flash</code>、<code>deepseek-v4-pro</code> 支持 1M 上下文窗口用于包含大型代码库的长会话，可以通过 <code>contextWindow</code> 字段显式指定窗口大小。</div>



<Tabs>
<Tab zoneid="AKoL58VHYO" title="Web UI 方式">
<TabTitle>Web UI 方式</TabTitle>

1. 执行以下命令打开 Web UI。


```Bash
openclaw dashboard
```



2. 在左侧菜单栏选择**配置** \- **Settings** \- **Advanced**，单击 **Open** 查看并修改配置信息。具体配置信息如下，其中需要修改的核心配置信息如下：

* baseUrl：https://ark.cn\-beijing.volces.com/api/v3

* apiKey：[获取API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

* models：[选择模型并获取 Model ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)


<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>



* <div data-tips="true" data-tips-type="warning">如果已经配置过 OpenClaw，请勿直接覆盖原有配置，建议根据提供的配置更新<code>models</code>、<code>agents</code> 和 <code>gateway</code> 节点信息。其中<code>models</code>节点包含支持的模型列表。</div>



```JSON
{
  "models": {
    "providers": {
      "volcengine": {
        "baseUrl": "https://ark.cn-beijing.volces.com/api/v3",
        "apiKey": "<ARK_API_KEY>",
        "api": "openai-completions",
        "models": [
          {
            "id": "doubao-seed-1-8-251228",
            "name": "doubao-seed-1-8-251228"
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "volcengine/doubao-seed-1-8-251228"
      },
      "models": {
        "volcengine/doubao-seed-1-8-251228": {}
      }
    }
  },
  "gateway": {
    "mode": "local"
  }
}
```



3. 配置完成后，先保存配置文件，然后单击 **Update** 更新配置，配置更新完成后需要重新连接服务进入 Web UI。

   <span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/be24b57cff314b749016abd2fd3ada7a~tplv-goo7wpa0wc-image.image) </span>


</Tab>
<Tab zoneid="qIS6F2Vuav" title="终端方式">
<TabTitle>终端方式</TabTitle>

1. 在终端执行以下命令打开 OpenClaw 配置文件。


```Bash
nano ~/.openclaw/openclaw.json
```



2. 修改配置信息，其中需要修改的核心配置信息如下：

* baseUrl：https://ark.cn\-beijing.volces.com/api/v3

* apiKey：[获取API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

* models：[选择模型并获取 Model ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)


<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>



* <div data-tips="true" data-tips-type="warning">如果已经配置过 OpenClaw，请勿直接覆盖原有配置，建议根据提供的配置更新<code>models</code>、<code>agents</code> 和 <code>gateway</code> 节点信息。其中<code>models</code>节点包含支持的模型列表。</div>



```JSON
{
  "models": {
    "providers": {
      "volcengine": {
        "baseUrl": "https://ark.cn-beijing.volces.com/api/v3",
        "apiKey": "<ARK_API_KEY>",
        "api": "openai-completions",
        "models": [
          {
            "id": "doubao-seed-1-8-251228",
            "name": "doubao-seed-1-8-251228"
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "volcengine/doubao-seed-1-8-251228"
      },
      "models": {
        "volcengine/doubao-seed-1-8-251228": {}
      }
    }
  },
  "gateway": {
    "mode": "local"
  }
}
```



3. 配置完成后保存文件，并在终端执行以下命令重启服务使更改生效。


```Bash
openclaw gateway restart
```



</Tab>
</Tabs>


<span id="800352f1"></span>
## 开始使用


* 打开 TUI，并查看 Gateway 状态。


```JSON
openclaw tui
/status
```



* 打开 Web UI，在 Chat 页面进行交互。


```JSON
openclaw dashboard
```


<span id="293b4349"></span>
# 接入 TRAE

<span id="b81d6e61"></span>
## 安装 TRAE CN

访问 [TRAE 官网](https://www.trae.cn/)下载并安装对应操作系统的版本。

<span id="eb2647c8"></span>
## 配置工具


1. 选择 **个人用户** 入口登录后，点击界面右上角的 **设置** 图标，进入设置中心。

2. 在左侧导航栏中，选择 **模型** ，在模型管理页面进行配置。

3. 点击  **+ 添加模型** 按钮，界面上显示 **添加模型** 窗口，在窗口中配置以下信息。

* **服务商** ： **火山引擎**

* **模型** ：

   * 直接从列表中选择 TRAE 预置的模型（均为默认版本）。

   * 若希望使用其他模型，单击 **使用其他模型** ，然后在输入框中填写 **模型 ID** 配置信息。

* **API 密钥** ：[获取API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)


<span id="1b160428"></span>
## 切换模型

在 AI 对话输入框的右下角，单击当前模型名称，在模型列表中，选择配置的模型。

选定模型后，即可使用 TRAE 进行开发任务了。

<span id="8cf0e46e"></span>
# 接入 Cline

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">对于个人开发场景，推荐订阅 <a href="https://www.volcengine.com/docs/82379/2366394">Agent Plan 套餐</a>，接入教程参见 <a href="https://www.volcengine.com/docs/82379/2373738">快速开始</a>。</div>


<span id="9e8b45ff"></span>
## 安装步骤

打开 VSCode，在扩展市场搜索`Cline`安装。

<span id="a1998577"></span>
## 配置工具

Cline插件安装完成后，您需要配置以下信息。


* **API Provider** ：`OpenAI Compatible`（Agent Plan 接口兼容 OpenAI 标准）

* **Base URL** ：`https://ark.cn-beijing.volces.com/api/v3`

* **API Key** ：[获取API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

* **Model ID** ：按需选择模型并获取 [Model ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)


配置完成后，就可以在输入框中输入需求，与模型进行交互。

<span id="43252d72"></span>
# 接入 Cursor

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">对于个人开发场景，推荐订阅 <a href="https://www.volcengine.com/docs/82379/2366394">Agent Plan 套餐</a>，接入教程参见 <a href="https://www.volcengine.com/docs/82379/2373738">快速开始</a>。</div>


<span id="eb949c8b"></span>
## 安装步骤

官网下载安装包：通过[Cursor官网](https://cursor.com/features)下载并安装Cursor。

<span id="14785575"></span>
## 配置工具

<div data-tips="true" data-tips-type="tip" data-tips-is-title="true">说明</div>


<div data-tips="true" data-tips-type="tip">由于 Cursor 的限制，只有订阅了 Cursor Pro 及以上套餐的用户才支持自定义配置模型。</div>


Cursor安装完成后，Models 模块的具体配置如下：


* OpenAI API Key：[获取API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

* Override OpenAI Base URL：`https://ark.cn-beijing.volces.com/api/v3`

* Add Custom Model：按需选择模型并获取 [Model ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)


配置完成后，即可在聊天面板中选择配置的模型进行交互。

<span id="803716d6"></span>
# 接入 Roo Code

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">对于个人开发场景，推荐订阅 <a href="https://www.volcengine.com/docs/82379/2366394">Agent Plan 套餐</a>，接入教程参见 <a href="https://www.volcengine.com/docs/82379/2373738">快速开始</a>。</div>


<span id="ea3c94f0"></span>
## 安装步骤

打开 VSCode，在扩展市场搜索`Roo Code`进行安装，安装完成后选择信任发布者。

<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/dd47c5150044469cb4e95b8de067d817~tplv-goo7wpa0wc-image.image) </span>

<span id="a9ebc613"></span>
## 配置工具

安装完成后，配置以下信息。


* **API Provider** ：`OpenAI Compatible`（Agent Plan 接口兼容 OpenAI 标准）

* **Base URL** ：`https://ark.cn-beijing.volces.com/api/v3`

* **API Key** ：[获取API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

* **Model** ：按需选择模型并获取 [Model ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)


配置完成后，就可以在输入框中输入需求，与模型进行交互。

<span id="398e865d"></span>
# 接入 Kilo Code

<div data-tips="true" data-tips-type="warning" data-tips-is-title="true">注意</div>


<div data-tips="true" data-tips-type="warning">对于个人开发场景，推荐订阅 <a href="https://www.volcengine.com/docs/82379/2366394">Agent Plan 套餐</a>，接入教程参见 <a href="https://www.volcengine.com/docs/82379/2373738">快速开始</a>。</div>


<span id="7518dbe3"></span>
## 安装步骤

打开 VSCode，在扩展市场搜索`kilo code`进行安装，安装完成后选择信任发布者。

<span>![图片](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/3e991c168c0c49bc9449f6f6efc29bd7~tplv-goo7wpa0wc-image.image) </span>

<span id="3a8a6d3b"></span>
## 配置工具

选择Use your own API key，然后配置以下信息。


* **API Provider** ：`OpenAI Compatible`（Agent Plan 接口兼容 OpenAI 标准）

* **Base URL** ：`https://ark.cn-beijing.volces.com/api/v3`

* **API Key** ：[获取API Key](https://console.volcengine.com/ark/region:ark+cn-beijing/apikey)

* **Model** ：按需选择模型并获取 [Model ID](https://www.volcengine.com/docs/82379/1330310#b318deb2)


配置完成后，就可以在输入框中输入需求，与模型进行交互。



