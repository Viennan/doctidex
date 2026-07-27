# 初始需求：doctidex Git Agent Plugin

状态：Initial requirement baseline，历史记录，非规范性

来源：原 `impls/docs/agent-git-plugin.md`

本文档保留 `doctidex-git` 首个完整用户 surface 需求与方案基线。第 1 至 4 节记录问题、
设计目标、心智模型和信息边界；第 5 至 7 节记录拟定的 Skills、CLI 与工作流；第 8 至
10 节记录实现约束和失败处理；第 11 节记录当时的验收标准。正文主体按原方案保留，
不把后续实现事实回写成原始要求。

本文档设计 `impls/agent-plugins/doctidex-git/` 对用户和 agent 暴露的操作界面。它面向在
Git 管理的目录中创建、读取、查询、维护和审阅 doctidex 目录树的场景。

本文档以 [`spec/overview.md`](../../../../spec/overview.md) 为唯一协议依据。旧的
`spec/reference-implementations/git-agent-scaffold.md` 只提供能力目标和 Git 协作
经验，不作为字段、路径或行为约定的来源。若本文档与协议正文冲突，以协议正文
为准。

本文档形成时用于描述目标 surface。当前语言无关设计以
[Architecture](../architecture/index.md) 为准；当前 Python 代码、CLI 字段及已知限制见
[Python Details](../details/python/index.md)。当前设计或实现与本记录不同时，不修改本记录
来掩盖演进结果。

## 1. 设计目标

插件需要让 agent 在不阅读插件源码、不理解缓存或 worktree 布局、也不预先熟悉
全部 doctidex 协议细节的情况下完成以下工作：

- 在现有 Git 工作目录中创建或接管 doctidex 目录树；
- 使用 `index.md` 提高导航和查询效率，同时保留 agent 自由探索目录树的能力；
- 声明、恢复、查看和显式同步 Git 类型的外部目录树挂载；
- 在明确的单一 doctidex 根内维护内容、索引和变更记录；
- 为挂载源打开独立的可写维护根，并协调涉及多个根的任务；
- 校验协议符合性、读写边界和链接，审阅 Git 变化；
- 在失败时获得面向当前任务的原因、已保留结果和可执行的下一步。

插件的正常输出必须使用用户已经接触到的概念：doctidex 根、内部路径、挂载路径、
Git URL、声明 revision、有效 commit、维护范围和 Git 变化。共享对象库、缓存键、
锁、worktree 管理和映射方式不是公开心智模型。

### 1.1 非目标

本方案不负责：

- 修改或补充 doctidex 协议；
- 规定分类体系、内容模板或查询引擎；
- 将一个 Git 仓库强制等同于一个 doctidex 根；
- 自动执行 `commit`、`push`、`reset`、`clean`、合并或远端发布；
- 把多个独立 doctidex 根伪装成一个可同时写入的目录树；
- 接管、替代或限制 agent 已有的文件浏览、搜索和读取工具；
- 向用户固定内部 clone、缓存、worktree、锁或文件系统映射布局。

### 1.2 CLI 客观性原则

本原则适用于插件的全部 CLI 命令和底层代码工具。CLI **不得内置 AI 能力**，不得
调用语言模型、生成模型或其他基于 prompt 的推理服务，也不得要求配置模型、prompt
或模型凭据。给定相同参数、目录树状态和外部 Git 状态，CLI 应产生相同的结构化
结果和文件操作。

CLI 只完成可以由明确规则判定的客观工作，例如：

- 解析 frontmatter、Markdown link 和 Git mount 声明；
- 发现根、负责 index、适用 log 和过滤边界；
- 规范化路径、判断路径上下文、枚举 index 中可解析的 link 和待核对索引候选；
- 读取 Git status、diff 和 revision，执行明确指定的 Git 与 mount 操作；
- 校验协议结构、字段、路径、index/log 连续性和读写边界；
- 按固定 schema 输出结果和基于明确错误类型的动作提示。

需要理解任务意图、评价内容质量或生成语义内容的主观工作必须由 agent 完成，包括：

- 决定应阅读、修改或优先处理哪些内容；
- 撰写、概括或重组 `index.md` 正文及其索引描述；
- 判断某项变化是否重要，并撰写 `log.md` 变更记录；
- 设计目录结构、选择跨根维护顺序、解释变更影响和形成审阅结论。

CLI 可以提供不改变语义的格式化能力，例如按既定 schema 排列 YAML 字段、规范
Markdown 空白或格式化由 agent 提供的 log 条目；格式化必须以调用方已经提供的
内容为输入，不得自行补写描述、摘要、理由或变更记录。是否提供独立 format 命令由
后续实现决定，本方案不要求该命令必须存在。

协议不规定 index 条目的固定格式，也不规定 log 条目的固定结构。CLI 因此只能报告
“未发现可由已公开规则解析的索引引用”“存在尚待判断是否重要的变化”等候选事实，
不得据此单独判定索引语义覆盖不足、log 遗漏或协议不符合。自由文本是否构成可识别的
索引条目、某项变化是否重要以及描述是否充分，均由 agent 判断。

Skills 可以由具备推理能力的 agent 执行，并使用 CLI 返回的客观事实完成上述主观
工作；CLI 与 Skill 的职责不得因此混合。

### 1.3 CLI 输出规模原则

CLI 必须控制默认输出规模，任何可能枚举文件、目录、link、finding、Git 变化、mount
或维护根的命令都不得无界输出。人读输出和 `--json` 使用同一结果预算，不能通过
切换格式绕过限制。

默认输出应根据目录结构进行确定性的 collapse 与 structural summary：

- 优先按 doctidex 根、负责 index 和目录层级分组；
- 小型目录可以展开明细，大型目录折叠为目录节点；
- 折叠节点只报告路径、直接项数量、后代数量，以及按条目类型、状态或严重度计算的
  数量，不生成内容摘要或主观结论；
- 明细按规范化内部路径或其他已文档化的稳定规则排序，不能随机选取代表项；
- error、warning 等重要结果也受预算约束，但必须在结构摘要中保留完整计数，并允许
  agent 按严重度继续展开。

所有列表型命令都必须提供逐步收窄或展开的机制，至少包括适用的 `--limit`、
`--depth`、PATH 范围和 `--cursor`。达到预算时，输出必须明确包含：

- `truncated: true`；
- 匹配总数、当前返回数量和折叠目录数量；
- 下一页 cursor 或一条精确的继续查询命令；
- 可用于下钻的目录、负责 index、状态或严重度维度。

实现必须为默认明细数量和输出字节数设置稳定、文档化的上限。即使实现提供
`--all`，它也只能是显式 opt-in；预估结果可能过大时，应建议按路径或 cursor 分页，
不得把大规模输出直接作为普通 Skill 调用的默认结果。

本节的 summary 仅指由计数和分组得到的客观结构摘要，不允许借此调用 AI 或生成
目录内容的语义摘要。agent 根据逐页取得的事实决定是否继续展开以及如何概括内容。

## 2. 用户心智模型

### 2.1 doctidex 根是操作范围，Git 仓库是协作载体

