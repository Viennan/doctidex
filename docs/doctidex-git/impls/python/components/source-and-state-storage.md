# Git source 与状态存储的实现

本页说明 Python 对 Git source resolution、bare cache、`RootStorage` JSON validation 与物理 publication
primitives 的实现。它落实[external snapshot](../../../architecture/external-snapshots-and-presentations.md)与
[worktree/cache](../../../architecture/worktrees-and-cache.md)，不重新定义 manifest/runtime option 语义；这些事实由
Architecture 和 [worksite inventory](../worksite-inventory-and-construction.md) 统一拥有。

## Git source 与 cache 的职责归属

| 源码归属 | 职责 | 调用者与可观测边界 |
|---|---|---|
| [`git/runner.py`](../../../../../impls/libs/python/whero/doctidex/git/runner.py) | 基于参数数组调用 Git subprocess，并转换经净化的失败。 | 供 source/external/hook/worktree 使用；不提供 public Python API 或 interactive credential prompt。 |
| [`git/source.py`](../../../../../impls/libs/python/whero/doctidex/git/source.py) | `RevisionSelector`、source canonicalization、source resolution、bare cache acquisition 与 detached worktree helpers。 | 支持 external install/restore、hook alignment、URL worktree；产生固定的 commit/cache 事实。 |
| [`git/storage.py`](../../../../../impls/libs/python/whero/doctidex/git/storage.py) | `RootStorage`、root/cache lock namespaces、manifest/runtime 读写与 validators。 | 供 external/hook/worktree 使用；拥有物理 `/.doctidex/git` paths，并转换 validation failure。 |

Canonical source 与 source ID 是 Python 用于 equality/cache 的 identifiers。它们可能不同于 `source_url` 的
presentation，不得被视为用户可见的 credentials 或 cross-language wire identity。当前 cache 对每个 canonical source
使用一个 bare Git repository，并通过 local lock namespace 协调 source mutation boundaries；尽管 artifact 的
shared/preserve 语义是 common，cache layout 与 hash 仍是 private。

## `RootStorage` 的约定

`RootStorage` 将缺失的 runtime 读作空的、有效的 owner-local record；已存在但无效的 runtime 会被阻止。缺失的
manifest 可以是空的 local pre-install state，而要求 recovery 的调用者会收到
`recovery_manifest_missing`；已存在但无效的 manifest 会收到 `recovery_manifest_invalid`。它会在写入前验证 record
identity/path/references。因此，所有会在 Python worksite 中 materialize 的 configuration fields 都列于
[inventory](../worksite-inventory-and-construction.md#2-configuration-representations)。

首次 materialize 受管状态时，`RootStorage.ensure_host_layout()` 在 root `index.md` 声明 `.doctidex` 为
boundary/unsafe，并附加带 `unsafe: true` 的受管入口；selected root 同时是 host 时，它也附加 `.gitignore` 的
可达入口。它保留现有 frontmatter、Markdown 和 `.gitignore` 规则，且不为 namespace 内部对象分别生成索引。

当前实现的 publication 使用 same-directory temporary data、durable replacement 与 directory locks。这些原语支持
Architecture 的 preserve/reobserve boundary，但不构成 multi-resource transaction。详细的 interruption/lock constraints
见[publication/recovery](../publication-recovery-and-private-mechanics.md)。

## 证据

代表性证据位于 [`test_git_plugin.py`](../../../../../impls/libs/python/tests/test_git_plugin.py)：固定的
default/explicit revision behavior、不同的 selector identity、忽略 manifest 时的阻止、restore 的 runtime projection、
source/cache cleanup 与 root lock preservation。该测试套件验证可观测结果；它不将 cache hash、JSON 键顺序或
`RootStorage` helper structure 变成 Architecture requirement。
