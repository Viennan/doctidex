# 领域模型

本文定义 `doctidex-git` 用来连接目录树语义、Git revision 和用户工作流的语言无关
模型。每个属性标明其含义和可见性。精确 CLI 字段见[结果契约](interfaces/cli-schema.md)。

## 1. 可见性标记

| 标记 | 含义 |
|---|---|
| Public | 用户、agent 或程序集成完成任务需要理解。 |
| Public conditionally | 只在相关工作流出现，例如 maintenance root。 |
| Internal | 支撑公开语义，但不能成为 Skill 或普通 CLI 的前置知识。 |

## 2. Directory Tree Context

### 2.1 Doctidex Root

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| root path | Public | 根的文件系统路径；其直接 `index.md` 声明 `doctidex.root: true`。 |
| root index | Public | 默认导航入口、根级过滤配置和唯一 mount declaration table。 |
| containing Git worktree | Public conditionally | 提供 status、revision 和协作现场；可以大于 root，也可以包含多个 roots。 |
| child indexes | Public | 把索引责任分层委托给子目录；不改变 root identity。 |
| applicable logs | Public | 可选的最近变更背景，不是每次读取的强制入口。 |
| filters | Public | atomic、excluded、protected 条件及由它们形成的索引/维护边界。 |

### 2.2 Command Context

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| cwd | Public | 默认上下文来源。它减少常见调用参数，不构成文件访问限制。 |
| selected root | Public | 当前命令用于解释 root-owned state 和 mount namespace 的根。 |
| operation | Public | 决定参数、结果 schema、副作用和退出行为。 |
| operation target | Public | 命令实际检查或修改的 PATH/MOUNT_PATH；可以与选择根的输入不同。 |
| link document | Public conditionally | `resolve --from` 的来源文件；只提供 link 语义，不要求扫描文档。 |
| maintenance selector | Public conditionally | open 返回的 exact maintenance root；可恢复其所属宿主上下文。 |

选根必须确定。嵌套根没有被 cwd 或 exact path 明确选择时返回 `root_ambiguous`，而不是
自动采用最近祖先。

### 2.3 Path Context

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| host root | Public | 计算当前上下文的 doctidex 根。source view 中可为 mounted source root。 |
| path | Public | 被检查的文件系统路径，可以尚不存在。 |
| internal path | Public | path 相对于 host root 的 `/` 开头逻辑路径，不是 OS absolute path。 |
| source | Public | `local` 或 `mount`。 |
| host scope | Public | `included` 或 `excluded`；mount 在宿主语义中始终 excluded。 |
| attributes | Public | atomic、excluded、protected、mount 的集合；不是互斥枚举。 |
| responsible index | Public | 对 included local path 负责的最近 index；其他情况为空。 |
| applicable log | Public | 路径范围内最近可用 log；不存在时为空。 |
| boundary index | Public | 建立 excluded 边界的 index。 |
| boundary condition | Public | 命中的 path/regex 条件。 |
| mount path | Public conditionally | path 命中的完整 mount declaration root。 |

## 3. Link Resolution

### 3.1 Internal Path

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| raw input | Public | 调用者提供的 `/` 开头路径部分，不包含 anchor。 |
| normalized path | Public | 折叠空段、`.`、`..` 和重复 mount namespace 后的路径。 |
| link root | Public | 绝对内部 link 的实际基准，可以是 host root 或 mounted source root。 |
| link root kind | Public | `host_root` 或 `mounted_source`，用于解释 root 与 link root 可能不同。 |
| working path | Public | 原生文件工具可以尝试访问的文件系统路径。 |
| relevant mount | Public conditionally | 路径命中或来源依赖的 mount state。 |
| root relation | Public conditionally | 涉及 mount 时，对 source 是否可确认为当前根仓库及 commit 是否相同的保守判断。 |
| maintenance reuse | Public conditionally | 若随后需要写入，可否复用已有 scope 的有界建议；不改变 working path。 |

路径规范化不得越过 link root。一次从 host 开始的 mount namespace 不嵌套：mounted
source 中再次出现 `/.doctidex/mounts/...` 时回到原 host namespace。

## 4. Git Mount

### 4.1 Mount Declaration

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| type | Public | 插件处理的值为 `git`；其他扩展不由本插件解释。 |
| source URL | Public | 完整 Git repository URL 或本地路径；输出不得泄漏 embedded credentials。 |
| mount path | Public | `/.doctidex/mounts` 的规范化严格后代；同根 declarations 不得重叠。 |
| revision selector | Public | exactly one commit、tag 或 branch。 |
| source tree scope | Public | URL checkout root 必须是完整 doctidex root；不支持 source subtree selector。 |

