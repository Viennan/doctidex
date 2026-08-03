# Operation、result 与 failure 模型

> 归档状态：`format-illegal`。本页是 DX-REQ-0015 前的历史文档基线，不定义当前产品。

本篇定义所有 CLI、human、agent 和 program surface 共享的调用与结果语义。精确 command
grammar 见 [CLI](../interfaces/cli.md)，JSON 字段 schema 见
[CLI JSON Schema](../interfaces/cli-schema.md)。

## 1. Command Context

Command Context 包含 operation、raw inputs、cwd、explicit/default root inputs、selected root、
source/revision/path filters、dry-run/apply mode、pagination request 和 output mode。Context 只对
一次调用有效；previous plan、warning 或 cwd 不构成未来 apply authorization。

Selection 是领域步骤而不是 parser shortcut：root、owner、source、revision、install parent、
target 和 worktree 任一存在多个合理候选时，结果必须公开 candidates/affected 并要求用户决定。

## 2. Plan 与 effect

Write operation 分成 Observation、Plan、Revalidation 和 Publication：

1. Observation 读取 root/source/Git/managed state。
2. Plan 固定 identity、expected state 和 planned effects；默认 dry-run 到此结束。
3. Apply 在 mutation boundary 内重读影响安全性的事实；变化则 conflict。
4. Publication 以可诊断、可重试为原则逐项发布，并记录可可靠确定的 changed/network。

Plan 不是 lease 或 authorization token；apply 必须重新观察。跨 frontmatter、Git objects、ignore、
manifest、runtime、worktree 与 symlink 没有总事务。

## 3. Result Envelope

每个 Result 必须给出：schema version、operation、status、result narrative、selected root、changed
paths、actual network、findings、next actions、affected objects、requires-user reason、collection
metadata 和 operation fields。

| 属性 | 语义 |
|---|---|
| `status` | `ok`、`warning` 或 `blocked`；描述 operation，不替代 domain conclusion。 |
| `result` | 已完成、未完成与保留状态的稳定含义。 |
| `changed` | 本次可可靠确定的公开 path effects；planned path 不得混入。Blocked 结果无法完整重建 effect 时可以为空，但必须用 `affected` 和下一步要求重新观察现场。 |
| `network` | 本次是否实际访问 network。 |
| `affected` | 失败、部分成功或决定涉及的 identity/path。 |
| `requires_user` | 继续所需的输入、权限、credentials 或 Git decision 类别。 |
| `next_actions` | 基于保留结果可安全采取的有界动作。 |

Validation 的 `protocol_structure`、`scan_complete`、`semantic_review` 与 coverage 是互相独立的
domain conclusion；exit code 或 top-level status 不能替代它们。

## 4. Finding 与 failure

Finding 包含 domain、severity、stable code、human message、optional path 和 actions。Code 用于
program branching；message 可演进。Expected failure 必须回答：什么未完成、影响什么、什么
仍可用、最小恢复动作以及是否需要用户。

Failure 类别包括 argument/root、protocol、source/revision/network、dependency、target/mapping、
host Git、recovery、worktree、cache、concurrency/interruption 与 unexpected internal failure。
任何分类都不得用 destructive cleanup 掩盖不确定 ownership；network/credential failure 不得
伪装成 missing revision。

## 5. Partial success 与 interruption

Batch restore、external publication 和跨 root 工作没有总 rollback。Independent success 保留；
顶层 warning/blocked 必须列出成功项、失败项和 continuation。Interruption 停止启动新步骤，
保留已发布 effects；retry 复用相同 identity，只补齐缺失步骤。

Unexpected failure 只在 optional `details.diagnostic_id` 公开 bounded diagnostic ID，而不是
traceback、credentials 或 internal path；解析出 operation 前的 usage failure 使用 operation
`command`。
首次可安全重试一次；重复失败升级给 human/operator。

## 6. Collection 与 cursor

Collection 对 domain selection 应用 scope/filter 和稳定排序，再计算 total 与分页。每个 list
公开 total、returned、truncated；cursor 绑定 operation query、root/filter 和足以拒绝明显陈旧
continuation 的 observed state。各 Impls 说明 state observation 与 token encoding；它们不构成
跨实现 wire identity。Restore 使用 versioned manifest 与 normalized install-ID selection，并只
执行当前页，因此前页 payload effect 不改变后页 cursor identity。Identity/state 不匹配时返回
`cursor_invalid`，调用方从第一页重启。默认输出与每次 batch effect 都有界。
