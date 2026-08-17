# 子需求 0021.7：现有 install 的 exact object 恢复

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0021.7` |
| 状态 | `implemented` |
| 日期 | 2026-08-05 |
| 所属大型 Requirement | [DX-REQ-0021](overview.md) |
| 来源 | 用户确认 branch/tag selector 的同一 stable install path 可以随 host checkout 对齐不同 manifest `resolved_commit`，并决定扩展 `external restore --install ID`，使已获网络授权的 agent 能处理 hook 的 `revision_not_found`；随后明确 install 是建立/更新 snapshot、restore 是恢复 manifest exact snapshot，二者不能互相替代，并决定 restore 直接完成 checkout、hook finding 路径再由 `hook --run` 最终确认。 |
| 问题关联 | `hook --run` 的 `revision_not_found` 是现有公开 failure；该恢复能力尚未单独创建 Issue。 |
| 影响范围 | doctidex-git Architecture CLI/JSON contract、`external restore`、hook finding/action、Maintenance Skill、Python external/hook tests 与 Python Impls。 |
| 当前 authority | [external restore CLI](../../doctidex-git/architecture/interfaces/cli.md#10-external-restore)、[hook CLI](../../doctidex-git/architecture/interfaces/cli.md#13-hook)与[操作安全](../../doctidex-git/architecture/operation-safety-and-recovery.md#1-调用计划与授权)。 |

## 1. 需求意图

branch/tag/default selector 的 `install_id` 由 root、canonical source 与 normalized selector identity 决定，而不是由
每次解析出的 `resolved_commit` 决定。因此 host 的两个版本化 manifest 可以在相同 install ID/stable path 下记录
不同精确 commit；`hook --run` 负责在 host checkout 后把现有 payload checkout 到当前 manifest commit。

若该 commit 不在本地 managed Git objects 中，hook 必须继续离线并保留 payload，返回 `revision_not_found`。但当用户
已授权网络访问时，agent 目前不能仅根据该公开结果调用一个命令安全补齐对象：现有 `external restore --install ID` 在
payload path 已存在且 HEAD 不同的情况下返回 `install_path_conflict`，只支持重建缺失 payload。

这里的恢复不等同于一次新的 install。设 versioned manifest 记录 branch `main` 当时固定的 `C1`，而 source 的
`main` 已移动到 `C2`：用户明确授权 `external install --branch main` 时，命令是在按本次 selector 建立或更新 snapshot，
可以产生 C2 并更新 manifest；用户要求 clone、clean 或 checkout 后回到当前 manifest 所声明的 C1 时，必须调用
`external restore`。后者只能使用 manifest 的 `resolved_commit`，不能重新解析 branch/tag/default。当前 local runtime
已记录 matching install 的同 key retry 仍复用该已有 fixed commit；这一幂等路径也不是 restore。

## 2. 解决方案

将现有 `external restore --install ID` 的 direct-install workflow 扩展为同一 exact checkout result 的三种现场：

| 现场 | dry-run / apply 行为 | result state |
|---|---|---|
| stable payload path 不存在 | 保持现有 exact restore：验证或取得 manifest commit，重建 payload 到稳定路径并重建必要 runtime record。 | `planned` / `restored` |
| payload path 存在、HEAD 已等于 manifest commit | 保持只读 no-op；不访问 network。 | `unchanged` |
| payload path 存在、是完整 clean managed direct worktree，但 HEAD 不等于 manifest commit | dry-run 验证 source 可取得该 exact hash；apply 在 source lock 下取得 exact object 后，直接 detached checkout 到 manifest commit。 | `planned` / `restored` |
| manifest 或 stable path 不可验证、path 不是该 install 的 managed worktree、payload dirty，或 exact hash 仍无法取得 | 不 fetch、不 checkout、不重建；保留现场并返回 item-level finding。 | `blocked` |

`restored`表示 stable payload 已在 manifest 的 exact commit：它既可表示重建缺失 payload，也可表示将一个已验证、clean
的 existing direct payload checkout 到该 commit；不再区分 object 获取与 checkout 的中间结果。此结果不替代完整 hook
reconciliation。正常 clone/clean recovery 在 restore 成功后完成；若 restore 的输入来自 `hook --run` 返回的
`revision_not_found`，agent 必须执行下面的 hook retry，确认 runtime provenance 与 dependency state。

### 2.1 调用链与公开 handoff

1. `hook --run --root ROOT --json` 对一个 direct item 返回 `state: blocked`、`revision_not_found`、精确
   `install_id` 和 manifest `resolved_commit`。
2. 在用户已授权网络访问的前提下，agent 运行：

   ```text
   doctidex-git external restore --install INSTALL_ID --root ROOT --dry-run --json
   doctidex-git external restore --install INSTALL_ID --root ROOT --apply --json
   doctidex-git hook --run --root ROOT --json
   ```

3. dry-run/ apply 只消费 selected owner root 的 versioned manifest record；agent 不需要 cache path、内部
   worktree registration、remote 名称或 branch/tag 当前值。apply 返回 `restored` 时，payload 已 checkout 到 manifest
   `resolved_commit`；第三步的 hook retry 是这条由 hook finding 开始的恢复链的强制最终确认，负责同步 runtime provenance
   并重判 dependency state。

hook 的 `revision_not_found` finding 必须携带足以执行此路径的 stable install ID 和 machine-readable recovery action；
Maintenance Skill 将此路径说明为“授权的 exact-object recovery”，而不是一般性 native Git fetch 建议。

## 3. Architecture 与实现影响

- 保持 Architecture 的 `external_restore` item state enum；`restored` 同时覆盖重建缺失 payload 与将 existing clean
  direct payload checkout 到 manifest exact commit。更新 `hook_run` finding/action handoff、network matrix 和 CLI examples。
- Python 先验证 manifest direct record、stable path、Git worktree identity、clean state、common object store 与该
  install/source 的一致性；不通过时保持现有 preserve-first blocked path。runtime 可以仍反映 host checkout 前的 commit，
  但不能阻止 exact checkout；由 hook finding 进入的调用链必须通过随后成功的 hook 依 manifest 同步它。验证必须防止把
  exact object fetch 写入 foreign worktree 或错误 source cache。
- apply 使用已有 exact-commit source retrieval primitive，限制为 manifest `source_url` 和 `resolved_commit`；不
  resolve default branch、不 follow moved tag/branch、不写 manifest/link/frontmatter，并在已验证的 clean managed direct
  payload 上直接 detached checkout。由 hook finding 进入的调用链随后必须运行 `hook --run`，不以 restore result 代替
  hook 对 runtime/dependency state 的最终确认。
- 在 `hook` item 中公开 recovery handoff，而非暴露 cache location；更新 Published Maintenance Skill 前必须遵守其
  skill-system Architecture 的阅读与验证规则。Python Impls 记录 `restored`/`blocked` 的物理边界与测试 evidence。

## 4. 验收标准

- 为 branch/tag selector 建立两个 host commits：相同 `install_id`、不同 manifest `resolved_commit`。第二个 hash
  未预先放入本地 managed object store 时，首次 hook 返回 item-level `revision_not_found` 且不修改 payload/runtime。
- 对同一 item，restore dry-run 验证 exact hash 可取得且不写入；apply 取得该 hash 后直接 checkout 到第二个 hash，返回
  `restored`，不改写 manifest、runtime link 或 durable symlink。随后必须进行的 hook retry 成功确认 runtime provenance
  与 dependency state。
- path 不存在时保留既有 `restored` 行为；HEAD 已对齐时保留 `unchanged`；dirty、foreign、damaged或 source access failure
  均为 `blocked` 并保留所有受影响路径。
- JSON result 使用现有的 `restored` 表示 exact checkout 已完成，并报告 network fact；agent 可仅依 hook item 的
  `install_id` 和 result actions 完成流程。Maintenance Skill、Architecture、Python Impls 与 tests 对此链路一致。
- 该能力不自动改变 DX-ISSUE-0004 的状态，也不将 branch/tag 当前 remote 指向解释为 snapshot provenance mismatch。
- 对 manifest 为 C1、source branch 已为 C2 且 local payload 缺失的场景，Architecture 与 Published Skill 明确要求：
  用户授权更新 snapshot 时可用 `external install --branch`，希望恢复当前 manifest 时只可用 `external restore`；后一条
  路径不得重新解析 branch/tag/default 或改写 manifest。

## 5. 实施状态

2026-08-05 已完成完整实施。`external restore --install ID` 现验证 existing direct payload 的 managed identity、clean
status 与 shared source object store，并在取得 manifest exact object 后 detached checkout；该分支不改写 runtime、
manifest 或 durable link。`test_restore_existing_direct_payload_checks_out_manifest_exact_commit` 覆盖 dry-run、apply、
现场保持与必须的 hook retry；Maintenance Skill、Architecture 与 Python Impls 已对齐。完整 Python tests、Ruff、全根
validation 与 `git diff --check` 均通过。