### 4.2 Revision Selector

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| kind | Public | `commit`、`tag` 或 `branch`。 |
| value | Public | declaration 中的非空原始值。 |

selector 表达用户意图，不等于已读取对象，也不证明远端当前可解析。

### 4.3 Mount Runtime State

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| declared revision | Public | 当前 declaration selector。 |
| effective commit | Public | 当前读取的不可变 Git commit；首次 prepare 前可以未知。 |
| state | Public | `not_prepared` 或 `ready`。 |
| readable | Public | 逻辑 mount path 当前是否可由原生工具访问。 |
| next action | Public | 未准备时精确的 prepare 动作，ready 时为空。 |
| source identity | Internal | 用于复用同源数据；不能替代 public URL。 |
| revision snapshot | Internal | effective commit 对应的只读源视图。 |
| host presentation | Internal | 把 snapshot 映射到逻辑 mount path 的机制。 |
| persisted selection | Internal | 关联 declaration 与 effective commit 的运行状态。 |

`not_prepared` 是正常 lazy 状态，不代表 source 或目标文件不存在。`ready` 只说明当前
effective commit 可读，不说明 branch/tag 已与远端同步。

### 4.4 Root Relation

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| source | Public conditionally | `same_repository` 表示可可靠确认 source 对应当前 checkout root；否则为 `unknown`，不作否定断言。 |
| revision | Public conditionally | source 相同时为 `same_commit`、`different_commit` 或 `unknown`；source 未确认时固定为 `unknown`。 |
| evidence | Internal | 本地 checkout、已配置 source 地址和 Git 元数据；不在普通结果或 Skills 中展开。 |

相同 commit 不能单独证明 source 相同。当前 doctidex 根不是 Git checkout root 时不得把
同仓库 URL 当作根自引用。判断不联网，不承诺识别所有等价 URL、镜像或 fork；未知关系
保持普通 mount 行为。

## 5. Maintenance

### 5.1 Maintenance Scope Item

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| kind | Public | `host_root` 或 `mounted_source`。 |
| identity | Public | host root path 或 exact mount path；用于在本次返回中去重观察对象。 |
| base commit | Public | host HEAD 或 mounted source effective commit；可以未知。 |
| declared revision | Public conditionally | mounted source 的 commit、tag 或 branch selector。 |
| target branch | Public conditionally | host 当前 symbolic branch 或 mounted source 的 branch selector；detached、未知、tag/commit selector 时为 null。 |
| read path | Public conditionally | mounted source 在 host 中的只读入口。 |
| write path/action | Public | host 直接写路径，或 mounted source 的 open 动作。 |
| root relation | Public conditionally | mounted item 与当前 host root 的 source/revision 关系。 |
| maintenance reuse | Public | 可复用 host/maintenance scope，或没有唯一兼容 scope 的原因。 |

scope item 是本次命令对 host root 或 mounted source 的观察，不是分配状态。
item 可以是 agent 首次观察的对象，也可以已在现有计划中；返回结构不区分这两种
情况。scope 按 host 和 exact mount 分类去重，不创建或覆盖 agent 的工作计划。

agent 根据每次返回的当前事实，把同 source、同 base commit 且写入与交付目标兼容的
items 纳入同一选定写入范围。新目标或现场变化时可以重新运行 scope 并复核这个决定。
scope 会排除已知 branch 冲突，但不替 agent 完成权限与完整交付意图判断；它不打开写入
环境，也不形成跨范围事务。

### 5.2 Selected Write Scope

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| selected root | Public | agent 实际执行维护的 host root 或 maintenance root。 |
| covered items | Public in workflow | agent 已决定在该根处理的一个或多个兼容 scope items；CLI 不持久化该集合。 |
| write boundary | Public | 所有写入必须位于 selected root 下；mount read path 不得成为写入入口。 |
| maintenance basis | Public | 被覆盖 items 共享的 source/base commit；不同或未确认基准不得合并。 |
| result boundary | Public | 以 selected root 产生的 index/log 决策、Git diff、校验和交付动作。 |

一旦进入选定范围执行，原生工具可以自由浏览该根，但不得沿其 mount 将其他源
直接纳入写入边界。遇到这类目标时，agent 将它作为新的 scope 观察对象，再决定复用
已有范围还是打开独立范围。

