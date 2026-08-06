# 发布、恢复与私有机制

本页说明 Python 如何支撑 [operation safety and recovery](../../architecture/operation-safety-and-recovery.md)。它负责 lock/temp/atomic-replace/source-mutation/diagnostic 的实现细节，以及当前无法由源码/测试证实的边界；它不会把这些机制重新定义为 Architecture 的必需行为。

<a id="1-mutation-boundaries"></a>
## 1. 变更边界

| 资源 | Python 协调方式 | 面向产品的保证 |
|---|---|---|
| owner root 状态 | `RootStorage.mutation()` 在受管发布期间使用 root-local directory lock。 | conflict/interruption 时保留状态，结果提供证据；不提供全局 transaction。 |
| source/cache | `source_mutation` 按 canonical source / source ID 定位。 | 并发的 source/cache 变更有界，并会重观测/保留，而不强制删除。 |
| host hook | 注册期间使用 hook-local directory lock。 | foreign hook 仍受保护；并发安装不能成为覆盖的理由。 |
| 单个 JSON/text file | 当前 Python 代码使用同目录 temporary data、fsync 和 replace。 | 单个物理文件可原子发布；整个 workflow 的状态仍可能是部分完成。 |
| diagnostic | 在用户 cache 中尽力写入。 | 可以报告 opaque ID；diagnostic 失败不会在正常结果中暴露 traceback。 |

`RootStorage`、source 和 hook 的实现见[源码/状态存储](components/source-and-state-storage.md)和[checkout hook](components/checkout-hook-reconciliation.md)。它们的具体 directory 名称、timeout/retry 值、hash、JSON serializing 和 temp 名称有意保持为本地细节。

<a id="2-partial-effects-and-recovery"></a>
## 2. 部分效果与恢复

Python 服务独立发布 payload、`.gitignore`、index frontmatter、manifest、runtime、symlink、worktree、cache 或 hook entrypoint。一个效果发生后出现异常，可能留下有效但不完整的工作现场。因此，该实现报告已确认的 `changed` path、`affected` evidence 和稳定 finding，而不尝试大范围 rollback。后续操作会重读实际需要的相关当前状态，并遵循 Architecture 的 preserve/restore/block 规则。

| 情形 | Python 行为 | 边界 |
|---|---|---|
| 无效 manifest/runtime | validator 阻止自动变更。 | 不静默 repair/migration。 |
| worktree 创建后的 interruption | 原生 worktree 可能保留而没有已发布记录。 | 作为 orphan evidence 保留；不是受管 close target。 |
| link/index/manifest conflict | preflight 在可观察到变更的 target/ownership/tracking 时检测冲突。 | 重新运行 dry-run；不得覆盖。 |
| hook 协调无法证明 dependency revision | 移动/保留 hidden payload 加 runtime evidence。 | 不猜测 revision，也不重写 manifest。 |
| dry-run/apply 之间 cache state 发生变化 | `cache clean` 在删除前重新分类。 | 在 active/unknown/conflict 时保留。 |

<a id="3-evidence-boundary"></a>
## 3. 证据边界

Python test suite 覆盖 root lock conflict、被中断的 worktree publication、restore 的 blocked/partial item、hook hidden reconciliation 和 cache recheck。它并不能确立一项普遍定理，保证每项服务都在持有全部相关 lock 时重读每一项已观察输入。特别是，`WorktreeService.close` 在其 source/root mutation boundary 之前观察 runtime record/status；在补充源码/测试证据前，文档不得声称 close 在 lock 内重新验证。

这是实现证据边界，不是放弃共同 `changed`/`unavailable` 保留语义的许可。未来的代码/测试变更需要自己的已授权 Requirement，本页才能宣称更强的 race 保证。
