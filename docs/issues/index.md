---
type: index
doctidex:
  type: index
---

# Issues 导航

本目录保存由 review 或用户报告收集、且用户明确授权记录的问题。Issue 是问题及其处置的
项目治理记录，不定义新的需求、当前共同设计或具体实现事实；相应 authority 仍属于
Requirements、Architecture、Impls、协议或可验证的 source/test evidence。

每份 Issue 使用 `<NNNN>-<title>.md`，并以同号 `DX-ISSUE-<NNNN>` 作为稳定 ID；编号在本目录内
连续且稳定。创建时只能使用 `open` 状态，并应完整说明问题、影响条件、证据、受影响范围、关联
authority 和来源。
用户必须明确授权创建某一具体 Issue；报告问题、要求 review、授权 review 或得到 finding
均不构成创建授权。

| 状态 | 含义与授权边界 |
|---|---|
| `open` | 已获用户授权记录，尚未由用户确认真实性或处置。 |
| `confirmed` | 用户已明确授权将已核实的问题设为确认状态。 |
| `resolved` | 用户已明确授权将问题设为已解决；实现、测试通过或 review 结论本身不足以转换。 |
| `ignored` | 用户已明确授权不再报告该问题；保留其理由与风险，避免后续 review 重复报告。 |

除创建时的 `open` 外，转换到 `confirmed`、`resolved` 或 `ignored` 必须具有针对该 Issue 和
目标状态的明确用户授权。重开或其他状态回退同样需要用户明确指令，agent 不得从证据、
用户沉默、一般性认可、实现完成或 review 结果推断状态转换。

Review 必须核对当前 `confirmed` 和 `ignored` Issues：匹配 `confirmed` Issue 时在 finding 中
关联其 ID，避免重复报告；匹配 `ignored` Issue 时不报告，除非用户明确要求包含已忽略问题。
这项关联发生在 review 输出中，不授权 review 自动创建、修改或转换 Issue 文档。

| ID | 状态 | 严重程度 | 问题 |
|---|---|---|---|
| [DX-ISSUE-0001](0001-external-apply-stale-preconditions.md) | `resolved` | high | `external link --apply` 在锁内使用过期前置条件，可能损坏 durable mapping。 |
| [DX-ISSUE-0002](0002-validator-accepts-query-links.md) | `resolved` | high | 协议 validator 将仅含 query 的 link 误当作当前文档 file-path link。 |
| [DX-ISSUE-0003](0003-root-index-omits-github.md) | `resolved` | high | 根索引未使 `.github` 工作流目录可达，仓库当前不符合协议。 |
| [DX-ISSUE-0004](0004-hook-metadata-warning-unreachable.md) | `resolved` | medium | `hook --run` 无法产生公开 JSON contract 定义的 metadata warning。 |
| [DX-ISSUE-0005](0005-worktree-list-error-discriminator.md) | `resolved` | medium | `worktree list` 在 runtime 损坏时返回错误的 operation discriminator。 |
| [DX-ISSUE-0006](0006-root-index-stale-protocol-version.md) | `resolved` | medium | 仓库根入口将当前协议版本错误标为 `v1.0.0`。 |
