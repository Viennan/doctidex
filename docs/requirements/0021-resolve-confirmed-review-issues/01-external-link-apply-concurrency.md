# 子需求 0021.1：external dry-run/apply 的锁内重验

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0021.1` |
| 状态 | `implemented` |
| 日期 | 2026-08-05 |
| 所属大型 Requirement | [DX-REQ-0021](overview.md) |
| 对应 Issue | [DX-ISSUE-0001](../../issues/0001-external-apply-stale-preconditions.md) |
| 影响范围 | `ExternalService.install/link/restore/remove`、root runtime/manifest、presentation symlink、dependency hidden payload、external CLI regression tests 与 Python Impls。 |
| 当前 authority | [产品与用户 surface](../../doctidex-git/architecture/product-and-user-surfaces.md#5-可观察结果授权与非目标)、[操作安全与恢复](../../doctidex-git/architecture/operation-safety-and-recovery.md#1-调用计划与授权)、[external snapshot](../../doctidex-git/architecture/external-snapshots-and-presentations.md#1-用户问题与共同生命周期) 与 [CLI](../../doctidex-git/architecture/interfaces/cli.md#6-external-install)。 |
| 关联 | 已确认的 [DX-ISSUE-0001](../../issues/0001-external-apply-stale-preconditions.md) 是 `link` 范围的已记录问题。本次专项 review 还验证 `install`、`restore`、`remove` 的同类路径；用户尚未授权为这些新增发现创建 Issue，故本子需求直接统一记录其修复设计。[现有 install 的 exact object 恢复](07-restore-existing-install-object.md) 的实现必须同时满足本页的 `restore` 重验边界。 |

## 1. 需求意图

`dry-run` 只提供一次可审阅的观察，不保留 root、source、manifest、target 或 dependency parent 的 reservation。因而所有
`external ... --apply` 都必须在实际写入前重新观察会决定其安全性的当前状态；后获得 mutation lock 的调用不得把锁外
计划当作仍然成立的事实。

本子需求首先解决两个 `external link --apply` 竞争同一 target 时的已确认问题：受管 presentation 的 symlink、runtime
link record 和 versioned manifest link record 必须始终描述同一 install/source。专项 review 还确认下列同根因场景：

| 命令 | 过期观察与可见错误状态 | 必须保留的当前状态 |
|---|---|---|
| `external link` | 两个不同 direct source 都在 target 空闲时完成 preflight；先执行者建立 A 的 symlink，后执行者按旧计划写 B 的 runtime/manifest mapping。 | A 的 symlink 和两份 A mapping；后者返回 conflict/blocked。 |
| `external install` | direct install 与带 `--dependency-of` 的 install 同时从“child 不存在”计划；direct 先发布，dependency 调用随后用旧 role 覆写 runtime，而 manifest 仍是 direct。两个 dependency parent 也可能相互丢失 parent edge。另一个 parent 可在 child apply 取得 root lock 前被 remove。 | current direct role 不能降级；current parent edge 的并集不能丢失；已不存在或不完整的 parent 不能成为新 child record 的 parent。 |
| `external install` | preflight 确认 manifest 可 track 后，host 的 `.gitignore` 被另一调用或用户改为忽略 manifest；apply 仍写入它，portable recovery contract 因而无法被 Git delivery。 | 新的 ignore state；apply 不写被忽略的 manifest。 |
| `external restore` | 一次 apply 的分页读取时 manifest 对同一 stable install ID 记录 `C1`，在该调用取得 root lock 前 host checkout 改为 `C2`；apply 仍 materialize `C1` 并写入 `C1` runtime，却保留 `C2` manifest。 | 当前 manifest 的 `C2` record；本次 item 返回 blocked/conflict，调用方重做 dry-run。 |
| `external remove` | remove 在 dependency 尚为 complete 时通过 reference-free preflight；hook 随后将它移动到 `.hidden/<id>` 并标为 hidden；remove 的锁内 preflight 虽读到 hidden，仍继续删除 hidden payload/runtime。 | hidden dependency 的 payload、runtime 与 hook reconciliation evidence；返回 `preserved_hidden`。 |

### 1.1 可复现案例与当前错误状态

以下案例描述的是当前 Python 实现在两次 observation 之间发生合法并发状态变化时的结果。这里的“暂停”可以由测试的
barrier 或 source/root lock 等待形成；它不是要求产品提供跨 invocation reservation。

#### 1.1.1 `external link`：symlink 与 durable mapping 指向不同 install

**前提。** owner root `R` 中已有两个 complete direct install：`I-A` 的工作目录为 `source-A`，`I-B` 的工作目录为
`source-B`。`R/external/api` 尚不存在，runtime 与 manifest 都没有 `links["external/api"]`。

两个调用几乎同时完成锁外 preflight：

```text
doctidex-git external link source-A external/api --root R --apply
doctidex-git external link source-B external/api --root R --apply
```

**交错。** A 先取得 root lock，建立 `external/api -> source-A` 的相对 symlink，并在 runtime/manifest 发布 `I-A`
mapping。B 随后取得同一 lock，但仍沿用“target 不存在、两个 records 都不存在”的旧观察；它看到 path 已是 symlink 时
跳过创建，却继续把两个 durable record 写为 `I-B`。

**当前错误状态。** B 仍可能报告 apply 成功，而现场变为：

```text
filesystem:   R/external/api -> <relative path to source-A>
runtime.json: links["external/api"].install_id == I-B
manifest.json: links["external/api"].install_id == I-B
```

随后以 B 调用 `external rebind` 或任何需要证明 presentation 的操作，会发现实际 symlink 不等于 B mapping，返回
`mapping_damaged` 并保留现场；调用方不能通过正常 surface 管理这条刚被报告成功的 link。

**目标结果。** B 在 lock 内观察到 A 的新 mapping/target 后返回 `blocked` 或 conflict，A 的三份事实保持一致。相同
source/target 的重复调用仍为幂等成功；要切换 A 到 B 必须使用 `external rebind`。

#### 1.1.2 `external install`：direct 降级和 dependency parent 丢失

**前提。** `P1`、`P2` 是 `R` 内 complete install；同一 child source/selector 对应稳定 ID `C`，而 `C` 当前不存在。
由于 install ID 由 root、canonical source 与 normalized selector 决定，以下三个调用都指向同一 stable payload path：

```text
doctidex-git external install --url CHILD --branch main --root R --apply
doctidex-git external install --url CHILD --branch main --dependency-of P1 --root R --apply
doctidex-git external install --url CHILD --branch main --dependency-of P2 --root R --apply
```

**交错 A：role。** 普通 direct install 和带 `--dependency-of P1` 的调用都先观察到 `C` 不存在。direct 调用先经过
source/root lock，发布 `role: direct` 的 runtime record 与 portable manifest entry。dependency 调用随后通过同一 source
lock；payload HEAD 已相同，但它没有在 root lock 内重算 `role`，于是按旧计划写入 `role: dependency, parents: [P1]` 的
runtime record，且不删除已有 direct manifest entry。

**当前错误状态 A。** manifest 仍表明 `C` 是 direct，而 runtime 表明它是 dependency。`external link` 会依据 runtime
拒绝这个本应可呈现的 payload 为 `dependency_not_recoverable`；`external remove` 又会因 dependency runtime 不应有 portable
record 而得到 `mapping_damaged`。这不是用户主动选择降级，而是两个成功返回的 apply 共同制造的不一致状态。

**交错 B：parent。** 两个 dependency 调用分别在 `C` 不存在时计算 `parents: [P1]` 与 `parents: [P2]`。先写入的 parent
edge 会被后写入者的旧数组替换，最终只剩一个 parent。另一种等价交错是 child 已在锁外确认 `P1` complete，但
`external remove P1 --apply` 使用 P1 自己的 source lock 在 child 取得 root lock 前完成；child 仍发布指向不存在 P1 的
parent edge。

**当前错误状态 B。** runtime schema 只要求 parent 为非空 ID，不验证它仍存在，因此丢失 edge 或悬空 edge 可以被写入。
后续 hook reconciliation 无法从真实 parent forest 得到所需 provenance，只能保留/阻断 child，且没有正常命令能从结果
推断原先被覆盖的 parent。

**目标结果。** root lock 内以 current record 重新决定结果：已是 direct 的 `C` 保持 direct，新的 dependency request 只合并
去重 parent edge；两个有效 parent 都保留。若 `P1` 已不存在、hidden 或不 complete，child 返回
`dependency_parent_invalid`，不创建 payload、runtime、manifest、index 或 `.gitignore` 的 root-owned effect。

#### 1.1.3 `external install`：manifest trackability 在 apply 前失效

**前提。** `R/.doctidex/git/manifest.json` 起初没有被 host Git ignore。install 在锁外通过 manifest trackability 检查并
开始为新的 direct install 取得 source cache。

**交错。** 在该调用等待 source lock、fetch 或其它可控 barrier 时，另一个授权操作或用户编辑 host `.gitignore`，使
`/.doctidex/git/manifest.json` 成为 ignored path。之后 install 取得 root lock；当前实现会保留这条 ignore rule、执行
host layout，然后仍写入 manifest。

**当前错误状态。** 调用可报告 `external_install` 成功和 manifest changed，但 `git status` 不会把新的 portable recovery
manifest 作为可交付内容呈现。该 root 一旦 clone/clean 或 checkout 到另一主机，就没有可版本化的 direct snapshot record
可供 restore 消费；用户先前对“manifest 必须可 track”的审阅条件已失效。

**目标结果。** 在实际写 manifest 前重查 host Git trackability。发现已 ignored 时返回既有
`git_exclusion_conflict` 并保留用户的 `.gitignore`，不写 manifest。此规则不限制“没有 matching local runtime install
时，普通 install 可以按本次 selector 更新 snapshot”的既有行为；它只要求该更新仍然可被 Git track。

#### 1.1.4 `external restore`：旧 manifest record 被 materialize 到新 checkout

**前提。** 当前 host checkout 的 manifest 对 stable ID `I` 记录 branch provenance 和 fixed commit `C1`；`I` 的 direct
payload 与 runtime 均不存在。调用 `external restore --install I --root R --apply` 开始后，先在分页阶段读取 `C1` record，
并在取得 source cache/exact object 后尚未取得 root lock。

**交错。** 同一 host repository 在这个窗口 checkout 到另一个已审阅版本；新版 manifest 对相同 stable ID `I` 记录
`resolved_commit: C2`。stable ID 不含每次解析所得 commit，因此该变更是一个合法的 host checkout，而不是 manifest
schema 损坏。restore 随后取得 root lock，却只把最新 manifest 传给 runtime link projection，不比较
`installs[I]` 是否仍是先前的 `C1` record，继续创建 C1 worktree 并写 C1 runtime。

**当前错误状态。** apply 返回 `restored`，且结果中的 item/recovery-manifest identity 都来自旧观察；实际 filesystem 与
runtime 是 C1，versioned manifest 已是 C2。后续 hook 会以 C2 重新对齐；依赖 runtime/manifest 一致的 link、remove 或
rebind 则只能报告 mapping damage 或恢复阻断。独立的 dry-run 后重新执行全新的 apply 不复用 dry-run record；风险在于
上述单个 apply invocation 自己的读锁间窗口。

**目标结果。** root lock 内发现 current `installs[I]` 不再等于本次列表页的 portable record 时，不创建或 checkout payload，
也不更新 runtime；本 item 返回 `blocked`/conflict 并要求从新的 manifest 重新 dry-run。0021.7 对 existing clean payload
的 exact checkout 使用同一检查，因此不会在 C1/C2 checkout 之间绕过此约束。

#### 1.1.5 `external remove`：hook 刚隐藏的 dependency 被删除

**前提。** dependency `D` 当前为 `managed_state: complete`，normal install path 存在，且 remove reference scan 没有发现
指向 D 的 presentation、Markdown、symlink 或其它 child parent edge。`external remove D --root R --dry-run` 因此返回
`planned`；一个随后开始的 apply 也先以 complete record 通过锁外 preflight。

**交错。** 在 remove 取得 source/root lock 前，`hook --run` 判定当前 checkout 无法安全证明 D 的 revision provenance。
hook 取得同一 source/root lock，将 payload 移至 `/.doctidex/git/installs/.hidden/D`，并把 runtime record 改为
`managed_state: hidden`。remove 随后取得锁并重新运行 `_remove_preflight()`，所以它能读到 hidden record 与新的 hidden
path；但现有代码只在锁外入口处理 hidden，锁内仅再次检查 references，随后删除该 path 和 runtime record，最后报告
`removed`。

**当前错误状态。** hook 为下一次 reconciliation 保留的 payload、parent/Git evidence 与 hidden runtime record 全部消失。
dependency 没有 portable manifest entry，后续 hook 不能把这个已经被删除的 evidence 当作可 unhide 的现场重新判断；一次
remove 的成功结果因此撤销了另一次成功 hook 所作的 preserve-first 决定。

**目标结果。** final preflight 读到 hidden dependency 时，apply 直接返回 `preserved_hidden`，`changed` 和
`planned_changes` 均为空；只有 hook 之后的明确 reconciliation 才能改变 hidden lifecycle。

这不是要求跨两次 invocation 保持 transaction，也不要求 apply 回滚 source cache 中已经安全取得的 Git object。要求仅是：
在 root-owned filesystem、runtime、manifest、mapping 或 dependency state 已变化时，plugin 不能再用失效计划成功发布，
而应按当前可证明状态完成、合并或保留并报告。

## 2. 解决方案

保留 dry-run 的输入检查、网络/对象可用性检查和计划输出，但将最后决定 root-owned publish 是否仍可进行的事实收敛到
既有 `source mutation -> RootStorage.mutation()` 顺序的临界区。source lock 外已经得到的 fixed commit 可以继续作为
本次 apply 的 source fact；root lock 内不得捕获或复用旧 runtime、manifest、parent、target、tracking 或 path 观察。

1. **共用 final observation。** 为每个命令建立可同时供 dry-run 和 lock 内 apply 使用的 observation helper。apply 取得
   root lock 后，先重读当前 runtime、required manifest、受影响 filesystem path、host Git tracking 与命令专属 state；
   在所有可阻止 root publication 的检查完成前，不得创建 payload、symlink、runtime/manifest entry、index declaration 或
   `.gitignore` effect。
2. **`link`。** 按原始 source directory 与 target input 重读 direct-install record、target、responsible
   index/frontmatter ownership 和 tracking。重建 expected mapping，验证 runtime/manifest 同 target record 彼此一致，且
   target 要么不存在、要么是同一 mapping 的相对 symlink。foreign、overlap 或新发布 mapping 使本次 apply
   conflict/blocked；不同 source 仍只能通过显式 `rebind` 替换。
3. **`install`。** 在 root lock 内重读 exact install record 与可选 dependency parent，重新决定 role、parent 集合和
   manifest inclusion。direct 永不降级；并发 parent additions 合并为去重集合；若本次 parent 已不存在或不 complete，
   返回 `dependency_parent_invalid`，不发布 child payload/record。写 direct manifest 前再次确认 manifest 可 track。
   这不改变既有边界：**没有** matching local runtime install 时，用户明确执行的 install 仍可按本次 branch/tag/default
   selector 建立或更新 direct snapshot，即使 versioned manifest 有相同 stable install ID；这不是 restore conflict。
4. **`restore`。** 每个 apply item 在 root lock 内重新读取 required manifest，证明 selected portable record 仍等于本次
   列表页读取的 record，且 stable path 的 missing 或 existing-payload facts 仍可安全处理。record 或 path 变化时该 item
   返回 blocked/conflict，不能 materialize 旧 commit 或把旧 runtime projection 写入新 manifest state。[现有 install 的
   exact object 恢复](07-restore-existing-install-object.md) 新增的 existing-payload checkout 分支适用同一 final
   observation，而不形成绕过。
5. **`remove`。** 将 hidden preservation 作为 final preflight 的分支，而不是只在 lock 外决定。若重读后为 hidden
   dependency，直接返回 `preserved_hidden`，不删除 `.hidden` payload、runtime record 或其 reconciliation evidence；
   target/reference 仍在 lock 内重扫。
6. **guarded publication 与结果。** runtime/manifest 的每个 replace/delete 都比较仍是刚读取的值。不能证明时返回该
   command 的 blocked/conflict result，给出实际 `affected`/preserved evidence；只把已确认的物理效果放入 `changed`。
   未变化的完全相同 mapping/record 保持幂等语义。

该方案不建立 dry-run reservation，也不承诺对任意 native Git/user process 建立全局 transaction。它保证 plugin 在自己的
root mutation lock 中不会把已过期的 managed-state preflight 当作后续成功写入的依据。

## 3. 实现与文档影响

- 在 Python `external.py` 中提取 command-specific、可由 dry-run 与 lock 内 apply 共享的 final-observation helpers，
  避免两套 target/mapping/install/restore/remove 规则漂移；实际 publish 必须使用 lock 内结果，而非闭包捕获的锁外
  `runtime`、`manifest`、`parents`、path 或 `expected_mapping`。
- `install` 保持 source resolution 和 stable install-ID semantics，但把 role/promotion/parent merge、manifest trackability
  和 root publication order 建立在 current root state 上。`restore` 的实现与 0021.7 协调：前者定义 stale-manifest
  preserve boundary，后者定义 existing clean payload 的 exact checkout。
- 调整 runtime/manifest 更新顺序时保持 `mapping_damaged`、`install_damaged`、hidden preservation 与 partial-effect
  reporting 的 preserve-first 语义；不得把不一致状态“修好”为另一调用选择的 source/commit，也不得把已确认写入隐去。
- 在 Python Impls 记录各命令的 lock-internal revalidation、未覆盖的 `worktree close` preflight limit 与确定性测试证据。
  Architecture 已规定 apply revalidate concurrency condition，不需要因实现补齐而改变其共同 contract。

### 3.1 专项审计边界

本轮已审计所有当前具有 `--dry-run | --apply` 的写入路径。`rebind` 与 `unlink` 已在 root mutation lock 内重跑决定性
preflight，并对 runtime/manifest entry 做 guarded comparison；`cache clean` 在 source boundary 内再次分类 linked
worktrees，分类变化时返回 `cache_cleanup_conflict`。这些路径不并入修复范围。`worktree close` 没有 dry-run/apply
surface，且 Python Impls 已明确不声称其 preflight 会在 lock 内重验；它是现有证据边界，不在本次专项 Requirement 中
作为同类 finding 处理。

## 4. 验收标准

- 使用可控 barrier 或等价 test seam 让两个不同 direct source 在同一 target 的 preflight 后交错 apply：一个调用可
  发布，另一个必须 blocked/conflict；最终 symlink、runtime 和 manifest 三者的 install ID/source 一致。target 已被创建、
  重绑定或占用时，`link` 不删除、不替换、不改写对方 records。
- 两个同 source/selector 的 install 分别请求 direct 与 dependency，或分别请求不同 complete parents 后交错 apply：
  最终 direct 不降级、manifest/runtime 一致、parent edge 去重合并。parent 在 child final observation 前被 remove/hidden
  时，child 返回 `dependency_parent_invalid` 并不 materialize root-owned child state。
- manifest 在 install preflight 后变为 host Git ignored 时，apply 返回 trackability conflict，不写 manifest；没有
  matching local runtime install 的显式 selector install 仍可按当前 selector 更新 manifest snapshot，防止将此修复误收紧为
  restore-only 行为。
- manifest 同一 stable install ID 从 `C1` checkout 为 `C2` 后，旧 restore page/apply 不能创建 `C1` payload/runtime；
  item 返回 preserved blocked/conflict 并要求重新 dry-run。0021.7 的 missing-payload 与 existing-clean-payload checkout
  两个分支均覆盖该交错。
- hook 在 remove preflight 后将 dependency 隐藏时，remove apply 返回 `preserved_hidden`，hidden payload/runtime 保持不变。
- `rebind`、`unlink` 与 `cache clean` 的既有重验回归继续通过；相关 Python external/hook/cache tests、Ruff 与 Python Impls
  evidence 通过，且 Impls 不再把本页覆盖的命令表述为未证明的并发保证。

## 5. 实施状态

2026-08-05 已完成实施。`ExternalService` 在 root mutation 内重读 install role/parent、manifest、target、tracking、
restore selected record 与 hidden state，并以当前 record 作 runtime/manifest guarded publication；host layout 位于所有可预见
blocking precondition 之后。`test_git_plugin.py` 覆盖 stale target publication、direct promotion/parent merge、parent 被删除、
manifest tracking 失效、stale manifest restore 与 hook-hide/remove 交错。完整 Python tests、Ruff、全根 validation 与
`git diff --check` 均通过。本状态不创建新 Issue，也不改变已确认 Issue 的状态。
