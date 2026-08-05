# DX-ISSUE-0004：`hook --run` 无法产生公开 JSON contract 定义的 metadata warning

状态：`resolved`

创建日期：2026-08-05

严重程度：medium

来源：2026-08-05 对当前 `HEAD`（`259085abd8c324a53840f55a6783fa31eb874fbb`）进行的全仓 review；用户授权将严重度最高、已验证的问题记录为 Issue。

确认：2026-08-05，用户明确要求将本轮 review 创建的全部 6 个 Issue 置为确认状态。

## 问题

Architecture 的 HookItem contract 定义了 `revision_alignment: metadata_warning` 与非空
`metadata_mismatches`，用于表达 exact commit 已可用但 stable revision metadata 尚未安全对齐的可观察结果。Python
`HookService` 的 `_item()` 却无条件返回空 `metadata_mismatches`；其所有生产调用也未传入 `metadata_warning`。
顶层 warning 逻辑虽检查该值，但该分支无法从真实 reconciliation item 到达。

这使公开 contract 所定义的有效状态既不能被用户观察，也不能由顶层 `hook_run` 正确归纳为 warning。

## 具体场景

Architecture 为 checkout 后 reconciliation 定义了一个可区分的情形：direct install `D` 的 payload 存在，Git `HEAD`
能够安全对齐到 manifest 的 `resolved_commit`，但 runtime 中例如 `default_branch` 或 `revision_selector` 的 provenance
无法安全与 manifest 同步。`hook --run --root R --json` 不应为了把 metadata 写成完整而改变 fixed commit；它应保留
该 field-level mismatch 并让调用方看见。

这是一项 Architecture 已定义、但 Python 尚未 materialize 的状态，而不是已由现有 Python 测试构造出的单命令
reproduction。Python Impls 也明确将它列为 public-contract implementation gap。

## 当前错误状态

无论实际 hook item 的 provenance 是什么，`_item()` 都序列化：

```json
{
  "revision_alignment": "complete 或 not_applicable",
  "metadata_mismatches": []
}
```

所有生产调用仅传入 `complete` 或 `not_applicable`，所以结果中不可能出现
`"revision_alignment": "metadata_warning"` 或非空 `metadata_mismatches`。顶层虽然检查该状态以决定
`"status": "warning"`，该分支目前没有输入来源。

## 正确行为

在上述 commit 已对齐、metadata 未安全对齐的 case，公开结果至少应能表达：

```json
{
  "status": "warning",
  "operation": "hook_run",
  "items": [{
    "resolved_commit": "<manifest 的完整 commit>",
    "revision_alignment": "metadata_warning",
    "metadata_mismatches": ["<未对齐的 stable metadata field>"]
  }]
}
```

checkout 不回滚，且 durable manifest fixed commit 不被改写；调用方据此保留并处理 metadata 事实。

## 受影响范围与条件

- Python variant 的 `hook --run` JSON 和 human result，以及依赖 HookItem revision provenance 的调用方。
- 任一应保留 metadata mismatch、但 exact commit 仍可证明的 reconciliation 情形；当前实现不能如 contract 所述表示它。

## Authority 与证据

- [CLI JSON schema 的 HookItem](../doctidex-git/architecture/interfaces/cli-schema.md#6-hookitem)定义
  `metadata_warning` 和 `metadata_mismatches` 的语义；同页规定 per-item `metadata_warning` 应使顶层 status 为 warning。
- [CLI interface](../doctidex-git/architecture/interfaces/cli.md#hook-run)也将该结果作为公开 hook reconciliation contract 的一部分。
- [hooks.py](../../impls/libs/python/whero/doctidex/git/hooks.py#L575) 至 [hooks.py](../../impls/libs/python/whero/doctidex/git/hooks.py#L591) 固定返回空数组；
  [hooks.py](../../impls/libs/python/whero/doctidex/git/hooks.py#L180) 至 [hooks.py](../../impls/libs/python/whero/doctidex/git/hooks.py#L185) 的 warning 聚合却依赖不可产生的值。
- [Python Impls 的已知缺口](../doctidex-git/impls/python/architecture-coverage-evidence-and-worksite-validation.md#5-已知缺口与限制)已记录这一
  public-contract 实现缺口，表明它不是有意从 Architecture 移除该状态。

## 影响与后续决定

调用方无法区分 complete provenance 与应保留、待处理的 metadata mismatch，且文档承诺的状态机并不完整。后续需要
明确 mismatch 的实际检测来源，并同时实现 item fields、顶层 warning 聚合与覆盖该情形的回归测试；若不提供该能力，
应由经授权的 Architecture 变更移除契约。Issue 目前不授权任何一种变更。

## 处置

解决：2026-08-05，用户明确要求将本轮六项 Issue 标记为 `resolved`。根据
[DX-REQ-0021.4](../requirements/0021-resolve-confirmed-review-issues/04-hook-revision-provenance-contract.md)，产品选择了后者：
Architecture、CLI schema、Python 与 Impls 一并移除没有合法安全工作现场的 `metadata_warning` 和
`metadata_mismatches` contract。HookItem 只保留可证明的 `revision_alignment: complete|not_applicable`；不能安全确认的
情形仍返回 item-level `blocked` finding，顶层 warning 只据此聚合。

验证：`test_restore_existing_direct_payload_checks_out_manifest_exact_commit` 断言 hook item 不再包含被删除字段；完整
Python tests、Ruff、全根及 Requirement scope 的 validator、`git diff --check` 均通过。

残余边界：这不是 field-level provenance warning 的实现。若将来需要表达该状态，必须以新的 Requirement 先定义可实际
观察、可保留的 case 和 stable field names，再扩充 public contract。
