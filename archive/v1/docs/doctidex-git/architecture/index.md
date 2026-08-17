---
type: index
doctidex:
  type: index
---

# doctidex-git v1.0.0 架构

本目录定义 doctidex-git 当前、语言无关的共同产品设计。它让独立 variant 能正确实现同一
user surface，并能解释、接手、转换或保守保留另一个 variant 遗留的产品工作现场。它不要求
复制 Python 的 package、module、algorithm、storage primitive、lock 或调用链。

Architecture 的充分性以 user surface 的正确实现为止：它定义输入、默认值、持久状态与
artifact 的语义、可观察结果、失败、恢复、交接、兼容和安全边界；不改变这些行为的 bytes、
hash、temporary layout、publication algorithm 或 local optimization 属于 Impls evidence。
协议要求只由 [`spec/overview.md`](../../../spec/overview.md) 定义；本层不增加 protocol rule。

## 阅读路径

1. 从 [产品与 user surface](product-and-user-surfaces.md) 确定使用者、能力、前提、结果与
   非目标。
2. 面对一个已有目录或 host repository 时，先读 [工作现场与跨 variant 接手](worksite-handoff.md)：
   它列出可出现的配置和 artifact，并路由到每项的唯一 authority。
3. 按问题进入共同模型和 workflow：
   [树与 validation](tree-and-validation.md)、[external snapshot 与 presentation](external-snapshots-and-presentations.md)、
   [worktree 与 cache](worktrees-and-cache.md)，以及 [operation safety 与 recovery](operation-safety-and-recovery.md)。
4. 调用或集成时，读取 [CLI](interfaces/cli.md)、[JSON schema](interfaces/cli-schema.md) 或
   [programmatic integration](interfaces/programmatic-integration.md)。
5. 已安装 agent 的路由和信息边界由 [Published Skill system](skill-system.md) 定义；当前
   Python 如何落实所有共同事实见 [Python Impls](../impls/python/index.md)。

## 共同 authority

| 权威页面 | 唯一负责的事实 |
|---|---|
| [产品与 user surface](product-and-user-surfaces.md) | 产品问题、使用者、共同能力与非目标、逻辑责任和高层依赖。 |
| [工作现场与跨 variant 接手](worksite-handoff.md) | 实际遗留配置/artifact 的分类、发现方式、reader 读取边界和接手决策。 |
| [树与 validation](tree-and-validation.md) | doctidex root、owner/content/host 关系、`index.md` configuration、validation 语义。 |
| [External snapshot 与 presentation](external-snapshots-and-presentations.md) | install、manifest/runtime/link/hook、fixed snapshot、restore、mapping、hidden 与 host integration。 |
| [Worktree 与 cache](worktrees-and-cache.md) | writable worktree、runtime worktree record、shared source cache 和 cleanup 边界。 |
| [Operation safety 与 recovery](operation-safety-and-recovery.md) | plan/apply、result/failure、partial success、concurrency、diagnostic、transient artifact 和 recovery。 |
| [CLI](interfaces/cli.md) | argv grammar、command effect、default、write/network boundary 与 human next action。 |
| [JSON schema](interfaces/cli-schema.md) | stable JSON envelope、operation payload、code、pagination 与 field compatibility。 |
| [Programmatic integration](interfaces/programmatic-integration.md) | subprocess consumer 的 call/order/retry/compatibility discipline。 |
| [Published Skill system](skill-system.md) | 已安装 agent 的 audience、reading chain、command sufficiency 和 information boundary。 |

一个事实只在其中一页作为正文 authority 出现。接口页可引用模型和 workflow，但不重定义它们；
Impls 说明当前 variant 如何实现，不能以 source 或 test 静默改写共同语义。

## 工作现场与实现边界

当 variant 在 user surface 操作后留下 `index.md` configuration、host `.gitignore`、manifest、
runtime、install payload、presentation symlink、hook、worktree、cache、diagnostic 或中断证据时，
Architecture 必须令另一 variant 能解释其 identity、owner、状态、使用方式、lifecycle 和安全
处置。另一 variant 可以：

- 直接读写一个明确共同的 representation；
- 将已知 representation 转换为自己的 representation，同时保持 observable semantics；
- 在无法证明安全转换时保留现场并返回可行动的 blocked/diagnostic result。

它不得把存在的配置文件或 artifact 当作未定义的内部黑箱。反之，若 local mechanism 不出现为
工作现场配置/artifact，且不影响上述解释或 user surface 正确性，它不需要提升到 Architecture。

## 当前变体与历史边界

当前唯一实现变体是 [Python `1.0.0`](../impls/python/index.md)。它的 source、tests 和
Published Skills 是当前事实 evidence，不是 Architecture authority。重构前的页面保存在
[DX-REQ-0015 前 baseline](../archive/baselines/pre-dx-req-0015/index.md)，并统一标注
`format-illegal`；它们仅保留历史证据，不能用于定义本目录的当前结构或产品行为。

本设计细化 [DX-REQ-0015](../../requirements/0015-architecture-and-impls-document-principles.md)。
