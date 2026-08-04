# Architecture 覆盖、证据与工作现场验证

本页将 Python `1.0.0` 对 [Architecture](../../architecture/index.md) 的实现、源码/测试证据和工作现场验证关联起来。它不是第二份 Architecture：每一行都链接共同的权威说明，Python 行只交代入口、责任方、证据和限制。

<a id="1-capability-coverage"></a>
## 1. 能力覆盖

| Architecture 能力 | Python 入口与责任方 | 主要源码与测试证据 |
|---|---|---|
| 树、根、配置与验证 | `validate`；`protocol.document/root/validation`。 | [protocol/root 观察](components/protocol-and-root-observation.md)、[`test_protocol.py`](../../../../impls/libs/python/tests/test_protocol.py)。 |
| 结果、finding、JSON 与分页 | CLI 分发器、`errors`、`results` 与渲染器。 | [CLI/结果](components/cli-results-and-rendering.md)、protocol/plugin 的结果测试。 |
| 固定 external snapshot 与 manifest/runtime | `external install/restore`；`ExternalService`、source/storage。 | [external 实现](components/external-presentation-and-mapping.md)、[工作现场清单](worksite-inventory-and-construction.md)、插件 install/restore 测试。 |
| 持久呈现与 link lifecycle | `external link/rebind/unlink/link-parse`；external mapping 辅助逻辑。 | [工作现场清单](worksite-inventory-and-construction.md)中的 link/mapping 行、插件 safe/retry/portable-link/rebind/unlink 测试。 |
| 受引用保护的 remove | `external remove`；树观察加 source/root storage。 | external component、插件 remove/reference 测试。 |
| checkout 注册、协调与隐藏 | `hook --install/run`；`HookService`。 | [hook component](components/checkout-hook-reconciliation.md)、插件 foreign/alignment/hidden 测试。 |
| 可写 worktree | `worktree open/list/close`；`WorktreeService`。 | [worktree component](components/worktrees-and-cache-cleanup.md)、插件 clean/changed/unavailable/orphan 测试。 |
| 共享 cache 清理 | `cache clean`；`CacheService`。 | worktree component、插件 active/prunable/auto/recheck 测试。 |
| 并发、恢复与 diagnostic | 所有写服务、`RootStorage`、source/hook mutation 辅助逻辑。 | [发布/恢复](publication-recovery-and-private-mechanics.md)、lock/interruption/recovery 测试。 |
| 已安装的 agent 用户界面 | 插件 manifest 加 Overview/Read/Maintenance Skills。 | [变体交付](variant-delivery-and-surface.md)、[Skill system](../../architecture/skill-system.md)；产品验证不在 Python unit suite 范围内。 |

<a id="2-worksite-evidence-matrix"></a>
## 2. 工作现场证据矩阵

[工作现场清单](worksite-inventory-and-construction.md#3-scenario-construction-matrix)是必需的 Python 证据矩阵。它覆盖的是语义类别而非每一个本地分支：空现场/dry-run、直接 selector 变体、dependency/promotion、安全/不安全 link、缺失后的 restore、portable dependency、hook/hidden、remove 保护、worktree 状态、cache 状态以及 interruption/damage。每个类别都把实际物化的配置/artifact 映射到 Architecture 权威说明及测试/fixture 证据。

只有源码/测试证据能证明物化文件、选项值、artifact 状态和用户可见效果完全相同时，才可以合并等价场景。私有 cache path/hash、JSON 格式、lock primitive 和 helper call graph 无须单列场景，除非它们改变这些可观察的 handoff 语义。

<a id="3-paired-reader-verifier-protocol"></a>
## 3. 配对 reader/verifier 协议

进行文档重构验证时，执行者使用已安装的 Python console script 构造隔离的本地 Git fixture，保留完整工作现场并捕获 `--json` transcript。受限的 Architecture reader 只能得到：

1. fixture 工作现场；
2. 用户可见 transcript 和变体标识；
3. 当前的 `docs/doctidex-git/architecture/`。

它必须递归清点每个实际配置/artifact，说明每个物化选项和 artifact 的 producer/consumer/use/lifecycle，并引用强而直接的 Architecture 证据。它不得读取本 Impls 目录、源码、测试、Requirements、fixture 构造说明或先前的审阅报告。

随后，独立的全知识 verifier 会阅读适用的 Requirements、Architecture、全部 Impls、源码、测试、已发布用户界面、fixture 构造事实和 reader 输出。它检查每份被引用的证据是否确实蕴含相应主张，排除编造或牵强的推论，并判断该理解能否支撑正确的用户界面行为：输入/默认值、配置/artifact 效果、结果、失败、恢复、handoff 与安全性。它不要求重建每项本地算法、调用、lock 或字节细节。

必要的说明若无法在不离开 Architecture 的前提下得到支持，verifier 就记录一个 Architecture 缺口；它不能用自身的全部知识替 reader 补足缺口。结果和 fixture 位置记录在 [DX-REQ-0015](../../../requirements/0015-architecture-and-impls-document-principles.md)，不会提供给后续的原始 reader。实质性修复后最多进行一次有针对性的配对复跑。

<a id="4-current-validation-record"></a>
## 4. 当前验证记录

Python 基线测试套件位于 [`impls/libs/python/tests`](../../../../impls/libs/python/tests)。DX-REQ-0015 记录了已完成的隔离 fixture Architecture-only reader 和独立全知识证据检查，其中包括针对 `index.md` protocol metadata 和 cache-private container 的直接证据修复。文档验证还检查链接、doctidex 可达性、源码/测试目标可读性和清单覆盖度。

<a id="5-known-gaps-and-limits"></a>
## 5. 已知缺口与限制

| 类别 | 证据 | 当前文档处置 |
|---|---|---|
| 本次已解决的 Architecture/文档不一致 | 旧 Architecture 称不可用 worktree 的 close 会清理陈旧记录；源码、JSON contract 和既有 Python Impls 都保留该记录。 | Architecture 现要求保留 `worktree_unavailable`；无需改动代码。 |
| public contract 的实现缺口 | JSON hook contract 允许在非空 `metadata_mismatches` 时使用 `revision_alignment: metadata_warning`，但 `HookService` 目前从不产生该状态，测试也未覆盖它。 | Architecture JSON contract 仍是权威；Python 变体将其记录为 material limitation。产品/代码/测试修复需要单独授权。 |
| public contract 的实现缺口 | 损坏的 `runtime.json` 由 `worktree list` 调用 `RootStorage.read_runtime()` 时会得到 `operation: "external"`；JSON contract 为该命令定义的 discriminator 是 `worktree_list`。现有 damage 测试只断言 finding code，不断言该 discriminator。 | 被阻止的调用方可以安全使用共同 envelope/finding 并保留工作现场，但 Python 当前不符合按命令区分的 discriminator contract。产品/代码/测试修复需要单独授权。 |
| 实现证据边界 | 旧 Python 文档声称全部 External/Worktree/Cache/Hook 服务都会在 lock 内重读状态；`WorktreeService.close` 在 source/root mutation boundary 之前观察 record/status，且没有 race 证据。 | 本次重构移除了这项无证据的主张；不作更强的并发保证。 |
| 变体私有机制 | JSON encoding/hash、source/cache ID、Git argv、lock/temp 名称、symlink 计算和 module/helper graph。 | 在 Impls/source 中按需要记录；除非未来互操作 contract 使其中某项可观察，否则不纳入 Architecture 完整性。 |