每次操作都针对一个明确的 doctidex 根。根 `index.md` 是读取入口，也定义当前
目录树的过滤配置和唯一挂载表。Git 提供版本、差异和协作能力，但 Git 仓库根与
doctidex 根不要求相同；一个仓库也可能包含多个彼此独立的 doctidex 根。

插件从当前文件或显式路径发现根。发现结果不唯一时，插件不得猜测，必须列出候选
根并要求 agent 或用户选定。

### 2.2 doctidex 是导航层，不是文件访问网关

agent 可以继续使用其原有的文件工具自由浏览、搜索和读取 Git 工作目录，包括
`find`、全文搜索、文件读取、编辑器或运行环境提供的其他成熟工具。插件不得要求
所有读取都经过 Skill 指定的 CLI，也不得拦截每次文件访问或把 index 导航变成唯一
允许的探索顺序。

doctidex 提供的是更高效、更可靠的目录地图：根和负责 `index.md` 给出入口与范围，
link 给出相关内容，过滤配置表达索引、排除、保护和原子边界，mount 声明定位外部
目录树。Read Skill 可以利用这些信息推荐优先读取路径、引导按需恢复外部内容并
解释来源，也可以通过协议感知工具输出负责 index/log、路径上下文、link 解析和 mount
状态等辅助信息。实际文件浏览、搜索和读取仍由 agent 使用自己的工具完成。

自由读取不改变维护边界。agent 可以检查 excluded、protected 或 mount 内容来理解
现场，但写入仍必须遵守相应维护范围，外部源仍需从其独立维护根修改。

### 2.3 内部路径不是操作系统绝对路径

`/guide/index.md` 和 `/.doctidex/mounts/api/index.md` 中开头的 `/` 均表示相对于
link 所在文档的链接根的绝对内部路径，不表示主机文件系统的 `/`。CLI 默认利用当前
工作目录选择命令上下文，使单根内的常见操作无需反复传根。需要从宿主工作目录解释
挂载文档中的 link 时，`resolve` 接受可选的 link 来源文件路径，并由这个 agent 已知
且可访问的文件位置确定链接根；不要求 agent 先切换目录，也不要求其直接指定一个
本来就需要推断的链接根。

当前工作目录只是默认上下文，不是文件访问限制。短暂跨根阅读可保留宿主工作目录并
传入目标或 link 来源；当一项较大、步骤较多的工作集中在单一明确根时，agent 可以
进入该根开展工作，以简化后续参数和根选择。

### 2.4 挂载是只读入口，源根是维护入口

外部 doctidex 目录树只通过根 `index.md` 中的 `doctidex.mounts` 声明，并呈现在
`/.doctidex/mounts/<name>` 下。挂载始终引入 Git URL 所标识的完整源目录树，
不存在子树选择。

mount 采用 lazy restore：声明存在不表示源内容已经出现在工作目录中，插件也不会
在初始化、普通仓库浏览或添加声明时预先恢复全部 mount。agent 使用自己的工具阅读
mount 引入的外部 doctidex 目录树时，如果任务必须读取的文件或路径不存在，应按
Read Skill 中的指引检查其 mount 状态，并调用专门的 Mount 工作流或
`doctidex-git mount prepare <mount-path>`。恢复成功后，内容才通过工作目录中的
mount path 供 agent 原有文件工具直接读取。

在宿主根范围内，已经恢复的挂载内容可读取但不可写入，也不属于宿主的索引、日志、
符合性或维护范围。要修改挂载源，agent 必须让插件打开该源自己的独立维护根，
然后从该根执行维护、校验和 Git 审阅。

### 2.5 声明 revision 与有效 commit 是两个概念

Git mount 使用 commit、tag 或 branch 之一声明 revision：

- **声明 revision** 是根 `index.md` 中用户选择的 selector；
- **有效 commit** 是插件为当前工作上下文实际读取的不可变 commit。

首次 prepare 解析声明 revision 并得到有效 commit；此后的普通读取、恢复和离线
校验沿用该有效 commit，不会因为远端 branch 或 tag 移动而静默改变内容。只有显式
同步才重新查询远端并切换有效 commit。同步前后插件都显示实际 commit，以便 agent
判断内容是否变化。

### 2.6 多根任务是多个独立结果

跨宿主和挂载源的任务会被拆成多个维护范围。每个范围有自己的根、基准 revision、
Git diff、校验结果和后续 Git 动作。插件可以规划顺序和汇总结果，但不会把这些
变化描述成一次单根写入，也不会替用户提交或推送。

## 3. 协议约束在插件中的体现

插件必须把以下规则内建到所有 Skill 和 CLI 中，使 agent 无需自行补全协议判断：

1. 只有包含 `doctidex.root: true` 的根 `index.md` 可以声明
   `doctidex.mounts`。
2. 根 `doctidex.excludes` 必须包含 `path: .doctidex/mounts`，无论该路径是否
   物理存在。
3. 每个 `mount_path` 都是经过路径段规范化的绝对内部路径，且是
   `/.doctidex/mounts` 的严格子目录；不得重复或互为祖先与后代。
4. 一个 mount 引入 `url` 标识的完整源目录树。插件不支持或接受 `src_path`。
5. 指向符合 doctidex 的外部目录树的路径引用使用
   `/.doctidex/mounts/...` 绝对内部路径，不使用相对路径。
6. 挂载内容不由宿主索引，不写入宿主 `log.md`，不接受以宿主为范围的维护。
7. 一次从某个根开始的路径解析只有该根的一套 mount 命名空间。进入挂载源后再次
   遇到 `.doctidex/mounts`，会回到起始根的命名空间，而不是递归进入源自己的
   mount 表。
8. 源文档中的普通绝对内部 link 以源自身 doctidex 根为链接根；以
   `/.doctidex/mounts` 开头的 link 是上一条规则的例外。
9. 物理目录、符号链接或文件系统挂载只有在根 mount 声明存在时才具有
   `doctidex_mount` 语义。

### 3.1 插件强制 Git ignore 规则

对于每个由本插件管理且位于 Git worktree 内的 doctidex 根，其文件系统路径
`<doctidex-root>/.doctidex/mounts/` **必须被 Git ignore**。根目录中的
`.gitignore` 必须包含能够覆盖该路径的有效规则；标准写法为：

```gitignore
/.doctidex/mounts/
```

这里开头的 `/` 相对于该 `.gitignore` 所在的 doctidex 根，不是操作系统根目录。
仅依赖用户全局 ignore 或 `.git/info/exclude` 不满足本插件要求，因为规则需要随
目录树的 Git 内容一起传递。

此规定是插件实现的强制要求，不是对 doctidex 协议正文的追加。它与根
`index.md` 中的 `excludes: [{path: .doctidex/mounts}]` 必须同时成立：`excludes`
定义目录树语义边界，`.gitignore` 防止挂载的物理呈现进入 Git 状态和提交，两者
不能互相替代。

若该路径下已经存在 tracked 文件，仅添加 ignore 规则不会使其脱离 Git index。
插件必须停止 mount 准备或写操作，列出相关文件并给出从 Git index 移除它们的
下一步；不得自动执行 `git rm --cached` 或删除工作区内容。

例如，以下是插件接受的 Git mount 扩展：

```yaml
---
type: index
doctidex:
  type: index
  root: true
  excludes:
    - path: .doctidex/mounts
  mounts:
    - type: git
      url: https://example.com/design.git
      revision:
        branch: main
      mount_path: /.doctidex/mounts/design
---
```

