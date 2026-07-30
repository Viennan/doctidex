# 需求 0002：根自引用场景的用户提示

| 属性 | 值 |
|---|---|
| ID | `DXG-REQ-0002` |
| 状态 | `approved` |
| 日期 | 2026-07-28 |
| 来源 | 用户在当前会话中提出，并在核对现有行为后收敛范围 |
| 影响范围 | doctidex-git Read、Maintain、Workspace Skills，CLI 关系提示与 Python 实现 |
| 协议关系 | 非规范性实现需求；不改变 [`doctidex` 协议](/spec/overview.md)规定的 mount 路径、排除和维护边界 |

本文要求 `doctidex-git` 在根自引用及相近场景出现时，为 agent 提供足以选择正确读取
和维护入口的提示。它补充现有 user surface，不建立新的维护模型，也不要求 agent 理解
source cache、Git worktree 或仓库身份判定等内部机制。

本文是需求历史，不是当前接口事实。当前实际行为以
[Architecture](../doctidex-git/architecture/index.md)、[Python Details](../doctidex-git/details/python/index.md)和已发布
Skills 为准。

## 1. 需求来源摘要

用户希望 Read、Workspace、Maintain Skills 及相关 CLI 结果覆盖以下容易误判的情况：

- 当前根通过自己的 mount 声明再次引用同一 Git 仓库；
- mount 的 revision 可能与当前根 HEAD 相同，也可能不同；
- agent 可能把只读 mount 入口误认为当前根，或者为了维护当前根而不必要地打开 mount
  workspace。

在对现有 surface 和实现进行核对后，用户进一步明确：需求的重点是在这些情况出现的
位置增加简要而明确的提示，不要求重构代码、仓库身份模型或整体维护架构。需求描述
无需逐字保留最初表述，应以这一收敛后的意图为准。

## 2. 问题与目标场景

### 2.1 从 mount 读取当前仓库的另一个视图

宿主根的 mount 可以指向与宿主当前 Git 仓库相同的源。即使 mount 的 effective commit
恰好等于当前根 HEAD，两条路径的用户语义仍不同：

- 当前根路径是用户已经打开的 Git 工作现场，可能包含未提交变化；
- `/.doctidex/mounts/...` 是该 mount 的只读读取入口，展示它自己的 effective commit。

如果 agent 因“同仓库”或“同 commit”把 resolve 结果改写为当前根路径，就可能读到不
属于 mount 快照的工作区变化。revision 不同时，这种路径折叠还会直接读取错误版本。

### 2.2 直接维护当前根

当任务明确要修改当前 doctidex 根时，该根本身就是写入现场。agent 应在根目录或其中
的文件上使用 Maintain 工作流，不需要先把当前仓库声明成 mount，也不需要运行
`maintenance open` 绕到 `/.doctidex/mounts/...` 下再建立工作区。

当前工具已经通过 `maintenance scope` 的 `kind: host_root` 与 `write_path` 表达这一
事实。需求只要求 Skills 把该用法讲清楚，不新增“为当前根执行 maintenance open”的
命令分支，也不把 host root 改称 maintenance root。

### 2.3 合并同 revision 的维护范围

mount path 始终只用于读取，但“从 mount 发现待修改内容”不等于“必须为该 mount 新开
维护根”。agent 应先比较 source 关系与维护基准：

1. 同一 Git source、相同 effective commit 的变更应尽量合并到同一个 maintenance
   scope，避免对同一份基准建立相互独立、可能产生冲突结果的写入现场；
2. 自引用 mount 的 effective commit 等于当前根 HEAD 时，当前 `host_root` 已经是可复用
   的写入 scope，agent 应优先在当前根完成这些变更，无需调用 `maintenance open`；
3. 已经存在同一 source、同一 effective commit 的 mounted-source maintenance root 时，
   后续兼容变更应优先复用它；
4. effective commit 不同、source 关系无法确认、写入权限或交付目标不兼容，或者用户明确
   要求隔离时，才为 mount 保留独立维护 scope。

“尽量合并”不改变 mount 的只读路径，也不表示可以把 mount 映射为当前根。它只影响
agent 对写入现场的选择。合并后的变更使用所选 scope 自己的 Git 状态、diff、校验和
交付流程。

## 3. 用户心智模型

