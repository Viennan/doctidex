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

## 5. Maintenance

### 5.1 Maintenance Scope Item

| 属性 | 可见性 | 含义与约束 |
|---|---|---|
| kind | Public | `host_root` 或 `mounted_source`。 |
| identity | Public | host root path 或 exact mount path；用于去重独立结果。 |
| base commit | Public | host HEAD 或 mounted source effective commit；可以未知。 |
| read path | Public conditionally | mounted source 在 host 中的只读入口。 |
| write path/action | Public | host 直接写路径，或 mounted source 的 open 动作。 |

scope 只分类和去重，不打开写入环境、不决定任务顺序，也不形成跨根事务。

### 5.2 Maintenance Context

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