`revision` 是本插件为 `type: git` 定义的扩展字段。它必须是 YAML 映射，并且只含
`commit`、`tag` 或 `branch` 中的一个非空字符串。URL 对应 checkout 的根必须
就是待挂载的完整源目录树；本扩展不提供从 Git 仓库内部选择 doctidex 子目录的
方式。

路径：

```text
/.doctidex/mounts/a/guide/.doctidex/mounts/b/index.md
```

按 mount 命名空间不可嵌套规则解析为：

```text
/.doctidex/mounts/b/index.md
```

Read Skill 必须向 agent 解释该路径规则，`resolve` 可以给出规范化结果和 mount
状态，`check` 负责校验相关 link，mount 恢复实现必须维持相同语义。这些辅助能力
用于帮助 agent 正确使用自己的文件工具，不构成另一套文件访问通道。

### 3.2 Regex 方言

协议暂未规定 `atomic_entries`、`excludes` 和 `protected` 中 `regex` 的具体方言。
本插件统一采用成熟第三方 Python `regex` 库的 **VERSION1** 方言。实现依赖必须固定
`regex` 版本，不能直接绑定系统正则动态库，也不能随宿主语言默认正则引擎而变化。
VERSION1 提供广泛的 Perl-compatible 与 Unicode 正则能力，并与协议示例使用的语法
一致。该选择是公开的实现约定，不是 doctidex 协议要求。

匹配规则如下：

- 输入是相对于负责 index 所在目录、完成 `.` 和 `..` 路径段规范化后的完整相对
  路径，路径分隔符统一为 `/`；
- 对完整路径字符串执行 `regex` VERSION1 search；插件不隐式添加 `^`、`$` 或其他
  锚点；
- 输入和 pattern 按 Unicode 字符串处理，并启用 VERSION1 Unicode 语义；
- 默认区分大小写；需要改变行为时，由 pattern 使用 VERSION1 inline option 明确表达；
- 同一 pattern 对文件和目录使用相同匹配规则，目录后不附加 `/`；
- pattern 编译失败是确定性的结构错误。诊断必须指出 index、配置字段和列表位置，
  提供有界的 VERSION1 错误说明，并提示修正 pattern 后重试 `check`。

Skill 面向 agent 说明 regex 时必须包含上述路径基准、search 语义和大小写规则，使
agent 无需阅读实现代码即可编写和排查过滤条件。

## 4. 公开信息边界

### 4.1 agent 正常可见的信息

插件应按操作需要提供：

- 当前 Git 工作目录、选定的 doctidex 根和根 `index.md`；
- 当前读取或维护的内部路径范围；
- 当前路径的宿主范围、来源、负责 index、适用 log、条目属性和推荐导航入口；
- `atomic_entries`、`excludes`、`protected` 和 mount 形成的边界；
- mount path、Git URL、声明 revision、有效 commit 和可读状态；
- 是否需要网络或凭据，以及操作是否会写文件；
- 为外部源打开的可写维护根路径、基准 revision 和允许写入范围；
- dry-run 计划、实际文件变化、校验结果和未完成事项；
- 需要用户授权或决定的 Git 动作。

维护根的可访问文件系统路径属于当前任务必需信息，可以显示给 agent。插件不得让
agent 由该路径推断或管理内部存储结构。

### 4.2 默认不公开的信息

正常输出、Skill 文档和持久化 doctidex 内容不得包含：

- source key、checkout key、缓存 key 或内部 schema；
- clone、对象库、只读 revision checkout 的实际布局；
- Git common-dir 关联和 worktree 管理命令；
- 锁名、锁文件、fetch 批次、引用计数或垃圾回收状态；
- 使用了符号链接、overlay、虚拟 resolver 还是其他映射机制；
- 仅供实现排障的内部路径和堆栈。

显式 debug 模式可以输出诊断 ID，并将详细记录写到实现私有位置；正常错误仍只给
用户层原因和动作。debug 信息不得成为正常工作流的前置条件。

### 4.3 公开状态词

Skills、CLI 人读输出和 `--json` 应使用一致的有限状态词：

| 对象 | 状态 | 用户层含义 |
|---|---|---|
| 操作 | `ok` | 请求已完成 |
| 操作 | `warning` | 可用结果已产生，但存在未经验证或建议处理的事项 |
| 操作 | `blocked` | 请求未完成，需要执行所列动作或获得用户输入 |
| 协议结构 | `pass` / `fail` | CLI 可确定的协议结构是否通过 |
| 语义复核 | `clear` / `required` | 是否存在需要 agent 判断的索引或 log 候选 |
| 插件就绪 | `ready` / `blocked` / `not_applicable` | 当前 Git 现场是否允许执行相关插件操作 |
| mount | `not_prepared` | 声明结构有效，但 lazy mount 尚未恢复；需要读取时执行 prepare |
| mount | `ready` | 当前有效 commit 可通过逻辑 mount path 读取 |
| mount | `needs_network` | 本地缺少首次读取所需对象，需要联网 |
| mount | `needs_auth` | 需要用户提供对应 Git source 的访问权限 |
| mount | `invalid` | 根 mount 声明不符合协议或 Git 扩展约定 |
| mount | `unavailable` | URL 或声明 revision 当前无法取得 |
| maintenance | `ready` | 独立维护根已就绪且可写 |
| maintenance | `has_changes` | 维护结果已保留，等待校验或交付 |
| maintenance | `awaiting_user_git_action` | 需要用户决定或执行 Git 协调动作 |

`needs_network`、`needs_auth` 和 `unavailable` 只描述外部源可取得性，不得用来表达
某种内部映射方式失败。远端是否存在更新未经检查时，以 `warning` 附加
`remote revision not checked`，当前 mount 仍保持 `ready`。

## 5. Skills

Skills 帮助 agent 理解用户意图、识别 doctidex 结构并组织工作流。CLI 是 Skills
可以复用、agent 也可以按需直接使用的协议感知辅助面，不是文件访问的强制入口。
Guide 与专项 Skill 的公开说明合并后必须完整写明：适用意图、输入与前置条件、读写
边界、是否触网、运行现场、成功结果、可恢复问题的下一步和必须向用户升级的条件。

Skills 形成显式且无环的阅读链条。`doctidex-git-guide` 集中建立用户心智模型、共享
术语、路径参数类型、通用 CLI 语法、输出状态、安全基线和专项工作流路由。agent 在
首次使用、概念不熟悉或任务跨越多个工作流时先加载 Guide；心智模型已经建立后，
直接加载所需专项 Skill，不在每条命令前重复加载 Guide。专项 Skill 可以按条件引导
回 Guide，也可以在职责边界处转交另一个专项 Skill。

共享约定只在 Guide 中解释一次；专项 Skill 必须在工作流之前解释自身新增的术语，
并为其引入的每条命令给出完整用户契约，包括准确调用形式、参数类型与限制、必填与
可选项、省略或默认行为、根选择方式、读写与触网影响、适用时的 dry-run/apply 和
批处理语义、agent 决策所需的返回字段，以及失败后的可执行动作。Guide 与一个相关
专项 Skill 应足以让 agent 完成对应工作流，无需猜测参数或查阅实现文档。