| agent 的目标 | 应使用的入口 | 不应采取的动作 |
|---|---|---|
| 读取 link 命中的自引用 mount | 继续使用 resolve 返回的 mount 下 `working_path` | 因仓库或 commit 相同而自行替换成当前根路径 |
| 维护当前打开的 doctidex 根 | 直接维护 `host_root` item 的 `write_path` | 为了获得写路径而先创建自引用 mount 或调用 `maintenance open` |
| 维护与已有 scope 相同 source、相同 commit 的内容 | 把兼容变更合并到已有 `host_root` 或 `maintenance_root` | 仅因从另一个 mount 进入就重复打开工作区 |
| 维护没有兼容 scope 的 mount revision | 对精确 `MOUNT_PATH` 执行 `maintenance open`，写入返回的独立根 | 写入宿主 mount path，或把不同 commit 混入同一 scope |

根自引用只是一种需要额外解释的 source 关系，不改变 mount 的只读性、effective commit
生命周期或各 maintenance scope 的写入边界。

## 4. 已接受要求

### 4.1 Skills 提示

1. `doctidex-git-read` 必须简要说明：mount 指回当前仓库时，无论 revision 是否与当前
   HEAD 相同，访问路径仍位于宿主 `/.doctidex/mounts/...` 下并保持只读。
2. `doctidex-git-maintain` 必须明确：维护当前选中的 doctidex 根时直接使用该根；
   `maintenance_root` 术语继续表示 `maintenance open` 为 mounted source 返回的独立根。
3. `doctidex-git-workspace` 必须说明如何区分 `maintenance scope` 返回的 `host_root` 与
   `mounted_source`，并引导 agent 将同一 source、相同 effective commit 且写入与交付
   目标兼容的变更尽量合并到同一 scope。自引用 mount 与当前根 HEAD 相同时，优先复用
   `host_root`，无需额外打开 mounted-source maintenance root。
4. 若共享心智模型需要一句统一规则，可同步更新 `doctidex-git-guide`；专项 Skills 不得
   大量复制相同说明。
5. 提示只描述用户可见的路径、读写边界、revision 关系和下一步动作，不暴露 source
   cache、worktree 布局或仓库比较算法。

### 4.2 `resolve` 的关系提示

1. `resolve` 的路径行为保持不变：涉及 mount 时，`working_path` 仍是宿主可访问的 mount
   路径；不得因自引用而折叠到当前可写根。
2. 当工具能够可靠确认相关 mount 的 source 与当前命令根属于同一 Git 仓库时，结果应
   增加稳定、结构化且规模有界的关系提示。提示至少表达：
   - 这是当前根的 source 自引用；
   - 返回路径仍是只读 mount 入口；
   - mount effective commit 是否与当前根 HEAD 相同；
   - 如需修改且 commit 相同，优先把变更合并到当前根 scope；不同时再进入独立的
     mounted-source 维护流程。
3. 相同 commit 不能单独作为“同一仓库”的判据，revision 不同也不能单独排除自引用。
4. 无法可靠判定仓库关系时，工具必须表达未知或不提供肯定标记，不能猜测。未知状态
   不影响 resolve 的路径、可读性或既有后续动作。

精确字段名和枚举值由 Architecture 的 CLI schema 确定。实现可以利用操作时已经可得的
本地 Git 信息，但本需求不要求联网验证仓库身份或建立通用的远程 URL 等价系统。

### 4.3 Maintenance 工具的关系提示

1. 当前根维护继续由 `maintenance scope` 的 `host_root` item 与 `write_path` 表达；该
   结构已经足以让 agent 直接开始维护，不要求增加新的 open 生命周期。
2. `maintenance scope` 的结果应为 agent 判断可合并项提供足够的 source 关系、base
   commit、可复用写入入口和建议动作；工具可以分组或标注，但不代替 agent 判断写入与
   交付目标是否兼容。
3. 对自引用 mount，当 source 与当前根相同且 base commit 等于当前根 HEAD 时，建议动作
   必须优先指向当前根 `write_path`，而不是无条件建议 `maintenance open`。
4. 没有兼容 scope 时，`maintenance open` 的行为继续与普通 mounted source 相同：返回
   独立 `maintenance_root`、`writable_root`、base commit 和 mount 边界。
5. 当工具能够可靠确认 source 关系时，`maintenance open` 结果应增加与 resolve 一致的
   结构化关系提示，并指出是否已有可复用的同 revision scope。若 agent 已明确选择隔离
   或不存在兼容 scope，返回的仍是 mount source 的独立写入现场。
