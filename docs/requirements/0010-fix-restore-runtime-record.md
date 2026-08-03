# 需求 0010：修复 restore 生成无效 runtime record

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0010` |
| 状态 | `approved` |
| 日期 | 2026-08-01 |
| 来源 | 用户要求确认 `external restore` 遗漏 `requested_default` 是否为 bug；确认后创建独立 bugfix 需求，并随后明确要求实施修复。 |
| 影响范围 | Python doctidex-git external restore、runtime state、回归测试和 Python Impls limitation/coverage 文档。 |
| 协议关系 | 非规范性实现修复；不改变 [`doctidex` 协议](../../spec/overview.md)或 doctidex-git Architecture 的公共能力。 |

## 1. 已确认的问题

Python `ExternalService._restore_item` 从 portable manifest 重建 direct install 时，会写入
`canonical_source`、`role`、`parents` 和 `managed_state`，但没有写入 runtime install validator
要求的 boolean `requested_default`。Restore 本次调用仍返回 item `state: restored`，随后任何通过
`RootStorage.read_runtime()` 读取该 state 的操作都会把整个 runtime document 判为 damaged。

这里的 damaged 指 runtime state 不符合实现自己的闭合 schema，并不表示恢复出的 Git payload
内容损坏。判定链如下：

1. `_valid_runtime` 要求 `installs` 中每项都通过 `_valid_install(..., portable=False)`；
2. runtime install 的 `requested_default` 必须是 boolean，字段缺失时 `record.get(...)` 为 null，
   `isinstance(..., bool)` 因而返回 false；
3. 任一 install record 无效都会使整份 `_valid_runtime` 返回 false；
4. `RootStorage.read_runtime()` 将这种 runtime ownership/mapping 不自洽统一转换为
   `mapping_damaged`，避免其他 workflow 在不完整 ownership 上继续读写。

Restore 当场没有失败，是因为 `update_runtime()` 先校验修改前的 runtime，再由 callback 插入新
record 并直接写盘，没有对 callback 产生的最终 state 再做一次 validation。所以下一次 operation
重新调用 `read_runtime()` 时才发现无效 record。这一延迟暴露也是本 bug 需要回归测试覆盖的部分。

`requested_default` 是 Python runtime 的请求来源标记：`true` 表示创建或更新 install 时调用方
省略了 revision，`false` 表示调用方显式给出 commit、tag 或 branch。省略请求首次解析后同样会
被固定为 commit selector，因此不能仅从 `revision_selector` 区分 default intent 与显式 commit。
后续再次省略 revision 时，`ExternalService.install` 使用该 boolean 优先找到原 install，复用已经
固定的 selector/commit，而不是重新读取可能移动的 default branch。它不是 remote default branch
的当前状态，也不授权 refresh；`default_branch` 只保存首次解析来源的 provenance。

因此该字段虽然属于 Python internal runtime schema，却支撑 Architecture 要求的省略 revision
幂等 lookup 和 fixed-snapshot 语义，同时也是当前 runtime validator 的 required field。

端到端复现结果为：

| 步骤 | 可观察结果 |
|---|---|
| install + link 后移除 managed payload | durable presentation 保留，target 成为 missing。 |
| `external restore --apply` | item 返回 `restored`，payload 被重建。 |
| 检查 runtime install | `requested_default` 缺失。 |
| 立即执行 `external link-parse` | operation blocked，failure code 为 `mapping_damaged`。 |

这不是单纯内部字段差异：公开 restore 成功会产生实现自身无法继续读取的持久状态，并阻断
install、link、link-parse、worktree 等依赖 runtime 的后续 workflow，因此属于产品 bug。

事实入口：

- [restore realization](../doctidex-git/impls/python/components/external-presentation-and-mapping.md)
  在修复前记录该 limitation，现已描述修复后的 runtime provenance rebuild；
- [`external.py`](../../impls/libs/python/whero/doctidex/git/external.py) 的 `_restore_item` 构造
  runtime record；
- [`storage.py`](../../impls/libs/python/whero/doctidex/git/storage.py) 的 `_valid_install(...,
  portable=False)` 要求 `requested_default` 为 boolean；
- 修复前的
  [`test_link_restore_and_current_owner_parse`](../../impls/libs/python/tests/test_git_plugin.py)
  只断言 payload 和 symlink 恢复，没有在 restore 后再次读取 runtime，因而未捕获该问题。

## 2. 修复设计

Restore 写入 runtime install 前必须重建完整且可立即通过 `RootStorage.read_runtime()` 校验的
record。`requested_default` 从 portable default provenance 恢复：

- manifest `default_branch` 为 non-null 时，原 install 来自省略 revision 的 default intent，写入
  `requested_default: true`；
- manifest `default_branch` 为 null 时，原 install 使用显式 selector，写入
  `requested_default: false`。

该推导与当前 source resolution 和 Architecture 的 default provenance 定义一致。修复不增加
portable manifest 字段，不迁移 schema，不刷新 remote HEAD，也不改变 install ID、selector、
exact commit、source relation 或 restore publication 边界。

## 3. 实施影响

1. 修改 `impls/libs/python/whero/doctidex/git/external.py` 的 restore runtime-record construction，
   补齐 `requested_default`。
2. 在 `impls/libs/python/tests/test_git_plugin.py` 增加 restore 后 runtime read 与 `link-parse` 回归
   测试，并分别覆盖 default intent 与显式 selector 的 boolean 值。
3. 保留 `RootStorage` validator 的严格要求；不得通过放宽 validator、silent repair、private state
   edit 或跳过 runtime read 隐藏无效 record。
4. 修复完成后更新 Python Impls 中 external restore、physical runtime schema、recovery known
   limits 和 Architecture coverage，将该 material limitation 移除并链接测试证据。
5. Architecture、portable manifest schema、CLI/JSON contract、Published Skills 和 protocol 不需要
   行为变更；若实施中发现这一前提不成立，应先返回本 Requirement 讨论，不得扩大范围。

## 4. 依赖与历史边界

本 bug 是 [DX-REQ-0009](0009-architecture-and-details-maintenance-rules.md) 在 Python gap 重分类后
保留的唯一 material limitation 的后续修复。用户已明确授权在 `approved` 的 `DX-REQ-0009` 中
添加 follow-up 回链；该机械链接不重新打开或改变其状态，双向关系现已完整。

## 5. 验收标准

1. 对 default-intent direct install 执行 missing -> restore 后，runtime install 包含
   `requested_default: true`，`RootStorage.read_runtime()` 成功。
2. 对显式 revision direct install 执行同一流程后，runtime install 包含
   `requested_default: false`，且 selector 与 exact commit 不变。
3. Restore 后立即执行 `external link-parse` 能返回原 managed mapping，不再因本问题产生
   `mapping_damaged`；随后省略 revision 的 install lookup 仍复用原 default-intent install。
4. Existing complete、blocked item、batch partial success、manifest/cursor 和 link restore 行为没有
   回归；相关 Python tests 与 Ruff 通过。
5. Python Impls 不再把该问题列为 current material limitation，并能从 restore、runtime schema、
   recovery 和 coverage 页面追踪到修复与代表性测试。
6. 不放宽 runtime validator，不修改 Architecture、portable manifest schema、公开 CLI/JSON、
   Published Skills 或 protocol。

## 6. 实施进展

用户已于 2026-08-01 明确授权实施本 bugfix。当前按第 3 节范围修改 Python restore runtime-record
construction、回归测试与 Python Impls，未修改 Architecture、portable manifest schema、CLI/JSON、
Published Skills、protocol 或 runtime validator。

实施结果：

1. `ExternalService._restore_item` 以 `record.get("default_branch") is not None` 重建
   `requested_default`，其余 selector、exact commit、install identity 与 publication 边界不变。
2. `test_restore_rebuilds_requested_default_provenance` 覆盖 default intent 与显式 commit 两条路径，
   证明恢复后 runtime 可读、boolean provenance 正确、selector/commit 不变，且 remote HEAD 移动后
   的省略 revision 重试仍复用原 install；`test_link_restore_and_current_owner_parse` 增加 restore 后
   `link-parse` 的 available mapping 断言。
3. Python Impls 的 restore、physical runtime projection、recovery 与 coverage authority 已记录修复
   机制和代表性测试，不再保留该 material limitation。

验证结果：

| 检查 | 结果 |
|---|---|
| `.venv/bin/python -m pytest impls/libs/python/tests -q` | 通过。 |
| `.venv/bin/python -m ruff check impls/libs/python` | 通过。 |
| `git diff --check` | 通过。 |
| `.venv/bin/doctidex-git validate . --scope /docs --scope /impls --json` | 本次新增/修改文档无 finding；仍报告 5 个既存的根 `index.md` `link_annotation_invalid`，不属于本 bugfix 授权范围。 |

本 Requirement 的授权范围与验收标准已实现。用户于 2026-08-01 明确确认当前实现，状态更新为
`approved`，可进入 PR/MR。