Skill 必须按已发布产品的使用环境编写。可以说明公共分发名、公共命令和通用安装
方式，但不得引用本实现源码仓库的目录布局、editable 安装命令、测试入口或调试
现场；这些内容属于实现仓库的 `AGENTS.md`。CLI 如何生成结果、必须维护何种内部
状态等实现约束也不得写成 Skill 指令；Skill 只说明 agent 需要采取的动作、可观察
结果和用户需要作出的决定。

### 5.1 `doctidex-git-guide`

用于第一次接触插件、需要确认术语或命令规律，或者任务跨越多个专项工作流的场景。
它说明 doctidex 根、命令上下文、宿主根、内部路径、link 来源文件、mount path、
声明 revision、有效 commit、lazy mount、维护根等用户层概念，区分文件系统路径与
doctidex 内部路径，并解释 cwd 默认上下文、`--json`、列表预算与分页、显式
dry-run/apply、命令触网类别和公共状态词。

Guide 不执行领域工作，也不要求 agent 按固定顺序使用 CLI。它根据用户意图路由到
Setup、Read、Mount、Maintain、Workspace、Validate 或 Review，并列出常见的跨
Skill 链条。加载 Guide 后，agent 只需继续读取实际任务所需的专项 Skill。

### 5.2 `doctidex-git-setup`

用于“在这个 Git 管理的目录中创建 doctidex”或“检查并接管已有 doctidex 根”。

它会先发现 Git 与 doctidex 上下文，展示 dry-run，再最小化创建或补全根
`index.md`。它保证必需 frontmatter、根标识和
`excludes: [{path: .doctidex/mounts}]`，并确保根 `.gitignore` 有效忽略
`/.doctidex/mounts/`；仅当 `.git` 位于目录树范围内时，才规划相应协议排除。
`log.md` 是可选文件，不因初始化而强制创建。

`init` CLI 只创建或调整可按规则确定的 frontmatter、过滤配置和 `.gitignore`，并
客观列出待核对索引候选。目录说明、索引描述和其他 `index.md` 正文由 agent 生成；
CLI 不得根据文件内容自动撰写这些文本。

结构初始化成功后，agent 得到选定根、创建或修改的文件、待核对索引候选和离线校验
结果。agent 随后判断已有自由文本是否已经构成有效索引，为确有缺口的条目撰写正文，
并再次校验。Setup Skill 只有在 agent 完成这一步后才报告目录树接管完成；它不创建
公开的运行时目录，不提交 Git 变化，也不自动添加外部挂载。

### 5.3 `doctidex-git-read`

用于向 agent 提供 doctidex 目录树的推荐阅读方法、路径语义和 lazy mount 恢复
指引。Read Skill 不需要重复实现 agent 已有工具已经擅长的通用文件读取、目录遍历
或全文搜索，但可以提供依赖 doctidex 结构和语义的辅助工具；实际探索策略和文件
工具始终由 agent 自主选择。

Read Skill 的基本定位是“阅读指南”，不是“文件读取代理”。其指引必须包含：

- 将根 `index.md` 视为推荐入口，优先利用其摘要和 link 缩小候选范围；这是效率
  建议，不是必须遵循的读取顺序；
- 进入具有自身 `index.md` 的子目录后，优先使用该 index 理解局部范围；没有局部
  index 时，可参考最近负责的祖先 index；
- 将 `log.md` 视为可选的变更背景，在需要理解近期演进、历史决策或变化原因时读取，
  不要求每次任务都读取，也不以 log 代替当前文件和 index；
- 将 `atomic_entries` 作为整体理解和索引的提示，而不是禁止 agent 检查其内部文件；
- 明确 `excludes` 表示内容不属于当前 doctidex 目录树，`protected` 表示当前维护
  范围不可写；两者都不限制 agent 为理解仓库现场而读取；
- 说明相对 link、绝对内部路径、链接根和 mount 命名空间不可嵌套的规则；
- 当 index 提供的信息不足、线索不完整或全局搜索更合适时，直接使用 agent 自带
  工具扩大探索范围，不需要 Skill 或 CLI 许可。

Read Skill 可以按需使用以下协议感知辅助信息，但不得把它们变成阅读前置条件：

- 当前路径所属的宿主根；若属于当前树，则给出负责 index 和适用 log；若属于 mount，
  给出宿主 mount 声明上下文，并在源可读时另行给出源目录树的根、负责 index 与适用
  log；
- 当前路径是否被宿主排除、来源是本地还是 mount，以及是否具有 atomic、protected
  等可以同时成立的条目属性；
- index 中与当前任务相关的候选入口和 link，不代替 agent 对文件内容的判断；
- link 规范化后的内部路径、链接根和对应工作目录路径；
- mount 的声明 revision、有效 commit、lazy 状态和需要时的恢复动作。

这些辅助信息由 CLI 按明确规则提取；哪些入口与当前任务相关、应先读什么以及如何
解释内容，仍由 agent 判断。

Read Skill 应优先减少不必要的上下文切换和工具调用：同一根内规范化的普通路径可按
规则直接推断；从宿主浏览已挂载文档时，可以把包含 link 的可访问文件路径传给
`resolve`，由其区分源根普通绝对 link 与回到宿主 mount 命名空间的 link。单根内持续
探索时，也可以进入该根后复用 cwd 默认上下文。`resolve` 是消歧和 mount 状态辅助，
不是每个 link 都必须经过的访问网关。

mount 采用被动的 lazy 恢复指引。agent 使用自己的工具阅读 mount 引入的外部
doctidex 目录树时，如果任务必须读取的文件或路径不存在，应先判断该路径是否属于
根 `index.md` 中声明的 mount：

- 若 mount 为 `not_prepared`，不要把目标误判为源中不存在；按 Mount Skill 指引
  运行 `doctidex-git mount prepare <mount-path>`，然后用原工具重试；
- 若 prepare 需要网络或凭据，按 Mount Skill 的诊断向用户说明需求；
- 若 mount 已为 `ready`，目标仍不存在，才将其作为真实的缺失路径继续调查；
- 若路径不属于任何声明的 mount，按普通仓库文件缺失处理。

prepare 完成后，agent 继续使用与浏览宿主仓库相同的原生工具读取
`<doctidex-root>/.doctidex/mounts/...`；恢复 CLI 不接管后续读取，也不得要求 agent
改用内部 checkout 或缓存路径。由于 mount path 必须被 `.gitignore`，默认遵守 Git
ignore 的全库搜索通常不会混入外部内容；需要搜索外部源时，agent 可以用自己的
工具定向探索明确的 mount path。

普通阅读不会重新解析 branch 或 tag。Read Skill 的成功结果是 agent 获得足够的
规则和方向来自主探索，而不是进入一套必须持续使用的读取会话。

### 5.4 `doctidex-git-mount`

用于列出、添加、移除、恢复和显式同步 Git mount。

添加或移除前，它检查操作目标是根 `index.md`、mount path 合法且无重叠、声明保持
完整源树语义、根 `.gitignore` 有效且 mount 路径下没有 tracked 内容，以及现有
文档 link 是否受影响。添加默认离线完成，只写入并校验声明，不访问远端、不解析
首次有效 commit，也不获取或恢复源；成功状态为 `not_prepared`。移除默认先报告
仍指向该 mount 的引用。