6. 无法确认关系时，open 仍按普通 mounted source 完成；不得因关系未知而阻断维护，
   也不得猜测性地合并到当前宿主根。
7. `maintenance status`、`handoff` 和 `close` 的选择方式及生命周期保持不变。只有这些
   结果确实需要帮助 agent 保持同一关系判断时，才可复用该提示；不得为此扩展成新的
   状态系统。

## 5. 设计约束与非目标

- 不改变 doctidex 协议或 mount namespace 语义。
- 不把自引用 mount 重定向、符号链接或别名化为当前可写根。
- 不为当前根新增 `maintenance open` 参数形式、context 或 close 生命周期。
- 不把仅有相同 commit、但 source 关系不明或交付目标冲突的任务强行合并。
- 不改变实际打开的 mounted-source worktree 的 base commit、handoff 或交付模型。
- 不要求完整解决所有 Git remote URL、镜像、fork、重写历史或本地路径的仓库等价问题。
- 不使用 AI 判断仓库关系；提示必须来自确定性的客观信息。
- 不因提示字段缺失或关系未知而破坏既有命令兼容性。

## 6. 落实结果

| 层面 | 已落实结果 |
|---|---|
| Architecture | 已补充自引用、同 revision scope 复用工作流，以及 `root_relation`、`maintenance_reuse` 的完整公共 schema。 |
| Published Skills | Guide 定义共享术语；Read、Maintain、Workspace 分别说明只读路径、当前根直写和 scope 复用决策。 |
| Python 实现 | `git.relations` 保守判断本地关系并排除已知 branch 冲突；resolve/scope/open 返回同一关系 object，路径选择和 maintenance 生命周期保持不变。 |
| 测试 | 已覆盖同/different commit 自引用、branch 交付冲突、SCP/local 地址歧义、nested root unknown、已有同 source/base commit scope 复用和普通 mount 回归。 |
| Details | [Repository Relation](../doctidex-git/details/python/repository-relations.md)与[Maintenance](../doctidex-git/details/python/maintenance.md)记录模块、字段生产和限制。 |

相关当前设计入口包括 [User Surface](../doctidex-git/architecture/user-surface.md)、
[工作流](../doctidex-git/architecture/workflows.md)、[领域模型](../doctidex-git/architecture/domain-model.md)、
[CLI 结果契约](../doctidex-git/architecture/interfaces/cli-schema.md)和
[Skill 系统](../doctidex-git/architecture/skill-system.md)。这些页面现已作为当前行为的权威说明。

## 7. 验收标准

1. 当前根维护的 Skill 引导直接使用当前根，不要求创建或打开自引用 mount。
2. 自引用 mount 的 revision 无论与当前 HEAD 相同还是不同，resolve 都返回 mount 下的
   只读路径，不会读到当前工作区的未提交变化。
3. 在可可靠确认的自引用场景中，resolve 结果包含可供 agent 决策的关系与只读提示。
4. 自引用 mount 的 effective commit 与当前根 HEAD 相同时，Skills 与 scope 结果优先
   引导 agent 把兼容变更合并到当前根，不额外打开 maintenance root。
5. 多个 mount 指向同一 source、相同 effective commit 且任务兼容时，agent 能识别并
   复用一个已有 maintenance scope；不同 commit 不会被合并。
6. 没有兼容 scope 或明确选择隔离时，`maintenance open` 仍返回独立维护根，并在可可靠
   确认时标明 source、revision 与可复用 scope 的关系。
7. 关系未知时，resolve 和 open 维持普通 mount 行为，不产生错误的肯定标记，也不阻断
   原本可完成的工作。
8. 普通外部 mount、maintenance scope/status/handoff/close、lazy prepare/sync 和多根
   工作流均无行为回归。

## 8. 后续关系

本文是对同一需求在现状核对后的收敛，而不是另一个维护架构。实现采用最小附加字段，
并已同步 Skills、Architecture、Python code、测试和 Details；后续若扩展 URL 等价识别
或改变 scope 生命周期，应新建 Requirement，而不是回写本记录。

依赖方向如下：本文依赖 [DXG-REQ-0001](0001-agent-git-plugin.md) 的初始插件 surface；
[DXG-REQ-0003](0003-maintenance-scope-semantics.md) 后续细化本文的 scope 合并语义；
[DX-REQ-0004](0004-project-docs-and-requirement-lifecycle.md) 迁移并治理本文的状态和链接。
