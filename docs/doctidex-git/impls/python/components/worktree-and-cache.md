# Worktree 与 cache

## [`git/worktrees.py`](../../../../../impls/libs/python/whero/doctidex/git/worktrees.py)

`WorktreeSource` 属性为 `kind`、common `gitdir`、canonical `identity`、可公开 `source_url`、
`repository_relative_path`、实际 `network` 和可选 `ResolvedSource`。`WorktreeService` 属性为
owner context/root/storage。

`_classify` 的顺序是 managed presentation、gitfile、bare/working tree、URL；目录/文件类型
互斥，因此与公开 managed -> working/bare -> gitfile -> URL 语义一致。gitfile 会解析为
common gitdir，避免从 linked-worktree private gitdir 再创建现场。managed subdirectory
保留 suffix，所有结果 path 仍在 owner root 的扁平 worktree namespace。

`open` 在 source mutation boundary 中解析 selector/base commit，每次生成随机 ID/path，统计
同 source/base 的 reuse candidates，创建 detached writable worktree后才发布 record；它不建
branch 或进入 external manifest。创建与 record publication 间中断可由 Git metadata 和受管
namespace留下客观 orphan 证据，当前实现只保留，不自动 adopt/delete。

`list` 从 runtime 选 root 内 items，再用原生 `git status --porcelain` 重算
clean/changed/unavailable，按 exact source/worktree filter、稳定 path 顺序分页。WorktreeItem
包含 Architecture 定义的全部 source/owner/selector/base/root-internal/worktree/suffix/working
path/state/findings 属性。

`close` 只匹配 exact record path；unavailable/changed 以顶层 WorktreeItem blocked 并保留。
clean path 在 source/root lock 中调用 `git worktree remove`，成功后删除 record；不触碰其他
presentation。若 remove 后在 record deletion 前中断，下一次 close 把 absent path 分类为
unavailable 并保留 record，不从缺失 path 推导自动清理授权。

## `CacheService`

`clean(url, apply)` 不选择 root。locator 必须是 remote 或绝对 local path；canonical identity
只定位一个 bare source。`clean_auto(apply)` 枚举 cache root `sources/` 的 direct child，只有
`<24-lowercase-hex>.git` 的 non-symlink directory 是 candidate；它们以 opaque source ID 排序，未知
object 或 symlink 不读取、不报告为 candidate，也不删除。当前 cache storage 不保存 canonical URL，因此 auto item 不能恢复或
公开 source URL。`_classify_linked_worktrees` 解析 `git worktree list --porcelain`，跳过 bare 本身，
把每个登记唯一分成 valid 或 Git `prunable`；语法/metadata异常 blocked。

URL mode 的 source lock 内有任一 valid 时返回 preserved warning。否则 dry-run 返回 planned；apply
立即重查相同计数后只删除 bare source directory，公开 changed 仍为空。Auto 为每个 ID 取得同一
source lock；candidate 在 enumeration 后消失、变成 symlink、metadata damage 或 recheck conflict 都被捕获成
`blocked` item，其余 candidate 继续。`source_mutation_id` 让 auto 与使用 canonical source 的
open/remove/URL clean 共用同一 lock namespace。Auto 的 top-level results 汇总 item findings/counts，
但不泄露 cache path。两种模式都不清理 root payload、manifest、runtime 或其他来源。该 operator
command不进入 Published Skills。

## Effects、concurrency 与 evidence

Open/remove/cleanup 通过 source lock 串行；worktree record publication 另进入 root lock。List
只读且每次重新观察 Git。Close/cleanup 的任一 ownership 或 metadata 不确定都会完整保留对象。

[`tests/test_git_plugin.py`](../../../../../impls/libs/python/tests/test_git_plugin.py) 的
`test_worktree_dirty_preservation_and_close`、`test_worktree_open_accepts_a_linked_worktree_gitfile`、
`test_unrecorded_worktree_namespace_path_is_preserved`、
`test_interrupted_worktree_publication_leaves_orphan_evidence`、
`test_worktree_source_kinds_managed_bare_and_submodule`、
`test_cache_cleanup_preserves_active_then_removes_eligible`、
`test_cache_cleanup_accepts_prunable_registration` 与
`test_cache_cleanup_auto_isolated_candidates`、
`test_cache_cleanup_auto_rechecks_each_candidate` 提供证据。跨平台与 suite 入口见
[Platform](../platform-package-and-dependencies.md)和
[Architecture coverage](../architecture-coverage-and-tests.md)。