`mount prepare` 是从 `not_prepared` 恢复到 `ready` 的专门入口。它只让现有声明
指向的内容可读，不改变声明 revision；已有有效 commit 时继续使用该 commit，首次
准备时才按声明解析有效 commit。同步会先预览旧、新有效 commit 和受影响路径，只有
显式应用才切换。同步同一 URL 的多个 selector 时可以合并远端访问，但这一优化不
出现在普通输出中。

成功后 agent 看到 mount path、URL、声明 revision、已知时的有效 commit、是否可读，
以及根 `index.md` 是否发生变化。

### 5.5 `doctidex-git-maintain`

用于维护一个已经明确选定的 doctidex 根。

它在写入前展示目标根、任务范围、已有 Git 变化和不可写边界。维护时保留未知
frontmatter 与无关用户改动，遵守最近负责的 index、atomic、excludes、protected
和 mount 边界，按实际变化更新必要的 `index.md`；存在适用的 `log.md` 时更新其
负责范围内的重要变化。

少量、局部操作可以保留当前工作目录并传明确路径。若工作被拆分到某一个 doctidex
根且工作量较大、步骤较多，Skill 应推荐 agent 进入该根开展维护，使原生工具和省略
可选路径的 CLI 自然使用该根，减少重复参数；多根协调时仍保留明确的逐根路径。

内容修改、index 正文和 log 记录均由 agent 判断并撰写。CLI 可以报告待核对索引
候选、适用 log、文件变化和格式问题，但不得自动生成描述、摘要或变更记录，也不得
把候选直接定性为索引或 log 缺口。

成功后 agent 得到 changed files、index/log 跟进情况、校验结果和待用户审阅的 Git
diff。若目标位于 mount path，该 Skill 不直接写入，而是转交 Workspace Skill
打开源的独立维护根。

### 5.6 `doctidex-git-workspace`

用于维护挂载源，或协调一个任务涉及的多个 doctidex 根。

它先列出每个独立根、基准 commit、读写范围、依赖顺序和预期结果。对于挂载源，
它提供一个与当前只读挂载视图隔离的可写维护根；当前宿主仓库同时被引用时也使用
独立维护根，不切换、重置或混入用户当前工作目录。

每个根分别调用 Maintain 与 Validate。成功后 agent 得到逐根 diff、校验结果、
revision 影响以及待用户执行的 commit、push 或 selector 更新。未提交变化的维护根
会保留，除非用户明确处理；插件不会用清理来代替交付结果。

`maintenance scope` 和 `open` 由 cwd 选择宿主。`open` 返回的精确维护根路径同时
携带后续选择所需的用户上下文；agent 可以从任意 cwd 将它传给 `status`、`handoff`
或 `close`。在一个维护根内进行多步骤工作时，进入该维护根仍是推荐的简化方式。

### 5.7 `doctidex-git-validate`

用于只读检查目录树和插件公开状态。

默认离线检查 frontmatter、index/log 连续性、过滤条件、可解析 links、根级 mount
声明、mount path、不可嵌套解析和协议维护边界；同时独立检查根 `.gitignore` 的有效
规则、tracked 状态及其他插件运行前置条件。它区分“本地结构不符合”、“需要 agent
判断的语义候选”、“插件操作尚未就绪”、“远端未经验证”和“当前无法取得源”。只有
显式在线模式才访问远端或检查 selector 是否出现新 commit；在线检查本身也不执行
同步。`not_prepared` 是合法运行状态，不因物理内容尚未恢复而产生符合性失败。

底层 `check` CLI 必须分开返回：

- `protocol_structure`：CLI 可确定的协议结构检查，状态为 `pass` 或 `fail`；
- `semantic_review`：索引条目和重要变更等需要 agent 判断的候选，状态为 `clear` 或
  `required`；
- `plugin_readiness`：`.gitignore`、tracked mount 内容及 Git 工作现场等插件前置
  条件，状态为 `ready`、`blocked` 或 `not_applicable`。

`.gitignore` 不满足要求可以令 `plugin_readiness: blocked` 并阻止 mount 准备，但
不得令 `protocol_structure` 失败或被描述为 doctidex 协议错误。Validate Skill 使用
CLI 事实检查候选内容后，由 agent 给出最终的协议符合性判断。每条 finding 都包含
所属结果域、协议路径或文件、用户层说明和可执行动作。

### 5.8 `doctidex-git-review`

用于只读审阅单根或多根任务结果。

它结合 Git diff 与 doctidex 范围检查内容变化、index/log 跟进、过滤和保护边界、
是否穿透 mount 写入、mount 声明及 revision 影响，以及每个维护根是否仍有需要用户
处理的 Git 动作。

CLI 只通过 `changes` 和 `check` 提供确定性的 diff、范围及校验事实。内容是否准确、
描述是否充分、变更是否合理以及最终审阅结论由执行 Review Skill 的 agent 形成。

成功后 agent 得到按严重程度排列的 findings、逐根变化摘要和交付前检查清单。它
不修复文件、不恢复挂载、不提交或推送。

## 6. CLI surface

插件只暴露一个公共可执行文件 `doctidex-git`。所有命令默认提供适合人和 agent
阅读的简洁输出，并支持 `--json` 返回同等语义的结构化结果。写操作支持
`--dry-run`；需要联网的操作在计划中明确标识。该 CLI 可以提供依赖 doctidex 信息的
导航和路径辅助，但不以重复通用文件读取、目录遍历或全文搜索为目标，也不替代
shell、编辑器、搜索器或 agent 运行环境已有的文件工具。所有命令都必须遵守第 1.2
节的客观性原则和第 1.3 节的输出规模原则。

```text
doctidex-git context [PATH]
doctidex-git inspect [PATH]
doctidex-git resolve INTERNAL_PATH [--from LINK_DOCUMENT]
doctidex-git init [PATH] [--dry-run | --apply]

doctidex-git mount list
doctidex-git mount add --url URL (--commit SHA | --tag TAG | --branch BRANCH) \
  --mount-path INTERNAL_PATH [--dry-run | --apply]
doctidex-git mount remove MOUNT_PATH [--dry-run | --apply]
doctidex-git mount prepare [MOUNT_PATH]
doctidex-git mount sync [MOUNT_PATH] [--dry-run | --apply]

doctidex-git maintenance scope [PATH ...]
doctidex-git maintenance open MOUNT_PATH
doctidex-git maintenance status [MAINTENANCE_ROOT]
doctidex-git maintenance handoff [MAINTENANCE_ROOT]
doctidex-git maintenance close [MAINTENANCE_ROOT]

doctidex-git check [PATH] [--online]
doctidex-git changes [PATH]
```

可能返回集合的命令接受适用的 `--limit N`、`--depth N` 和 `--cursor TOKEN`；PATH
参数用于优先缩小范围。具体默认预算由实现文档固定，但不得取消分页和截断元数据。

`--apply` 是文档中的显式写入表达；交互式实现也可以在展示同等计划并得到当前调用
授权后执行。命令不得把“未传 `--dry-run`”解释为允许破坏性 Git 操作。

### 6.1 阅读辅助信息

