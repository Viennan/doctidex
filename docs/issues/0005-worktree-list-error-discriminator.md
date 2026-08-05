# DX-ISSUE-0005：`worktree list` 在 runtime 损坏时返回错误的 operation discriminator

状态：`resolved`

创建日期：2026-08-05

严重程度：medium

来源：2026-08-05 对当前 `HEAD`（`259085abd8c324a53840f55a6783fa31eb874fbb`）进行的全仓 review；用户授权将严重度最高、已验证的问题记录为 Issue。

确认：2026-08-05，用户明确要求将本轮 review 创建的全部 6 个 Issue 置为确认状态。

## 问题

`WorktreeService.list()` 直接调用 `RootStorage.read_runtime()`。当 `runtime.json` 无法通过 schema validation 时，
该共同 helper 构造的 `DoctidexError.operation` 固定为 `external`。异常 envelope 因而把一次 `worktree list`
调用标识为 `operation: "external"`，而不是该 command 的 `worktree_list`。

## 具体场景

设 owner root `R` 的 `.doctidex/git/runtime.json` 已损坏为 schema 不接受的 JSON object，例如缺少 required
record collections。调用者执行：

```text
doctidex-git worktree list --root R --json
```

`WorktreeService.list()` 的第一步就是 `self.storage.read_runtime()`；它尚未来得及建立 list response 或转换 command
context，便收到共同 storage helper 构造的错误。

## 当前错误状态

失败结果以 external surface 身份返回，而非请求的 worktree list：

```json
{
  "status": "blocked",
  "operation": "external",
  "findings": [{"code": "mapping_damaged"}],
  "affected": ["R"]
}
```

`mapping_damaged` 与保留现场的动作本身仍有意义，但使用 `operation: "external"` 后，按 operation 分派 JSON schema
的客户端会进入错误分支，无法把该结果作为 `worktree_list` 的失败处理。

## 正确行为

同一损坏现场应保留 `mapping_damaged`、affected root 与恢复 action，但 command discriminator 必须保持调用边界：

```json
{"status": "blocked", "operation": "worktree_list", "findings": [{"code": "mapping_damaged"}]}
```

这样调用方才能按 `worktree_list` contract 读取失败，而不需要从 human message 或 domain 猜测原命令。

## 受影响范围与条件

- Python variant 的 `worktree list` 失败 JSON/human result；依 operation discriminator 路由或解析失败结果的调用方。
- 选中的 owner root 存在损坏或不兼容的 `.doctidex/git/runtime.json`。

## Authority 与证据

- [CLI JSON schema 的 `worktree_list`](../doctidex-git/architecture/interfaces/cli-schema.md#82-worktree_list)要求
  operation discriminator 为 `worktree_list`，这是该 command 的 stable public field。
- [worktrees.py](../../impls/libs/python/whero/doctidex/git/worktrees.py#L112) 至 [worktrees.py](../../impls/libs/python/whero/doctidex/git/worktrees.py#L121)
  未在读 runtime 失败时重写 command context。
- [storage.py](../../impls/libs/python/whero/doctidex/git/storage.py#L69) 至 [storage.py](../../impls/libs/python/whero/doctidex/git/storage.py#L80)
  将所有损坏 runtime 的 error 固定为 `operation="external"`。
- [Python Impls 的已知缺口](../doctidex-git/impls/python/architecture-coverage-evidence-and-worksite-validation.md#5-已知缺口与限制)已明确记录此 contract 不符合；
  现有 damage test 只断言 `mapping_damaged`，未断言 discriminator。

## 影响与后续决定

机器调用方会将 worktree 查询失败错误路由到错误的 command schema，破坏 JSON contract 的稳定分派。后续应让
shared runtime reader 接受调用 operation，或在每个 command boundary 重建保留原有 code/affected/actions 的错误，
并为 `worktree list` 损坏 runtime 增加 discriminator 回归测试。Issue 目前不授权实现或文档修改。

## 处置

解决：2026-08-05，用户明确要求将本轮六项 Issue 标记为 `resolved`。根据
[DX-REQ-0021.5](../requirements/0021-resolve-confirmed-review-issues/05-worktree-runtime-error-discriminator.md)，
`RootStorage.read_runtime()` 与 `update_runtime()` 接受调用方 operation，`WorktreeService.open/list/close` 均传入
自己的 command discriminator。因此损坏 runtime 的 `worktree list` 保留共同 `mapping_damaged` diagnosis，但其 envelope
标识为 `operation: worktree_list`。

验证：`test_worktree_list_reports_its_operation_for_damaged_runtime` 构造 invalid `runtime.json`，并断言返回
`worktree_list`、`mapping_damaged` 与 owner root；完整 Python tests、Ruff、全根及 Requirement scope 的 validator、
`git diff --check` 均通过。

残余边界：共享 storage error 仍采用同一 `mapping_damaged` code、affected root 和恢复 action；调用方应以 operation
分派命令 contract，而不应把 domain 或 human message 当作 discriminator。
