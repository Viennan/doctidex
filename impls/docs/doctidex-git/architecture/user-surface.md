# User Surface

本文从使用者角度定义 `doctidex-git` 解决的问题和公开心智模型。命令语法见
[CLI 用户接口](interfaces/cli.md)，具体场景见[用户工作流](workflows.md)。

## 1. 需要解决的问题

Git 能保存文件和历史，但不会解释一个目录树如何被渐进阅读、哪些 index 负责某段
内容、外部目录树当前读取哪个 revision，或跨仓库修改应如何隔离。doctidex 提供目录
树语义；`doctidex-git` 补充 Git 环境中的可操作能力。

| 场景问题 | 不加设计约束时的风险 | `doctidex-git` 提供的 surface |
|---|---|---|
| 接管已有 Git 目录 | agent 可能覆盖正文、遗漏根标记或把运行时内容纳入 Git | 可预览、最小化的 `init` 工作流。 |
| 从大目录树定位内容 | 强制专用 reader 会损失成熟文件工具的能力，完全无引导又会重复搜索 | index/log/path context 辅助，原生工具仍可自由读取。 |
| 引用外部 Git 目录树 | 每个引用各自 clone，revision 漂移，逻辑路径与物理路径混淆 | 根级 mount 声明、lazy prepare、明确 effective commit。 |
| 读取未恢复的 mount | 文件不存在容易被误判为源内容缺失 | `not_prepared` 状态和精确 prepare 动作。 |
| 跟随 branch/tag 更新 | 普通阅读若自动更新会破坏可重复性 | 读取固定 effective commit，只有显式 sync 才切换。 |
| 修改挂载源 | 直接改只读呈现会污染宿主或影响其他引用 | 与宿主读取视图隔离的 maintenance root。 |
| 同时修改多个根 | 把多个仓库当成一次写入会隐藏独立 diff 和交付动作 | scope 拆分、逐根验证和独立 handoff。 |
| 自动检查目录树 | 结构错误、内容判断和插件前置容易被混成一个“失败” | protocol、semantic、readiness 三个结果域。 |
| CLI 输出供 agent/程序消费 | 无界路径枚举会挤占上下文，模糊错误无法决定下一步 | 确定性 JSON、有界 collection、可行动 finding。 |

## 2. 使用者与接口模式

### 2.1 人

人通常通过 agent 间接使用，也可以直接运行 CLI。人负责提供源、revision、授权和
Git 交付决定；CLI 不替人 commit、push、merge、清理或处理凭据。

### 2.2 Agent

agent 先通过 foundational Skill 建立共享术语，再进入任务对应的专项 Skill。它使用
CLI 获取 doctidex 客观事实，并继续使用自身文件、搜索、编辑和 Git 工具完成内容
阅读、语义判断和实际维护。

### 2.3 程序

程序以 CLI `--json` 为当前稳定集成面，按 `operation` 选择 schema，按 `status`、
结果域、finding code 和 collection 驱动状态机。Python 包内对象目前不是稳定公共
库 API；程序集成模式见[程序集成](interfaces/programmatic-integration.md)。

## 3. 核心心智模型

### 3.1 doctidex 根是操作范围

每次操作选择一个明确的 doctidex 根。根 `index.md` 是默认入口和唯一 mount 表；Git
仓库只是协作载体。一个仓库可以包含多个根，根也不必等于 Git worktree 根。命中多个
根时，插件返回歧义而不猜测。

### 3.2 doctidex 是导航层，不是访问网关

index、log、link 和过滤配置帮助缩小搜索并理解范围，但不会阻止普通文件访问。用户
仍可以直接读取 excluded、protected、atomic 或 mount 内容来理解现场；这些属性约束
的是索引责任和维护权限，而不是读取工具。

### 3.3 cwd 是默认上下文，不是强制根参数

常见单根工作直接从该根运行命令，省去重复参数。短暂从宿主浏览挂载内容时，可以
保留 cwd 并传入目标文件或 link 来源。较大、多步骤的单根维护可以进入对应根以简化
后续命令。不存在要求所有命令都显式传一个抽象 `--root` 的设计。

### 3.4 mount 是只读入口，source root 是维护入口

宿主通过 `/.doctidex/mounts/...` 读取完整外部 doctidex 根。这个逻辑入口属于宿主的
excluded 范围，不在宿主 index/log/维护责任内。需要修改时，用户打开独立 maintenance
root，并从 source 自己的 index、过滤边界和 Git diff 开展工作。

### 3.5 声明 revision 与 effective commit 分离

commit、tag 或 branch 表达用户声明；effective commit 表达当前实际读取快照。prepare
恢复已有快照，普通读取不会追踪远端移动。sync 明确比较 old/new 并在 apply 后切换，
从而兼顾可重复读取和显式更新。

### 3.6 多根任务产生多个结果

宿主和每个 mounted source 都有自己的基准 commit、写入边界、diff、验证与交付动作。
它们可以被一个 agent 协调，但不是原子事务，也不能由一个根的成功掩盖另一个根的
失败。

## 4. 公开接口

| 接口 | 主要使用者 | 解决的问题 | 可观察结果 |
|---|---|---|---|
| Skills | agent | 建立心智模型、命令契约和任务流程 | agent 获得足以独立完成工作的指引。 |
| 人读 CLI | 人、agent | 快速确认根、mount、状态和动作 | 有界的状态、结果与下一步。 |
| JSON CLI | agent、程序 | 稳定分支处理和自动组合 | 按 operation 区分的结构化 schema。 |
| 逻辑 mount path | 人、agent、文件工具 | 透明读取外部目录树 | prepare 后可由原生工具正常访问。 |
| maintenance root | 人、agent、Git 工具 | 隔离修改 mounted source | 独立可写目录、基准 commit 和 handoff。 |

CLI 是确定性、非 AI 的事实工具。目录说明、index 正文、log 记录、任务优先级和审阅
结论由 agent 或人形成。

## 5. 公开与内部信息边界

### 5.1 必须公开

- 选中的根、内部路径、link root、工作路径和范围属性；
- mount path、清理后的 source、声明 revision、effective commit 和可读状态；
- maintenance root、基准 commit、可写边界和目标 branch 提示；
- 操作是否预览、写文件或可能联网；
- Git changes、三个验证域、finding、已保留结果和下一步；
- 需要用户提供的授权、凭据、revision 或 Git 动作。

### 5.2 默认隐藏

- source/cache/state 的键和物理布局；
- clone、对象库、revision checkout、映射和锁的具体技术；
- 内部 schema 迁移、引用计数和垃圾回收；
- 调试堆栈和仅实现者可理解的路径。

维护根的可访问路径是完成任务所必需的公开信息；它不意味着用户需要管理该路径背后
的存储结构。未预期错误可以公开诊断 ID，但不能要求普通用户阅读实现源码。

## 6. 非目标

- 不修改 doctidex 协议或规定内容分类体系。
- 不把 Git 仓库强制等同于 doctidex 根。
- 不实现通用文件 reader、搜索器、编辑器或 Git porcelain 替代品。
- 不自动生成需要语义判断的 index/log 内容。
- 不自动 commit、push、merge、reset、clean 或删除用户结果。
- 不承诺多个根的跨仓库原子事务。
- 不把某一种文件系统呈现或缓存布局固化为用户契约。

## 7. Surface 验收

一个工作流只有在以下条件同时满足时才算完成：用户无需读源码即可理解参数；正常
结果说明获得了什么；失败说明什么未完成、什么已保留和下一步；可读 mount 最终可由
原生工具访问；主观内容仍由 agent 判断；默认输出不会无界占用上下文。