`context` 输出 Git 工作目录、doctidex 根、入口 index 和当前模式（宿主读取、挂载
读取或独立维护）。

`inspect [PATH]` 输出可供 agent 判断阅读方向的客观结构信息，至少包括：

- 宿主 doctidex 根、PATH 的内部路径和本地或 mount 来源；
- PATH 是否属于宿主范围，以及命中的 excluded、atomic、protected 属性；属性按集合
  返回，不建模成互斥状态；
- 对宿主 included 内容，返回负责 `index.md` 和适用 `log.md`；对宿主 excluded 内容，
  返回排除它的 index 和条件，但负责 index/log 明确为 `none`；
- 对 mount 内容，返回宿主 mount 声明上下文，并在源可读时另行返回源根、源负责
  `index.md` 和源适用 `log.md`；不得把宿主 index/log 说成挂载内容的负责范围；
- 适用的过滤与维护边界；
- index 中已有 link 的标签、目标及文件顺序；
- 未发现机器可解析索引引用、需要 agent 核对的候选条目。

`inspect` 不按任务相关性排序、不生成推荐理由，也不摘要 index 或目标文件。agent
根据这些事实决定使用自己的工具继续读取或搜索哪些路径。link 和待核对候选过多时，
`inspect` 按负责 index 和目录折叠，并返回总数、当前页和继续展开入口。

`resolve INTERNAL_PATH [--from LINK_DOCUMENT]` 面向“这个 doctidex 路径实际指向
哪里”的判断。省略 `--from` 时使用 cwd 选中的链接根；传入时该参数必须是包含 link
的可访问文件，而不是要求 agent 另行指定链接根。命令至少输出：

- 原始输入、规范化后的内部路径、实际链接根、链接根种类和对应工作目录路径；
- 使用 `--from` 时的 link 来源文件；该参数只选择解析语义，不承诺验证文档中确实
  存在该 link；
- 路径是否跨入 mount，以及 mount path、来源和有效 commit；
- mount 的 `not_prepared`、`ready` 或受阻状态；
- `not_prepared` 时精确的 prepare 命令，`ready` 时可交给原生文件工具的路径。

这些命令可以解析 frontmatter、index 和 link 来生成结构化辅助信息，但不规定 agent
随后必须读取哪些文件、使用什么搜索工具或按什么顺序探索。agent 可以忽略辅助
信息、交叉验证结果或直接扩大范围。

### 6.2 mount 输出

`mount list` 和 `mount prepare` 的单项结果至少包含：

```text
Mount path:        /.doctidex/mounts/design
Source:            https://example.com/design.git
Declared revision: branch main
Effective commit:  4d6c2f...
Readable:           yes
```

尚未恢复时，`mount list` 显示 `State: not_prepared`、`Readable: no`，并直接给出
`doctidex-git mount prepare <mount-path>`；这是一种正常 lazy 状态，不是错误。
首次准备前允许显示 `Effective commit: not resolved`。`mount prepare` 成功后显示
`State: ready`、解析出的有效 commit 和 `Readable: yes`。

不得在此增加 projection 类型、缓存命中、内部 checkout 路径或锁状态。

`mount sync --dry-run` 还显示是否需要网络、旧/新有效 commit、受影响的逻辑路径和
仍可继续使用的旧结果。commit selector 不需要重新解析；branch 和 tag 只有在
`--apply` 后才切换。

### 6.3 maintenance 输出

`maintenance open` 至少返回：

- maintenance root 的可访问路径；
- 它对应的 mount path 和源 URL；
- 基准 commit 与目标 branch（如果存在）；
- 可写 doctidex 根和不可越过的边界；
- 下一步维护、校验和 handoff 命令。

`maintenance scope` 只计算涉及的 doctidex 根、基准 revision、读写边界和显式依赖
边，不决定任务顺序。`maintenance handoff` 输出 changed files、Git 状态和校验结果
等客观事实但不撰写交付摘要，也不提交。`maintenance close` 只关闭没有未提交或未
交付结果的上下文；存在变化时必须保留并给出下一步，不得自动丢弃。

## 7. 用户可见工作流

### 7.1 创建或接管目录树

用户请求：“把这个 Git 目录整理为 doctidex。”

1. Setup Skill 运行 `context` 和 `init --dry-run`，取得客观结构与待核对索引候选。
2. agent 看到将选用的根、需要创建或补全的 `index.md`、新增 excludes、根
   `.gitignore` 规则、待核对候选，以及“不会触网、不会提交”。
3. 写入获准后运行 `init --apply` 生成确定性结构，agent 自行撰写目录说明与索引
   正文，并判断已有自由文本是否已经覆盖候选条目。
4. 最后运行离线 `check`，分别确认协议结构、语义复核和插件就绪结果；现场结果是
   普通 Git 文件变化，没有要求用户理解的运行时目录。

完成后，agent 得到入口路径、变更文件和仍需人工决定的索引描述。已有内容和无关
Git 变化保持原样。

### 7.2 渐进读取和查询

用户请求：“找出 API 鉴权的设计依据。”

1. Read Skill 发现根并用入口或最近负责的 `index.md` 提供优先探索路径。
2. 需要结构化辅助时，agent 可以调用 `inspect` 获取负责 index/log、范围上下文、
   已有 link 和待核对索引候选，或调用 `resolve` 解释 link 与 mount 状态；若 link
   来自已挂载文档，可直接传该文档的可访问路径，不必离开宿主 cwd。这些调用是可选的。
3. agent 自主选择其原生搜索、目录浏览和文件读取工具。
4. 索引没有覆盖当前问题、线索不足或 agent 判断全局搜索更合适时，可以直接扩大
   搜索范围，不需要得到 Read Skill 或 CLI 的许可。
5. 阅读 mount 引入的外部 doctidex 目录树时，如果原生工具发现任务必须读取的路径
   不存在，agent 按 Read Skill 指引检查声明与 mount 状态；若为 `not_prepared`，
   调用 Mount 工作流或精确的 `mount prepare` 命令，不自动恢复所有 mount。
6. prepare 成功后，对应工作目录路径变为可读，agent 回到原有工具继续探索。
7. 挂载内容使用当前有效 commit，不触发 branch/tag 同步。

完成后，agent 保留对仓库文件的直接访问，同时获得引用内容的逻辑来源路径和必要
时的有效 commit，而不会看到 clone 或映射位置。

### 7.3 添加外部 Git 目录树

用户请求：“把 design 仓库的 main 分支挂到 design。”

1. Mount Skill 将简称规范化为
   `/.doctidex/mounts/design`，但在歧义时要求明确路径。
2. `mount add --dry-run` 检查根声明位置、必需 excludes、根 `.gitignore`、路径下
   是否已有 tracked 内容、路径冲突、revision 和完整源树语义；默认无需网络。
3. `mount add --apply` 只以结构化 YAML 修改根 `index.md`，不访问或恢复源。
4. `check` 验证声明和外部引用形式。

完成后，根 `index.md` 出现一条 mount 声明，mount 状态默认为 `not_prepared`；宿主
index、log 和 Git tracked diff 不会出现展开的源文件。此时无需访问该源，只有后续
任务确实需要读取时才执行 prepare。

### 7.4 Lazy 恢复与显式同步 mount

