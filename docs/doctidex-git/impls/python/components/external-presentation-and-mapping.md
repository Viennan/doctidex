# External presentation 与 mapping 的实现

[`git/external.py`](../../../../../impls/libs/python/whero/doctidex/git/external.py) 负责 Python 对 install、link、
restore、remove 和 link-parse 的编排。它消费 `RootContext`、source/storage 和 current managed records，落实
[external snapshot/presentation](../../../architecture/external-snapshots-and-presentations.md)，但不把
`ExternalService` 或其 helper records 变为 public API。

## 入口与负责的副作用

| 入口 | Python 协调器的副作用 | 所落实的 Architecture 契约 |
|---|---|---|
| `ExternalService.install` | resolve/fix source revision，创建或复用 detached payload，确保 host layout，发布 runtime 以及 direct manifest entry 或 dependency parent edge。 | install identity、fixed snapshot、direct/dependency/promotion、plan/apply。 |
| `ExternalService.link` | 证明 complete direct source，校验 target/tracking/safe state，写入 relative symlink 和 responsible-index declaration，并发布 runtime/manifest mapping。 | durable presentation、`safe_state`、trackability、mapping。 |
| `ExternalService.restore` | 枚举 portable direct entries，重建 local runtime projection 和缺失的 exact payload。 | 不刷新 ref、不重写 link 的 exact recovery。 |
| `ExternalService.remove` | 对 payload/runtime/manifest 和 references 做 preflight，只移除 reference-free 的 exact install state。 | reference-protected removal 和 hidden preservation。 |
| `ExternalService.link_parse` | 将 current runtime mapping 与 portable installed-content mapping 合并为一个 public result。 | available/missing/dependency/damaged/unmanaged distinction。 |

上述每个 physical file/effect 只在
[worksite inventory](../worksite-inventory-and-construction.md#1-physical-layout-与-ownership) 列出一次。本组件将其
连接到 `ExternalService`/helper ownership，而不重复 schema fields。

## 控制与数据流

```text
CLI external command
  -> RootContext + RootStorage validation
  -> source resolution / fixed commit / source-cache boundary
  -> payload or mapping preflight
  -> root mutation boundary
  -> manifest/runtime/index/ignore/symlink effects
  -> envelope, finding, affected/changed evidence
```

Install 和 link 在各自 managed publication 前重验相关的 user-visible preconditions。Restore 的范围仅限
versioned manifest entries；link-parse 是 read-only，并将 portable broken dependency links 视为正常的
`dependency_not_installed` state。Remove 扫描 Architecture 定义的 reference classes，明确不会为求成功而
删除 references。

该 module 的 stable facts 只通过 CLI/JSON 露出。内部 `_mapping_*`、`_portable_*`、source/cache helper
signatures、path computation 和 relative-symlink calculation 可以演进，只要保持 Architecture contract 和
inventory mapping。

## 失败与证据

`DoctidexError` paths 区分 root/source/revision/tracking/reference/mapping/manifest damage 与 unexpected
failures。External mutations 具有独立 publication effects，因此 result `changed`/`affected` 是 recovery
evidence 的一部分；caller 不假定 rollback。Locks、publication order 和 interruption evidence 见
[publication/recovery](../publication-recovery-and-private-mechanics.md)。

[`test_git_plugin.py`](../../../../../impls/libs/python/tests/test_git_plugin.py) 中的 representative tests 覆盖
fixed default revision、dependency cycle/promotion、link safe classification/retry、link-parse portable mapping、
restore runtime projection、remove reference protection 和 retained cache boundary。
