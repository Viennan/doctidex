# 子需求 0021.4：hook revision provenance contract 对齐

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0021.4` |
| 状态 | `implemented` |
| 日期 | 2026-08-05 |
| 所属大型 Requirement | [DX-REQ-0021](overview.md) |
| 对应 Issue | [DX-ISSUE-0004](../../issues/0004-hook-metadata-warning-unreachable.md) |
| 影响范围 | doctidex-git Architecture CLI/JSON contract、Python hook service、hook JSON tests、Python Impls 的 known gaps/evidence。 |
| 当前 authority | [Hook CLI](../../doctidex-git/architecture/interfaces/cli.md#13-hook)与[HookItem schema](../../doctidex-git/architecture/interfaces/cli-schema.md#69-hook_install-与-hook_run)。 |

## 1. 需求意图

消除 Architecture、Python 实现和测试对 hook revision provenance 结果集合的不一致。当前 `metadata_warning` 与
`metadata_mismatches` 没有已定义的安全产生条件：可更新的 runtime provenance 会被对齐，而无法读写或无法证明的
state 已按 preserve-first 规则成为 blocked。继续保留一个没有合法工作现场的 public state 会误导调用方和维护者。

## 2. 解决方案

将 revision outcome 收敛为可观察且可测试的状态，而不是在 Python 中编造 metadata-warning case：

1. 先更新 Architecture 的 HookItem 和 `hook --run` 文字，删除 `revision_alignment: metadata_warning` 与
   `metadata_mismatches` fields；明确 `complete` 表示 exact commit 和可写 runtime provenance 已按 portable metadata
   对齐，`not_applicable` 表示没有可对齐 target，任何无法安全读取、校验、checkout 或写入 provenance 的情形为
   item-level `blocked` 并提供 finding。
2. 更新 JSON schema、human interface 和 consumers，顶层 `status: warning` 只由 item-level `blocked` 或既有
   preserved conditions 决定；checkout 仍不回滚，manifest fixed commit 仍不被 hook 改写。
3. 删除 Python 中永远不可达的 `metadata_warning` warning branch，并把 `_item()` 的 fields 调整为与经修订的
   Architecture 完全一致。更新 JSON-shape tests，确认不再允许已删除字段或枚举值。
4. 更新 Python Impls：移除“public contract implementation gap”已知限制，替换为 revised contract 的 source/test
   evidence 和 preserved/blocked 边界说明。

该决定是有意的 public contract 收窄，不是把 Issue 隐藏在代码实现之后；因此 Architecture 必须先于 Impls 和代码更新。
如后续产品需要 field-level metadata warning，应创建新的 Requirement，先定义可实际观测、可保留的合法工作现场和
stable field names，再重新扩充 contract。

## 3. 验收标准

- 经授权更新后的 Architecture、CLI schema、Python JSON output 和 tests 使用同一个 HookItem 字段与
  `revision_alignment` 枚举集合；仓库中不残留无法产生的 `metadata_warning` contract 承诺。
- 正常 direct/dependency reconciliation 仍能报告 `complete` 或 `not_applicable`；dirty、损坏、source/root conflict
  等不安全情况仍以 `blocked` finding 保留现场，checkout 不回滚。
- hook 的 operation、existing `counts`、offline 不 fetch 和不改写 manifest fixed commit 的共同行为不回归。
- Python Impls 的 known-gaps 表不再把本项列为当前 public contract 缺口，并给出对应测试路径。

## 4. 实施状态

2026-08-05 已完成 Architecture、Impls、Python 与测试对齐。HookItem 仅保留
`revision_alignment: complete|not_applicable`，Python 不再输出未定义 warning field，任何无法安全证明的 item 保持
blocked finding；`test_restore_existing_direct_payload_checks_out_manifest_exact_commit` 直接断言公开 item 不含已删除字段。
完整 Python tests、Ruff、全根 validation 与 `git diff --check` 均通过。