工作区重新打开、mount 尚未准备或此前呈现已清理时，保持 `not_prepared` 不属于
失败。agent 使用原生工具遇到任务必须读取但不存在的 mount 路径时，按 Read Skill
指引进入 Mount 工作流并运行 `mount prepare <mount-path>`。prepare 使用已有有效
commit 恢复相同读取结果；首次准备才解析声明 revision。恢复操作不更改声明或宿主
Git 状态。

用户请求“更新 design 挂载”时：

1. `mount sync --dry-run` 显式访问远端并展示旧、新 commit 和受影响路径。
2. agent 先说明内容可能变化的范围；用户授权后运行 `--apply`。
3. 其他仍引用旧 commit 的 mount 继续得到旧内容；解析到新 commit 的 mount 切换
   到新内容。
4. 同步完成后运行 link 和 mount 检查。

首次 prepare 失败时，mount 保持 `not_prepared`，插件报告恢复所需的网络、凭据或
revision 决策且不修改宿主。对已经 `ready` 的 mount 执行同步失败时，旧有效 commit
仍可读，插件报告“同步未完成”，而不是破坏当前挂载。

### 7.5 维护当前根

用户请求：“更新当前目录树的部署说明。”

1. Maintain Skill 展示根、候选文件、已有 Git 变化和 protected/excluded/mount
   边界。
2. agent 可以用 index 缩小范围，也可以使用原生工具自由搜索和读取现场；写入只
   发生在当前根允许的内容中。
   若该根内工作量较大或步骤较多，agent 可以先进入该根以简化后续命令参数。
3. agent 更新需要跟进的 index；已有适用 log 时记录重要变化。
4. `check` 与 `changes` 展示协议检查和最终 diff。

完成后，文件仍留在用户的当前 Git 工作区中等待审阅，不产生隐式提交。

### 7.6 维护挂载源

用户请求：“修正 design 挂载中的错误。”

1. 直接写 `/.doctidex/mounts/design/...` 会得到只读边界提示和
   `maintenance open` 下一步。
2. Workspace Skill 打开独立维护根，显示源、基准 commit、可写范围和维护路径。
3. Maintain Skill 从该源自己的 `index.md` 开始维护并独立校验；多步骤维护可进入
   该维护根执行，后续 handoff 仍显式传回维护根路径。
4. `maintenance handoff` 输出源根 diff、Git 状态和校验事实，agent 据此撰写交付
   摘要并判断需要向用户说明的 Git 动作。

宿主 mount 在整个过程中继续读取原有效 commit，用户当前工作目录也不被切分支、
重置或混入源修改。若源恰好就是当前宿主仓库，仍执行同样的隔离流程。

### 7.7 多根协同维护

用户请求同时修改源目录树及宿主对它的说明时：

1. `maintenance scope` 客观列出候选根、基准 revision、读写边界和显式依赖。
2. Workspace Skill 中的 agent 判断实际受影响根和维护顺序，再为每个外部源提供
   独立维护根；宿主留在当前可写根。
3. 每个根分别执行 Maintain、Validate 和 diff 审阅。
4. agent 汇总逐根结果，并明确哪些 commit/push 需要用户执行或授权。
5. 源取得新 commit 后，再预览并更新宿主 selector 或显式同步有效 revision，最后
   复查宿主引用。

该流程不是跨仓库原子事务。某一根失败时，已完成根的变化会被保留并单独报告，
不得回滚或覆盖用户结果来制造“全部成功”的表象。

### 7.8 离线工作

若声明 revision 的有效 commit 和所需对象已经可用，`mount prepare` 可以离线完成；
随后 agent 的原生文件工具、离线 `check` 和当前根维护都可在不访问远端的情况下
工作。

离线状态不等于不符合。输出应区分：

- 当前有效 commit 已验证且可读；
- 远端是否有新 commit 未验证；
- 首次读取所需对象本地不存在，因而需要联网或凭据。

## 8. Lazy mount 与可读性保证

mount 默认按需恢复。声明结构有效但尚未执行 prepare 时，`mount_path` 可以没有可
浏览的物理内容；该状态必须表达为 `not_prepared`，不得误报为源不存在、文件不
存在或内部失败。agent 使用原生工具发现任务必须读取的 mount 路径不存在时，按
Read Skill 中第 5.3 节的指引判断 mount 状态，并显式调用 Mount 工作流或
`mount prepare`。

prepare 成功后，插件必须在 agent 的工作环境中把符合协议的逻辑 `mount_path`
呈现为可由原生文件工具正常浏览和读取的路径。实现可以改变物理呈现方式，但必须
满足：

- shell、编辑器、搜索器和 agent 运行环境已有的文件工具可以直接访问
  `<doctidex-root>/.doctidex/mounts/...`；
- agent 不需要改用缓存路径、内部 checkout 或专用 CLI，也不需要选择符号链接或
  虚拟读取模式；
- 不公开 `unmaterialized`、`projection_failed` 或同类内部状态；
- 物理呈现方式变化不改变内部路径、链接根、mount 不可嵌套或只读边界；
- 恢复读取能力不修改宿主 tracked diff、Git index 或用户文件。

若内部实现使用虚拟 resolver 或其他非普通目录机制，插件与 agent 运行环境的集成
必须在原生文件工具层透明提供等价访问。不得把实现降级转化为“只能改用某个专用
读取命令”的用户限制。单纯无法建立某种物理映射不是用户错误。

只有 prepare 时发现外部源本身不可取得，才可以报告读取受阻，例如：缺少凭据、
网络不可用且本地没有所需对象、URL 不存在或 revision 不存在。诊断必须描述为
“外部目录树当前无法恢复”，不得要求用户处理 projection、worktree 或缓存。

## 9. 诊断与升级契约

每个非成功结果都必须回答五个问题：

1. 哪个用户操作未完成；
2. 哪个根、逻辑路径或 revision 受到影响；
3. 哪些结果已经完成并被安全保留；
4. agent 现在可以执行哪些动作；
5. 是否需要用户提供凭据、授权或决策。

面向人的默认格式为：

```text
Cannot continue: synchronize mount /.doctidex/mounts/design
Reason: the remote repository requires credentials
Still available: effective commit 4d6c2f remains readable
Changes made: none
Next actions:
1. Ask the user to provide access to https://example.com/design.git
2. Retry the explicit sync after access is available
Need from user: repository access
```

`--json` 使用稳定的用户语义字段：

```json
{
  "status": "blocked",
  "operation": "mount_sync",
  "root": "/workspace/docs",
  "affected": ["/.doctidex/mounts/design"],
  "changed": [],
  "result": "The current effective commit remains readable.",
  "findings": [
    {
      "severity": "error",
      "message": "The remote repository requires credentials.",
      "actions": ["Obtain repository access", "Retry explicit sync"]
    }
  ],
  "requires_user": "repository_access"
}
```

实现可以增加向后兼容的可选字段，但不得把内部缓存、锁或映射字段变成 agent 决策
所必需的信息。

### 9.1 常见失败与下一步

