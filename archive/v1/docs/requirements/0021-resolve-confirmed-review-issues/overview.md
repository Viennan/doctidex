# 需求 0021：解决 2026-08-05 全仓 review 的已确认问题

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0021` |
| 状态 | `implemented` |
| 日期 | 2026-08-05 |
| 来源 | 用户要求建立大型 Requirement 解决本轮全仓 review 的六个 Issue，并要求 Requirement 给出解决方案；随后用户明确将六个 Issue 全部标记为 confirmed，决定扩展 `external restore --install ID` 以恢复已有 install 缺失的 exact object，并澄清 `external install` 建立当前 snapshot、`external restore` 恢复 manifest exact snapshot 的命令边界。 |
| 问题来源 | [DX-ISSUE-0001](../../issues/0001-external-apply-stale-preconditions.md)、[DX-ISSUE-0002](../../issues/0002-validator-accepts-query-links.md)、[DX-ISSUE-0003](../../issues/0003-root-index-omits-github.md)、[DX-ISSUE-0004](../../issues/0004-hook-metadata-warning-unreachable.md)、[DX-ISSUE-0005](../../issues/0005-worktree-list-error-discriminator.md)、[DX-ISSUE-0006](../../issues/0006-root-index-stale-protocol-version.md) |
| 影响范围 | `spec/overview.md` 的实现解释、根 doctidex 导航、doctidex-git Architecture/Impls、Maintenance Skill、Python protocol validator、external/hook/worktree CLI、测试与公开 JSON contract。 |
| 实现授权 | 2026-08-05 用户明确授权按本记录实施全部子需求，包括必要的 Architecture、Impls、根导航、Published Skill、Python 代码、测试与验证；不授权改写 protocol 本身，亦不自动将任何 Issue 标为 `resolved`。 |

本大型 Requirement 将六个已确认的问题和一个由 hook 失败路径暴露的恢复能力拆为可独立验证的子需求。它们共享
“以既有 authority 为准、保留现场而不伪造成功”的原则，但不共享一个强制的代码发布步骤：根索引修复可以独立完成，
Python 行为修复需要同步更新其 Impls 和测试，公开 contract 的取舍须先由 Architecture 明确。

Issue 的 `confirmed` 只表示用户确认问题真实存在，不表示其已解决。本 Requirement 及全部子需求在完成授权的设计与
实现、验证并由用户接受前均保持 `draft`；任何子需求完成也不会自动把对应 Issue 改为 `resolved`。

## 1. 目标与边界

目标是让仓库自身重新满足其协议可达性和入口一致性，并让 Python variant 的可观察行为符合现有或经授权修订后的
Architecture：

1. `external install/link/restore/remove --apply` 不得因同 root 的过期 preflight 覆盖、删除或投影另一调用刚发布的
   managed state；`link` 的已确认问题与本轮确认的同类路径使用统一锁内重验方案。
2. validator 只把协议允许的 root-relative、root-internal relative 和 anchor-only 形式计入 file-path link 图。
3. `.github` 作为仓库根索引负责的内容具有符合协议的阅读入口。
4. `hook --run` 的 revision provenance contract 只承诺可由实际安全状态支撑、可测试的结果集合。
5. `worktree` command 在 runtime 损坏时保留自己的 `operation` discriminator。
6. 根入口对 current protocol 的版本陈述与 `spec/overview.md` 一致。
7. 当 hook 已确认 manifest 的 exact commit、但现有 direct install 缺少该 Git object 时，已获网络授权的 agent
   能只凭公开 `install_id` 走完 dry-run、精确对象获取和 hook retry，不必推导 cache 或 worktree 内部布局。

本 Requirement 不升级或重写 doctidex 协议，不改变已有 confirmed Issue 的事实或严重程度，不创建新的 Published Skill，
也不把 validator、hook 或 external 的内部实现细节提升为协议规则。

## 2. 总体解决方案

| 子需求 | 解决方向 | 主要产物 |
|---|---|---|
| [0021.1](01-external-link-apply-concurrency.md) | 把 `install/link/restore/remove` apply 的决定性 revalidation 移入同一 root mutation lock，并以当前 records、manifest、path、tracking 与 hidden state 作为写入前条件。 | Python external service、并发回归测试、Python Impls evidence。 |
| [0021.2](02-validator-query-link-classification.md) | 以统一 URL classification 排除含 query 的 Markdown hyperlink，使其不形成 protocol file-path edge。 | Python validator、protocol tests、Python Impls evidence。 |
| [0021.3](03-github-workflow-reachability.md) | 将 `.github` 作为原子工具目录从根索引显式暴露。 | 根 `index.md`、全根 validation evidence。 |
| [0021.4](04-hook-revision-provenance-contract.md) | 移除没有已定义安全触发条件的 metadata-warning public state，使 Architecture、实现、测试的 revision outcome 集合一致。 | Architecture CLI/JSON contract、Python Impls、hook tests。 |
| [0021.5](05-worktree-runtime-error-discriminator.md) | 让 shared runtime read 接收调用边界，并让 worktree surfaces 显式传入其 operation。 | Python storage/worktree service、CLI tests、Python Impls evidence。 |
| [0021.6](06-root-protocol-version-entry.md) | 将 root current-protocol 文案校正到 authority 的 `v1.1.0`。 | 根 `index.md`、文档一致性检查。 |
| [0021.7](07-restore-existing-install-object.md) | 扩展 `external restore --install ID`，为现有 clean direct install 取得 manifest 指定的 exact object 并直接 checkout；若恢复由 hook finding 触发，再由 hook 完成最终确认。 | Architecture CLI/JSON contract、Python external/hook service、Maintenance Skill、tests 与 Python Impls。 |

### 2.1 设计决定

- dry-run 仍不保留 lock reservation；只有 apply 必须在写入前重观测。并发修复不得把“后一调用也成功”作为目标，
  而应在其计划失效时保留当前现场并返回可处理的 blocked/conflict 结果。
- 0021.1 统一处理 `link` 的已确认 mapping race，以及专项 review 已验证的 install role/parent/trackability、restore
  stale-manifest 和 remove hidden-state race。它不把“无 matching local runtime 时按本次 selector 更新 snapshot”的
  install 语义误判为 conflict；0021.7 的 exact restore checkout 必须服从 0021.1 的 manifest/path final observation。
- 协议的 link 语义不因 Issue 0002 改变。`?query` 和 `path?query` 可以是普通 Markdown hyperlink，但不形成
  doctidex file-path edge；`#anchor` 仍是当前文档定位。
