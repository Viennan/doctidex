# Worktree 与 cache cleanup 的实现

[`git/worktrees.py`](../../../../../impls/libs/python/whero/doctidex/git/worktrees.py) 拥有 `WorktreeService` 与
`CacheService`。它实现 Architecture 的可写 worktree 与 shared-cache lifecycle；实际物理路径与记录清单统一保留在
[worksite inventory](../worksite-inventory-and-construction.md)，此处不重复。

## `WorktreeService` 的实现

| 入口 | Python 实现 | 保留的通用行为 |
|---|---|---|
| `open` | 对已管理路径、URL、working tree、bare gitdir 或 gitfile 分类；解析确切的 base commit；创建 detached Git worktree 并发布 runtime record。 | 每次成功产生新的 opaque ID、root-internal writable artifact、source-kind/base-commit result。 |
| `list` | 读取 runtime records，按 source/worktree 过滤，探测 path/Git status 并分页。 | `clean`/`changed`/`unavailable` 状态；opaque cursor 与有界条目。 |
| `close` | 定位确切的 runtime record，拒绝 unavailable/changed，移除 clean native worktree 后再移除 record。 | 只允许 clean close；以 `worktree_unavailable` 保留不可用的 record/payload。 |

该 service 使用 `RootStorage` records 与 source mutation coordination。Source classification 和 common Git-dir
resolution 是局部 implementation choices。它绝不将 unrecorded physical directory 视为 successful managed close，
也不会仅因 path 看似 stale 就删除 record。

`close` 在进入 source/root mutation boundary 前取得 record/status observation。因此，本文档不声称它会对该 observation
执行 lock-internal revalidation；其当前 race/evidence limit 记录于
[coverage](../architecture-coverage-evidence-and-worksite-validation.md#5-known-gaps-and-limits)。

## `CacheService` 的实现

`clean(URL, apply)` 会规范化传入的 eligible locator，并处理一个 cache。`clean_auto(apply)` 枚举当前 Python 识别的
cache candidates，隔离各个 source mutation failure，并聚合其状态。二者都使用 native Git
`worktree list --porcelain` 的事实，在 destructive apply 前分类 valid/prunable registrations。Python source ID/cache
directory 的命名和解析细节是 private；shared-cache preservation rules 由 Architecture 拥有。

| Python 结果 | 代码路径 | 可观测结果 |
|---|---|---|
| cache 不存在 | source-cache path 不是 directory。 | `cache_source_not_found`，不删除。 |
| 活跃且有效的 worktree | 分类器返回 valid linked count。 | 使用 `cache_worktree_active` 返回 `preserved`。 |
| 损坏或未知的 Git metadata | 分类器无法确认安全性。 | 使用 `cache_source_damaged` 返回 `blocked`，保留 cache。 |
| apply 前重查发生变化 | counts 不同或 candidate 消失。 | 返回 `cache_cleanup_conflict`/not-found，按对应 item 保留或继续。 |
| 符合条件的 apply | 第二次 classification 仍为 eligible。 | 只移除 exact cache，并返回 `removed`。 |

## 证据

[`test_git_plugin.py`](../../../../../impls/libs/python/tests/test_git_plugin.py) 覆盖 source-kind 的分类、
clean/changed 状态下的 worktree close、unavailable/orphan preservation、active/prunable cache states、auto isolation
与 per-candidate recheck。测试确立已记录的 user-visible outcomes，而非 UUID format、native Git argv 或 internal cache
path layout。