| 用户层情况 | 对当前任务的说明 | agent 可采取的动作 |
|---|---|---|
| mount 声明不符合协议 | 指向根 `index.md` 的字段和合法形式 | dry-run 修正声明，再运行 `check` |
| 远端需要凭据 | 首次读取或同步无法完成；已有有效 commit 仍可用 | 向用户请求访问权限，得到后重试 |
| 网络不可用 | 远端状态未经验证；本地有效内容不受影响 | 继续离线读取，或稍后显式同步 |
| revision 不存在 | 指定 selector 无法取得 | 请用户确认 commit、tag 或 branch |
| mount 尚未恢复 | 正常 lazy 状态，所需文件暂不可读 | 运行提示中的 `mount prepare <mount-path>` 后重试原读取 |
| mount 路径未被 Git ignore | 恢复内容可能进入 Git 状态或提交 | 在根 `.gitignore` 添加有效规则后重新检查 |
| mount 路径下已有 tracked 内容 | ignore 规则不能移除已有 index 条目 | 列出文件，请用户决定如何移出 Git index |
| 尝试写入 mount path | 宿主视图是只读入口 | 运行 `maintenance open <mount-path>` |
| protected 内容需要修改 | 当前根维护无权写入 | 缩小任务，或向用户请求明确决策 |
| 已有用户修改可能冲突 | 插件不会覆盖或清理 | 保留现场，列出冲突文件并请用户决定 |
| 多个 doctidex 根都可匹配 | 无法可靠确定操作范围 | 列出候选根，请 agent 或用户选定 |
| 移除 mount 后仍有引用 | 删除会留下无效外部 link | 先更新引用，或请用户确认保留该问题 |
| 维护结果尚未提交 | 结果已保留但未发布 | 展示 diff，向用户说明所需 Git 动作 |

### 9.2 必须直接向用户反馈的情况

agent 无法通过只读检查或安全重试解决以下情况时，必须停止相关写入并直接反馈：

- 需要新的远端凭据、网络权限或仓库访问授权；
- source URL、目标 revision、doctidex 根或维护分支存在实质歧义；
- 继续会覆盖、重置、清理或丢弃已有用户修改；
- 需要用户执行或授权 commit、push、merge、reset 等 Git 动作；
- protected 范围或跨根依赖要求改变原任务授权边界；
- 多根结果之间存在无法由当前任务安全决定的冲突。

反馈必须包含已保留的工作及其可访问位置。不得只输出“内部错误”后要求用户阅读
日志，也不得把多次盲目重试列为唯一动作。

## 10. 权限与安全规则

- 所有写操作先确定唯一 doctidex 根并展示计划；
- 所有可能触网的操作在运行前或 dry-run 中说明；
- 默认保留未知 YAML 字段、无关文件和用户已有 Git 变化；
- 每个受管理根的 `.gitignore` 必须有效忽略 `/.doctidex/mounts/`，该路径下不得有
  tracked 内容；
- 不通过挂载路径写源，不在 revision 只读视图中维护内容；
- 不自动 commit、push、reset、clean、切换用户当前分支或删除未提交结果；
- 凭据不得写入根 `index.md`、revision 状态、doctidex 文档或命令输出；
- 关闭维护上下文前确认结果已经干净或由用户明确处置；
- mount 准备、恢复和内部复用不得污染宿主 Git status；
- Read Skill、validate 和 review 不得隐式执行 mount prepare 或在线同步。

### 10.1 非公开实现能力边界

以下能力是兑现公开 surface 的实现要求，但不得进入普通 Skill 说明或 CLI 输出：

- 同一 Git source 的声明共享已经取得的 Git objects 和远端访问结果，避免按 mount
  重复 clone 或 fetch；
- 不同 revision 可以同时存在，解析到同一 commit 的声明可以安全复用同一只读
  revision 视图；
- mount 读取始终基于 commit 快照，包括源恰好是当前宿主仓库时，不得混入当前
  staged、unstaged 或 untracked 内容；
- 外部源维护使用与只读 revision 视图、其他任务和用户当前工作区隔离的可写上下文；
- 并发获取、复用、生命周期管理和映射降级由实现自行协调，不将锁或内部冲突转嫁
  给 agent；
- 文件系统无法直接表达安全映射或会形成环时，使用等价逻辑解析维持第 8 节的
  可读性保证。

这些要求只约束可观察结果和资源复用能力，不规定内部目录名称或布局。

## 11. Surface 验收标准

实现完成时，至少通过以下用户层场景验收：

1. agent 只阅读 Guide 与相关专项 Skill 即可理解当前任务所需的目录树概念、命令
   参数、默认行为、根选择、读写与触网影响、关键返回字段和失败动作，不需要猜测
   命令或查阅程序源码及实现文档。
2. agent 只阅读 Skills 即可理解目录树，并能用自己的文件工具完成自由浏览、搜索
   和读取；插件可以提供 doctidex 感知的导航、范围和路径辅助，但不将其变成文件
   访问网关。只有 lazy mount 恢复需要调用专门工作流或 `mount prepare`。
3. 同一 Git URL 的不同 revision 可以同时读取并共享已取得的 Git objects；解析到
   相同 commit 时可复用只读视图，但不向 agent 暴露复用机制。
4. 普通读取不会移动 branch/tag 的有效 commit；显式同步展示新旧 commit。
5. 每个受管理根的 `.gitignore` 都有效忽略 `/.doctidex/mounts/`，该路径下没有
   tracked 内容。
6. 任意合法 Git mount 都挂载完整源树，且只出现在根声明的
   `/.doctidex/mounts/...`。
7. mount namespace 不可嵌套，源中的相关 link 按起始根唯一 mount 表解析。
8. mount 声明默认保持 `not_prepared`；agent 遇到任务必须读取但不存在的 mount
   路径时，按 Read Skill 指引显式 prepare，而不会预先恢复所有 mount。
9. prepare 完成或 mount 的物理呈现方式变化后，agent 仍能用自己的文件工具从同一
   工作目录路径正常浏览和读取。
10. 维护挂载源会得到独立可写根，不影响只读挂载、当前用户工作区或其他 revision。
11. 多根任务分别报告每个根的 diff、校验、revision 影响和待办 Git 动作。
12. 离线、凭据缺失、revision 不存在、用户本地修改和协议错误均产生可执行诊断，
   且默认输出不包含内部实现约定。
13. 插件不自动提交、推送、重置、清理或丢弃任何用户结果。
14. 所有 CLI 在不配置或调用任何 AI 模型的情况下工作；`index.md` 正文、索引描述、
    `log.md` 记录、维护顺序和审阅结论均由 agent 生成或决定。
15. 所有列表型 CLI 默认限制结果规模，按目录提供确定性折叠和计数摘要，并通过
    limit、depth、PATH 和 cursor 支持逐步展开；任何默认调用都不会无界枚举路径。
16. 所有过滤条件按固定版本 `regex` 库的 VERSION1 方言、路径规范化和 search 规则
    得到一致结果；
    非法或超出基线的 pattern 产生可定位、可执行且有界的诊断。
17. `check` 分别报告协议结构、语义复核和插件就绪状态；语义候选由 agent 判断，
    `.gitignore` 等插件要求不会被误报为 doctidex 协议错误。

这些验收项约束的是插件公开行为。满足它们所采用的 Git object 复用、隔离 checkout、
worktree、锁和逻辑映射方案属于后续内部设计，不构成 agent surface 契约。