- `.github` 选择 `atomic-indexing`，因为其是 CI/tool configuration 目录且当前不含 doctidex `index.md` 或 `log.md`。
  根索引仍必须链接该目录本身，不能只加入 atomic declaration。
- Issue 0004 不应为使枚举值“可达”而捏造一个并不存在的安全 partial-alignment 状态。Architecture 已收窄 public
  contract，使 revision outcome 只保留可被实现和测试的 `complete`、`not_applicable` 与 item-level `blocked`；未定义
  warning field 已从 current Architecture、Python 与 Impls 移除。
- Issue 0005 只改变错误 envelope 的 command identity，不吞掉 `mapping_damaged`、`affected`、恢复 action 或
  preserve-first 行为。
- `external restore` 已有 `--install ID` filter，但当前只恢复缺失 payload。0021.7 将把它扩展为精确 direct restore：
  对现有、完整且 clean 的 direct install，取得 manifest `resolved_commit` 后直接 checkout；它不重写 manifest/link，也不
  重新解析 branch/tag。若该 restore 是处理 hook 的 `revision_not_found` finding，agent 必须再运行离线 `hook --run`，
  由 hook 完成既有 runtime provenance 与 dependency reconciliation 的最终确认。
- `external install` 是基于调用本次 source/selector 建立或更新 direct snapshot 的显式写入；没有当前本地 matching
  runtime install 时，它可以解析 branch/tag/default 的当前值并更新对应 manifest entry。`external restore` 则只以当前
  versioned manifest 的 exact commit/path 为恢复 authority，不能用 install 替代。当前本地已有 matching runtime install
  的同 key retry 仍复用其 fixed commit，不刷新 moving ref。

## 3. 子需求导航与聚合