### 5.3 Maintenance Context

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| maintenance root | Public | 独立、可写 source root；后续命令应原样传回。 |
| owning host root | Public indirectly | 由 exact maintenance root 恢复；正常输出无需解释登记机制。 |
| source/mount path | Public | 说明结果来自哪个 host mount。 |
| base commit | Public | open 时的 effective commit，作为 diff 和交付基准。 |
| target branch | Public conditionally | branch selector 的交付提示；不表示已 checkout 该 branch。 |
| writable boundary | Public | 允许 source 修改的根。host mount 保持 read-only。 |
| state | Public | `ready` 或 `has_changes`，由当前 Git status 得出。 |
| changes | Public | Git porcelain entries，不包含 line-level diff。 |
| lifecycle identifier | Internal | 区分并发或重复 open 的 context。 |
| owner registration | Internal | 支持从任意 cwd 使用 exact maintenance root。 |

### 5.4 Maintenance Reuse

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| status | Public | `recommended`、`selection_required` 或 `not_available`。 |
| scope kind | Public conditionally | recommended 时为建议根类型；selection required 时为 `maintenance_root`；not available 时为 null。 |
| write path | Public conditionally | 唯一建议的可写文件系统根；必须按该 scope 自身边界使用。 |
| target branch | Public conditionally | 唯一建议根的 branch 提示；没有唯一建议或无法识别时为 null。 |
| candidate count | Public | 当前已知兼容 scope 数量；不枚举大量内部路径。 |
| reason | Public | 稳定原因枚举，解释当前根复用、已有同 commit scope、多候选或不可复用。 |

当 item 与候选的 target branch 都已知且不同，候选不进入复用建议；任一侧为 null 时，
工具保留候选，由 agent 根据任务交付意图判断。`recommended` 不替 agent 判断任务权限；
`selection_required` 要求先查看已有 maintenance status。`not_available` 表示当前没有
已知兼容写入入口，不表示 mount 不可读。

## 6. Validation and Result

### 6.1 Validation Domains

| 对象 | 属性/值 | 含义 |
|---|---|---|
| protocol structure | `pass` / `fail` | 可由明确规则确定的协议结构。 |
| semantic review | `clear` / `required` | 是否有必须由 agent 阅读判断的候选。 |
| plugin readiness | `ready` / `blocked` / `not_applicable` | Git mount 操作前置是否满足。 |

三个域相互独立。semantic required 不是结构错误，plugin blocked 也不是协议失败。

### 6.2 Result Envelope

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| status | Public | `ok`、`warning` 或 `blocked`，只表达本次操作级结果。 |
| operation | Public | 稳定 schema discriminator。 |
| root | Public conditionally | 当前命令选择的 root。 |
| result | Public | 已完成或已保留结果的简短说明。 |
| changed | Public conditionally | operation-specific；可能是 path list 或 commit comparison boolean。 |
| findings | Public | 客观问题或 blocked 原因。 |
| semantic candidates | Public | 需要 agent 判断的提示，不是 confirmed findings。 |
| next actions | Public | 非 blocked 结果的建议步骤。 |
| affected | Public conditionally | blocked 操作受影响对象。 |
| requires user | Public conditionally | 所需用户输入或授权类别。 |
| collection | Public conditionally | 每个有界列表的计数、分组和 continuation。 |
| diagnostic details | Public conditionally | 仅有限诊断 ID 或安全计数；不能泄漏内部布局。 |

### 6.3 Finding

| 属性 | 含义与约束 |
|---|---|
| domain | protocol、semantic 或 readiness；通用 blocked finding 可省略。 |
| severity | 当前为 `error` 或 `info`。 |
| code | 稳定机器分支标识。 |
| message | 用户层原因，不能依赖内部术语。 |
| actions | 有序、可执行的下一步。 |
| path/index | 适用时定位文件、逻辑路径或负责 index。 |

### 6.4 Collection

| 属性 | 含义与约束 |
|---|---|
| total | 预算前项目数。 |
| returned | 当前页项目数。 |
| collapsed directories | 当前页结构分组数量。 |
| groups | 按路径父目录得到的客观计数。 |
| truncated | 是否存在未返回项目。 |
| next cursor | opaque continuation token；无下一页时为空。 |

collection summary 只由结构和计数产生，不包含 AI 生成的内容摘要。
