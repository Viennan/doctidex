# 工作树（worktree）与共享缓存

本页定义 writable maintenance worktree、其 runtime record 和 shared source cache 的共同语义。它们
解决的不是普通阅读，而是让调用方在不污染受管 read-only snapshot 的前提下维护指定 source/revision，
并在不误删其它 root 所用 Git objects 的前提下执行显式 cache cleanup。

## 1. 用户表面与边界

当前 host working tree 已是可写现场且目标就是当前 commit 时，human/agent 优先使用 native Git；
`worktree open` 是需要隔离、另一个 source/revision 或用户明确要求独立现场时的可选能力。它不
创建 nested checkout，也不成为发布/交付网关。

| Operation | input / default | result / safety boundary |
|---|---|---|
| `worktree open SOURCE [REVISION]` | SOURCE 可为 managed path、working tree、bare Git dir、gitfile 或 URL；revision 解析为 exact base commit。 | 在 selected owner root 内创建 detached writable artifact；每次成功创建新 ID，不是 idempotent reuse。 |
| `worktree list` | 可选 source/worktree filter、bounded pagination。 | 列出 current record 与 `clean`/`changed`/`unavailable`；cursor opaque。 |
| `worktree close WORKTREE` | 只接受 list/result 返回的 exact path。 | clean 才可关闭；changed/unavailable 一律保留并要求 native Git/用户决定。 |
| `cache clean --url URL` | exact absolute local locator 或 remote URL；默认 dry-run。 | 一个 shared source 的 planned/removed/preserved/blocked result。 |
| `cache clean --auto` | 默认 dry-run；enumerates recognized cache candidates。 | 每一 item 独立结果；其它 eligible item 不因某个 blocked item 回滚。 |

cache clean 面向 human/program operator，不由当前 Published Skills 路由。close、restore、install、
普通读取和 hook 都不会隐式 clean cache。

## 2. 运行时工作树记录

`runtime.json.worktrees` 是 owner-local configuration；每个 object key 和 `worktree_id` 都是相同
non-empty opaque ID。它与 `installs`/`links` 共用 `schema_version: "1.0"`，但由本页拥有 worktree
option 的 meaning。一个 Architecture reader 在现场发现它时必须逐项理解：

| Option | meaning / allowed value | user-surface effect 与 incoming rule |
|---|---|---|
| `worktree_id` | opaque record key。 | 关联 `root_internal_path`，不从值推断 source。 |
| `source_kind` | `managed_path`、`url`、`working_tree`、`bare_gitdir` 或 `gitfile`。 | 解释 SOURCE 怎样被分类；影响 source identity/provenance，不改变 CLI source input contract。 |
| `source_identity` | non-empty variant-local equality identity。 | lock/cache/reuse comparison；另一个 variant 可转换或重新观察，不能把它显示为 public source URL。 |
| `source_url` | sanitized public locator 或 `null`。 | 可供 user-visible result/diagnostic；不包含 credential。 |
| `gitdir` | source object repository/common Git dir 的 local locator。 | 证明 native Git source；不是 stable program API，无法验证时 worktree unavailable/preserve。 |
| `revision_selector` | `{kind: commit\|tag\|branch, value}`。 | 记录 user requested revision provenance。 |
| `base_commit` | 40 或 64 lowercase hexadecimal commit ID。 | writable worktree detached base；是 exact lifecycle identity。 |
| `root_internal_path` | `/.doctidex/git/worktrees/<worktree_id>`。 | owner-root logical location，与 actual path 的 handoff mapping。 |
| `worktree_path` | current host local path。 | 实际 writable artifact path；可能因 move/delete 变 unavailable，不可从 root-internal path 单独重建。 |
| `repository_relative_path` | `.` 或 normalized source-repository relative path。 | `working_path` 在 worktree 内的 user task location。 |

当前 record 的 ID/path/selector/base commit 或 schema 不能验证时，incoming variant 不得删除它来获得
clean state。它保留 record/physical evidence，报告 migration or `worktree_unavailable`；一个能证明同一
source/base commit 的 variant 可以转换为 own local representation，但须保留 user changes 与 observable
working path semantics。

## 3. 可写工作树生命周期

`worktrees/<id>/` 是 owner root 内的 writable managed artifact。它不是 install payload，也不是
durable presentation；它可以有 Git changes，因而任何 cleanup 都以保留优先。

| 状态 | 观察条件 | close / recovery rule |
|---|---|---|
| `clean` | path 与 Git metadata 可用，`git status` 无 changes。 | exact `worktree close` 可以移除 native worktree registration 与 runtime record。 |
| `changed` | path 可用但有 Git changes。 | 返回 `worktree_changed`、保留全部现场；user 用 native Git deliver/restore/retain 后再决定。 |
| `unavailable` | path 不存在、Git metadata 不能安全读取，或 record 不能证明可关闭。 | 返回 `worktree_unavailable`、保留 runtime record 和可定位 evidence；不得自动清理 stale record。 |
| orphan physical worktree | Git/path 存在但没有 matching managed record。 | 不是 doctidex-git 可关闭 target；保留并由 native Git/operator 诊断。 |

这里的 unavailable preserve rule 是当前共同行为。它避免一个 variant 将另一个 variant 的不完整
publication、moved path 或 user data 当成 stale metadata 删除。UUID strategy、Git worktree command、
status probe timing 和 runtime publication order 不改变上表的 user surface，属于 Impls。

## 4. 共享来源缓存与清理

source cache 是 user-cache 中按 source identity 共享的 bare Git object artifact。它可以被多个 owner
root 的 install 或 URL worktree 使用，因此不属于任何一个 root 的 deletion lifecycle。其 source ID、
directory path、hash、bare layout、lock name 和 enumeration algorithm 是 variant-specific；但 reader 在
工作现场看到它时必须知道它不是 config file、不是 payload，也不能因单个 root state 推断可删。

| cache result state | meaning | operator action |
|---|---|---|
| `planned` | dry-run 确认没有 valid linked worktree，apply 前仍会重判。 | 获得 delete authority 后以同 URL/auto intent apply。 |
| `removed` | apply 后缓存已删除。 | 不把 empty `changed` 当作未完成；后续需要时可重新取得 source。 |
| `preserved` | 至少一个 valid linked worktree 仍使用该 source。 | 保持 cache；结束所有有效 worktree 后再 dry-run。 |
| `blocked` | cache/Git registration 无法安全分类、并发变化或 candidate 消失。 | 完整保留，使用 native Git/等待/重观测，不能强制 remove。 |

`--auto` 只处理当前 variant 识别的 cache candidates，并逐项返回 opaque ID 和 count；它不把 private
cache path/source URL 泄露为 program contract。另一个 variant 若不兼容该 cache layout，可以保留它
并使用 own cache，或提供明确 migration/cleanup operator flow；它不能把未理解的 bare repository 删除。

## 5. 接手、并发与非目标

incoming variant 的 handoff 顺序是：读取 `runtime.worktrees` 的 semantic fields，检查 actual path/Git
availability，保持 changed/unavailable evidence，再决定直接使用、convert、native handoff 或 blocked。
cache 只在 explicit cleanup surface 依 Git registration eligibility 处理。source/network/lock conflict、
interruption 与 partial publication 的通用处理见 [operation safety](operation-safety-and-recovery.md)。

本页不规定 worktree ID generation、bare cache hash、file locking、Git registration parsing、status
algorithm 或 delete syscall。这些 execution details 不影响独立 variant 正确实现上表的 user-visible
worktree/cache behavior，故保留在 Impls/source。