| ID | 子需求 | 对应 Issue | 状态 |
|---|---|---|---|
| `DX-REQ-0021.1` | [external dry-run/apply 的锁内重验](01-external-link-apply-concurrency.md) | [DX-ISSUE-0001](../../issues/0001-external-apply-stale-preconditions.md)；本轮新增同类发现未创建 Issue | `implemented` |
| `DX-REQ-0021.2` | [validator 的 query link 分类](02-validator-query-link-classification.md) | [DX-ISSUE-0002](../../issues/0002-validator-accepts-query-links.md) | `implemented` |
| `DX-REQ-0021.3` | [`.github` workflow 的协议可达性](03-github-workflow-reachability.md) | [DX-ISSUE-0003](../../issues/0003-root-index-omits-github.md) | `implemented` |
| `DX-REQ-0021.4` | [hook revision provenance contract 对齐](04-hook-revision-provenance-contract.md) | [DX-ISSUE-0004](../../issues/0004-hook-metadata-warning-unreachable.md) | `implemented` |
| `DX-REQ-0021.5` | [worktree runtime 错误的 operation 判别](05-worktree-runtime-error-discriminator.md) | [DX-ISSUE-0005](../../issues/0005-worktree-list-error-discriminator.md) | `implemented` |
| `DX-REQ-0021.6` | [root current-protocol 版本入口](06-root-protocol-version-entry.md) | [DX-ISSUE-0006](../../issues/0006-root-index-stale-protocol-version.md) | `implemented` |
| `DX-REQ-0021.7` | [现有 install 的 exact object 恢复](07-restore-existing-install-object.md) | hook `revision_not_found` 的 agent-facing recovery gap；未创建 Issue，等待用户决定是否单独记录。 | `implemented` |

全部子需求均已完成授权实现和验证，因此 overview 为 `implemented`。只有用户明确批准全部子需求与 overview 后，
才可进入 `approved`；对应 Issue 的 `resolved` 状态仍需逐项授权。

## 4. 实施顺序与跨层跟踪

1. 先用 Architecture authoring flow 处理 0021.4 的 public contract 收窄和 0021.7 的 restore result/agent recovery
   contract；0021.1 复用既有 Architecture 的 concurrency/operation authority，并为 0021.7 的 root-locked final
   manifest/path observation 提供共同边界，无须借此重写共同 contract。
2. 依次实现并测试 0021.1、0021.2、0021.4、0021.5 与 0021.7；0021.7 的 restore implementation 必须在 0021.1
   的 revalidation design 下完成。每项完成后更新 Python Impls 的 source/test evidence 和
   已知限制，不能继续把已解决缺口留为 current limitation。
3. 处理 0021.3 与 0021.6 的根索引编辑，并以全根 `doctidex-git validate . --json` 验证。0021.3 是当前唯一
   已知 deterministic protocol finding；0021.6 需要直接比对入口文字与 authority header。
4. 最后运行完整 Python tests、Ruff、全根 validator 和相关文档链接检查。只有各子需求的验收标准都满足，才记录
   其 `implemented`；Issue 的 `resolved` 状态仍需要用户针对每个 Issue 的明确授权。

## 5. 总体验收标准

- 六份 confirmed Issue 各有一个对应的、可独立运行的验收证据；不得以聚合“全绿”掩盖单项缺口。
- Python 行为变更同时具有直接回归测试和更新后的 Impls evidence；无需改动的 Architecture 必须保持为现行 authority，
  所有 public contract 变更先由 Architecture 确定。
- `doctidex-git validate . --json` 不再返回 `.github`、`.github/workflows` 或
  `.github/workflows/python.yml` 的 `path_unreachable`，且不因该修复引入新的 protocol finding。
- 根入口与 `spec/overview.md` 对 current protocol 使用相同的版本值 `v1.1.0`。
- 已获网络授权的 agent 仅使用 hook item 的 `install_id` 与公开 `external restore` contract，即可为现有 clean direct
  install 补齐 manifest exact commit 并安全重试 `hook --run`；全程不要求 cache path、Git worktree registration 或
  source URL 的内部推导。
- Architecture 和 Published Skill 明确区分“用户授权按 selector 建立/更新 snapshot”的 install 与“按当前 manifest
  exact commit 恢复”的 restore；agent 在后者场景不得以 branch/tag/default install 代替 restore。
- 所有文档逻辑以中文可读地组织，所有 Requirement/Issue 链接可达，并保留本记录的需求决策、实现 evidence 与
  Issue 处置边界。

## 6. 实施证据

2026-08-05 已完成代码、Architecture、Python Impls、Published Maintenance Skill 与根导航更新。`pytest -q
impls/libs/python/tests`、`ruff check impls/libs/python`、`doctidex-git validate . --json` 与 `git diff --check`
均通过；全根 validation 保留五项既有 `unsafe_scope_review` semantic candidates，未返回 protocol finding。六个
confirmed Issue 保持 `confirmed`，本 Requirement 不代替用户作 `resolved` 或 `approved` 决定。
