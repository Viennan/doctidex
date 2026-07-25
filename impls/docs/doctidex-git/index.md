# doctidex-git 当前实现说明

状态：Draft，非规范性实现文档

本目录说明 `whero-doctidex` 0.1.0 中 `doctidex-git` 的当前实现。它回答三类问题：

- Python 代码实际读取、计算、保存和呈现了什么；
- 每条 CLI 命令当前接受什么输入、产生什么副作用、返回哪些字段；
- agent 应如何理解这些事实，哪些结论仍必须由 agent 或用户作出。

这里不是 doctidex 协议正文，也不是对未来实现的承诺。规范要求以
[`spec/overview.md`](../../../spec/overview.md) 为准；agent 可见产品设计以
[`agent-git-plugin.md`](../agent-git-plugin.md) 为准；本目录以当前 Python 代码和
测试为准。当产品设计与代码尚有差距时，本目录明确记录当前行为和限制。

## 文档导航

- [总体架构](architecture.md)：分层、模块职责、控制流和公开/内部边界。
- [协议与目录树](protocol-and-tree.md)：frontmatter、链接、路径、过滤、负责索引和
  协议校验。
- [Git、mount 与维护运行时](git-runtime.md)：source repository、revision view、
  projection、持久状态、锁和 maintenance root。
- [CLI 命令参考](cli-commands.md)：完整命令、参数、根选择、触网和写入行为。
- [CLI 输出字段参考](cli-output.md)：JSON、人读格式、退出码，以及所有返回字段和
  嵌套字段。
- [Agent 解读指南](agent-interpretation.md)：如何从状态和字段形成下一步，不把候选
  或运行状态误判为语义结论。
- [开发、测试与当前限制](development.md)：本仓库开发方式、测试覆盖和已知差距。

## 核心术语

| 术语 | 当前实现中的含义 |
|---|---|
| doctidex 根 | 某个目录，其 `index.md` 可被解析且包含 `doctidex.root: true`。 |
| 宿主根（host root） | 当前 CLI 操作所选中的 doctidex 根；它拥有本次解析使用的唯一 mount 表。 |
| 源目录树（source tree） | 由 Git mount 引入的完整外部 doctidex 根。当前实现不支持只挂载仓库子目录。 |
| 根索引 | doctidex 根直接包含的 `index.md`。只有它可以声明 `doctidex.mounts`。 |
| 负责索引（responsible index） | 对某个未排除路径负责的最近祖先 `index.md`。进入具有有效 `index.md` 的子目录后，责任转移到该文件。 |
| 适用 log（applicable log） | 从目标目录向宿主根查找时遇到的最近 `log.md`；不存在时为 `null`。 |
| 内部路径 | 以 doctidex 根为基准的逻辑路径。以 `/` 开头不表示文件系统根。 |
| 链接根（link root） | 解析绝对内部路径时使用的 doctidex 根。CLI `resolve` 当前返回所选宿主根。 |
| mount namespace | `/.doctidex/mounts`。同一次宿主解析中只有一个；后续再次出现该前缀会回到起始宿主的 namespace。 |
| mount 声明 | 根 `index.md` 中 `doctidex.mounts[]` 的一个映射，基础字段为 `type`、`url`、`mount_path`。 |
| Git revision selector | Git 扩展的 `revision` 中唯一的 `commit`、`tag` 或 `branch` 键和值。 |
| 声明 revision | 用户配置的 selector，表示希望跟随的 Git 引用或固定 commit。 |
| 有效 commit（effective commit） | 某个 mount 当前实际读取的 40 位 Git commit。branch/tag 更新不会自动改变它。 |
| lazy mount | 声明存在但尚未准备为可读路径的 mount，状态为 `not_prepared`。 |
| revision view | 按 source URL 和有效 commit 复用的 detached、只读 worktree；属于内部运行时。 |
| projection | 从 revision view 构建的宿主相关只读目录呈现，用于实现不可嵌套 mount namespace；属于内部运行时。 |
| presentation | projection 在宿主 `/.doctidex/mounts/...` 路径上的文件系统入口。正常使用者只接触该入口。 |
| maintenance root | 从有效 commit 新建的独立、可写 detached worktree。它是 agent 维护挂载源时应使用的路径。 |
| 协议结构 | CLI 能确定的格式、路径、连续性、过滤和声明结构事实。 |
| 语义候选 | CLI 找到、但必须阅读正文或 diff 后才能判断的候选事项，不等于错误。 |
| 插件就绪状态 | `.gitignore`、tracked mount 内容和 Git 扩展配置是否允许插件操作；它不等于协议符合性。 |
| finding | 一个确定性问题或候选说明，包含稳定 `code`、消息和建议动作。 |
| state store | 保存 mount 有效 commit 和 maintenance root 记录的内部 JSON 状态。它不属于 doctidex 目录树。 |

## 阅读边界

Agent 正常执行任务时通常只需要 Skills、CLI 命令参考、输出字段参考和 Agent 解读
指南。架构、Git 运行时与开发文档用于实现维护和排障，不应要求普通使用者理解
source hash、worktree、projection 或锁后才能操作。

CLI 不调用 AI，也不生成索引正文、目录说明、log 记录、维护顺序或审阅结论。代码
提供结构化事实和候选；agent 负责阅读文件、形成语义判断并在需要授权时询问用户。
