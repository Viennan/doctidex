# 子需求 0021.5：worktree runtime 错误的 operation 判别

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0021.5` |
| 状态 | `implemented` |
| 日期 | 2026-08-05 |
| 所属大型 Requirement | [DX-REQ-0021](overview.md) |
| 对应 Issue | [DX-ISSUE-0005](../../issues/0005-worktree-list-error-discriminator.md) |
| 影响范围 | Python `RootStorage`、`WorktreeService` error boundary、worktree CLI JSON tests、Python Impls evidence。 |
| 当前 authority | [CLI schema 的 `worktree_list`](../../doctidex-git/architecture/interfaces/cli-schema.md#82-worktree_list)。 |

## 1. 需求意图

共享 storage helper 可以产生共同的 `mapping_damaged` diagnosis，但不能替调用 command 决定公开 operation。调用方按
`operation` 分派 JSON payload，因此 `worktree list` 的 runtime 失败必须仍标识为 `worktree_list`。

## 2. 解决方案

将 runtime read 的 error context 参数化，并在 command boundary 显式传递：

1. `RootStorage.read_runtime()` 接受 operation（必要时也接受 domain）参数，默认值仅供明确属于 external surface 的
   旧调用使用；它继续提供相同的 damaged-state code、affected root 和 recovery action。
2. `WorktreeService.list()` 以 `operation="worktree_list"` 调用该 helper。审查同一 service 的 `open`、`close`
   等调用点，并为各自公开 command 传入正确 operation，避免相同 helper 在其他 worktree path 重演该错误。
3. CLI exception renderer 原样保留调用方提供的 operation；不得通过字符串匹配 error message 重建 context。
4. 更新 Python Impls 的 known-gaps 表，移除已修复的 `worktree_list` discriminator limitation。

## 3. 验收标准

- 构造 schema-invalid `R/.doctidex/git/runtime.json` 并运行 `doctidex-git worktree list --root R --json`，结果为
  `status: blocked`、`operation: worktree_list`，并保留 `mapping_damaged`、affected root 和现有恢复 action。
- runtime 合法时，`worktree list` 的分页、filters、cursor 和 unavailable warning 语义保持不变。
- external command 的 runtime failures 仍保留其已有 operation；worktree open/close 的损坏-runtime error 也与其
  command boundary 一致。
- 新测试直接断言 operation discriminator，而不只断言 finding code；Python Impls 记录修复 evidence。

## 4. 实施状态

2026-08-05 已完成实施。`RootStorage.read_runtime()` 与 `update_runtime()` 接收 caller operation，
`WorktreeService.open/list/close` 均显式传入各自 command。`test_worktree_list_reports_its_operation_for_damaged_runtime`
验证 invalid runtime 返回 `operation: worktree_list`、`mapping_damaged` 与 owner root。完整 Python tests、Ruff、全根
validation 与 `git diff --check` 均通过。
