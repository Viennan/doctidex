# External presentation 与 mapping 的实现

[`git/external.py`](../../../../../impls/libs/python/whero/doctidex/git/external.py) 负责 Python 对 install、link、
rebind、unlink、restore、remove 和 link-parse 的编排。它消费 `RootContext`、source/storage 和 current managed records，落实
[external snapshot/presentation](../../../architecture/external-snapshots-and-presentations.md)，但不把
`ExternalService` 或其 helper records 变为 public API。

## 入口与负责的副作用

| 入口 | Python 协调器的副作用 | 所落实的 Architecture 契约 |
|---|---|---|
| `ExternalService.install` | resolve/fix source revision，创建或复用 detached payload，确保 host layout，发布 runtime 以及 direct manifest entry 或 dependency parent edge。 | install identity、fixed snapshot、direct/dependency/promotion、plan/apply。 |
| `ExternalService.link` | 证明 complete direct source，校验 target/tracking/safe state，写入 relative symlink 和 responsible-index declaration，并发布 runtime/manifest mapping。 | durable presentation、`safe_state`、trackability、mapping。 |
| `ExternalService.rebind` | 验证既有 direct presentation 的 runtime/manifest/symlink/index/payload，再按 link source resolution 解析新 direct mapping，准备 sibling symlink 并在 root mutation 内发布新 mapping。 | 同 target 的 fixed-snapshot 切换、old/new result、没有 temporary broken symlink。 |
| `ExternalService.unlink` | 验证 exact durable target，使用 tree observation 查找 safe reference，reference-free 时删除 symlink/两种 link record，并只按 record ownership 更新 index。 | presentation-specific reference protection、frontmatter 保守清理、install 保留。 |
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

Install、link、rebind 和 unlink 在各自 managed publication 前重验相关的 user-visible preconditions。rebind
先创建 temporary sibling relative symlink，再以 `os.replace` publication live target；temporary path 只属于
mutation mechanics，不进入 public result。Runtime/manifest/index 是分别 atomic 的文件，故中断只保留实际 state，
后续 invocation 通过 mapping validation 诊断而不猜测补齐。unlink 的 preflight 不把它将删除的 own link record
当作 blocker，但保留其它 safe reference。Restore 的范围仅限 versioned manifest entries；link-parse 是 read-only，并将 portable broken dependency links 视为正常的
`dependency_not_installed` state。Remove 扫描 Architecture 定义的 reference classes，明确不会为求成功而
删除 references。

link record 在现有 portable 字段以外可保存 `frontmatter_ownership`。Python 在创建 link 时比较 responsible
index 的 exact declaration，分别记录 `managed`、`preserved`、`removed` 或 `absent`；rebind 在 safe/unsafe
分类转换时重算这些状态。unlink 只移除 `managed` entry、恢复 `removed` 的 `unsafe` entry；没有该 optional
field 的旧 record 按 legacy state 处理，保留所有 declaration。这是从现有 record 提供无损升级路径，storage
validator 继续接受 unknown optional fields，但要求 manifest/runtime 的 link record 在可证明 mapping 中一致。

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
