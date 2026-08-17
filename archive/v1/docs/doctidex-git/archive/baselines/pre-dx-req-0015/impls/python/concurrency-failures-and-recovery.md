# 并发、失败与恢复 realization

> 归档状态：`format-illegal`。本页是 DX-REQ-0015 前的历史文档基线，不定义当前产品。

## 1. Lock realization

`git.storage.source_mutation(canonical_source)` 使用 cache-root lock directory，把同 source 的
fetch/object preparation、worktree create/remove/move、checkout reconciliation 和 cache cleanup 串行化；其 `source_mutation_id`
底层入口让 auto cleanup 对 storage filename 中的 source ID 取得同一 lock。`RootStorage.mutation()`
使用 owner-root internal lock，把 frontmatter/ignore/manifest/runtime/payload publication 串行化。
调用顺序始终 source -> root；validation/list/link-parse 等只读操作不持锁。

`directory_lock` 通过 atomic `Path.mkdir()` acquire，每 50ms poll，默认 10s timeout；finally
`shutil.rmtree` release。它不检测/删除 stale lock，避免无法证明 ownership 时破坏并发结果。

## 2. Revalidation 与 atomicity

External/Worktree/Cache/Hook service 在 plan 后、持锁内重新读取 occupancy、record identity、Git
tracking、manifest identity 或 registration eligibility。变化转换为 `index_update_conflict`、
`cache_cleanup_conflict` 等稳定 failure，不覆盖。

`_atomic_text` 只保证一个 text/JSON file 的 replace。Detached worktree creation/move/checkout、chmod、
frontmatter、ignore、manifest、runtime 与 symlink 分别可见。Install/restore 按 source -> root
resource order 调用；link 依次发布 frontmatter、symlink、runtime、manifest。正常 result 通过
`changed` 暴露 effects；`DoctidexError.as_result` 不重建 publication 前后已经发生的 changes，
因此 mid-publication blocked 依靠 `affected`、现场重读和同 identity retry 恢复。

Hook registration compares the exact managed script before replacing it and has no composition mode. Each hook item
acquires its source lock before the owner-root lock; a failed item leaves its payload and runtime facts observable while
later independent items continue. The hook never waits for network/object acquisition: an absent exact object is a
preserved item-level `revision_not_found` outcome. A hidden move or runtime write can therefore be interrupted between
effects; the next run re-reads every hidden record rather than treating it as an already-complete decision.

## 3. Error translation

`DoctidexError` 持有 message、operation、affected、result、actions、requires_user、code、domain、
path、network、details 和 extra fields。`as_result` 生成 blocked envelope + Finding。Git runner
按 observable stderr/return code 区分 auth/network/revision/general errors，并清理 credentials。

`main` 对 usage/domain failure 返回 2；validation protocol fail 返回 1；interrupt 返回 130；未知
exception 写 diagnostic 后只公开 random ID。Renderer 不改变 domain fields。

## 4. Recovery behavior

| Incomplete state | Detection | Python response |
|---|---|---|
| objects only | cache/object presence、无 root change | same identity retry。 |
| host layout only | frontmatter/ignore + no complete record | install preflight/retry 补齐，不删无关配置。 |
| payload without record | path/HEAD/Git registration | preserve orphan/incomplete evidence；不 auto adopt/delete。 |
| runtime without manifest | role/manifest cross-check | direct retry 写 portable entry；保留 payload。 |
| missing direct payload | portable manifest + absent stable path | exact restore 重建 payload，并从 default provenance 重建可校验 runtime ownership。 |
| symlink/record mismatch | lexical target + runtime/manifest validators | `mapping_damaged`，不跟随或覆盖。 |
| worktree without ownership | Git registrations + namespace | preserve and report；用户决定后 native action。 |
| cache eligibility changed | second Git classification | conflict，cache 保留；auto 将其作为一个 blocked item，继续其它 candidate。 |
| remove payload deleted before metadata | exact ID 仍在 runtime/manifest、但 worktree path 已不存在 | same-ID remove 重新检查引用并发布剩余 per-install metadata 删除；它不删除 cache，也不猜测另一个 target。 |

Restore batch 捕获 item-level `DoctidexError` 并继续 independent items；top-level warning 与 totals
保留所有完成结果。成功恢复的 runtime record 可由后续 operation 立即读取；default-intent 与
显式 selector 分别恢复 `requested_default: true|false`，而 selector/commit 保持不变。Cursor
state 绑定 manifest/tree fingerprint，变化后拒绝继续。

## 5. Known limits

Logical readonly 不能阻止有权限进程修改；remote error 分类受 Git output 影响；orphan worktree
没有 automatic adoption command；platform symlink capability 不足时 link apply 不可用；validation
cursor 的 metadata fingerprint 不是 content-addressed snapshot；mid-publication blocked 需要重读
现场；unavailable worktree record 默认保留。这些是明确的 Python operating boundaries。
当前没有已知的 Architecture material limitation。
