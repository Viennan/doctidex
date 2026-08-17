# DX-ISSUE-0001：`external link --apply` 未在锁内重验过期前置条件

状态：`resolved`

创建日期：2026-08-05

严重程度：high

来源：2026-08-05 对当前 `HEAD`（`259085abd8c324a53840f55a6783fa31eb874fbb`）进行的全仓 review；用户授权将严重度最高、已验证的问题记录为 Issue。

确认：2026-08-05，用户明确要求将本轮 review 创建的全部 6 个 Issue 置为确认状态。

## 问题

`external link` 在进入 root mutation lock 前读取 runtime、manifest、target 与 Git tracking，并据此构造
`expected_mapping`。`--apply` 进入 lock 后只探测 symlink 能力、按旧计划创建不存在的 symlink，再直接写入
runtime 和 manifest；它不重新读取或比较这些前置状态。

因此，两个针对同一空闲 TARGET、但来自不同 managed direct install 的并发 `--apply` 都可能先通过
preflight。先获得 lock 的调用创建指向 source A 的 symlink；后获得 lock 的调用看到 symlink 已存在而不替换，
却把 `runtime.json` 与 `manifest.json` 更新为 source B 的 mapping。最终 presentation path 与 durable records
描述不同 source，后续命令只能以 `mapping_damaged` 保留现场。

## 具体场景

设 root `R` 已有两个可用的 direct install，工作目录分别为 `source-A` 与 `source-B`，而 `R/external/api`
尚不存在。两个调用几乎同时执行：

```text
doctidex-git external link source-A external/api --root R --apply
doctidex-git external link source-B external/api --root R --apply
```

在任一调用取得 mutation lock 前，两者都已经观察到 `runtime.links["external/api"]` 和
`manifest.links["external/api"]` 不存在，且 target 未被占用。随后交错如下：

1. A 先取得 lock，建立 `external/api -> source-A` 的相对 symlink，并把 A 的 mapping 写入 runtime 和 manifest。
2. B 再取得 lock。B 沿用锁外的“target 不存在、没有 mapping”计划；锁内只因 target 已是 symlink 而跳过创建，
   随即将 runtime 和 manifest 中 `external/api` 的 `install_id` 写成 B。

这是由当前锁外检查和锁内写入顺序直接导出的交错；现有测试没有人为控制这两个 invocation 的暂停点，故不是一次已保存的
并发命令 transcript。

## 当前错误状态

交错完成后，三个持久对象互相矛盾：

```text
filesystem: R/external/api -> <relative path to source-A>
runtime.json:  links["external/api"].install_id == <B 的 install ID>
manifest.json: links["external/api"].install_id == <B 的 install ID>
```

第二次 apply 仍可返回它已应用 B 的 mapping。之后以 B 为 source 运行 `external rebind ... external/api` 时，命令的
managed-record 检查会发现实际 symlink 不是 B，保留 presentation 并返回 `mapping_damaged`，而不是自动覆盖 A 的路径。

## 正确行为

B 在 lock 内重新观察到 A 已占用 target 或已发布 mapping 后，必须保留 A 的 path、runtime 和 manifest，并以
blocked/conflict 结果结束。无论采用何种内部 lock，成功的 apply 都不应返回 symlink 与 durable records 指向不同
install 的状态。

## 受影响范围与条件

- Python variant 的 `external link --apply`，以及同一 root 中所有依赖其 durable link mapping 的 external 操作。
- 至少两个调用在第一个调用完成 mutation 前取得相同 TARGET 的 preflight observation；两个调用使用不同、可用的
  direct install source。
- 同一根的 mutation lock 会序列化写入，但目前不会使锁外 observation 在锁内自动失效。

## Authority 与证据

- [产品与用户 surface](../doctidex-git/architecture/product-and-user-surfaces.md#5-可观察结果授权与非目标) 要求 apply
  重新验证 root、target、manifest、Git tracking、reference 与 concurrency condition。
- [操作安全与恢复](../doctidex-git/architecture/operation-safety-and-recovery.md#1-调用计划与授权) 要求现状变化时
  conflict 或 blocked，调用方不得为成功覆盖新发现的 state；其[恢复原则](../doctidex-git/architecture/operation-safety-and-recovery.md#3-部分成功中断与恢复)也要求后续操作重读当前 observable state。
- [external.py](../../impls/libs/python/whero/doctidex/git/external.py#L309) 至 [external.py](../../impls/libs/python/whero/doctidex/git/external.py#L432) 在 lock 外完成 mapping、target 与 manifest 检查；[锁内写入](../../impls/libs/python/whero/doctidex/git/external.py#L434) 至 [external.py](../../impls/libs/python/whero/doctidex/git/external.py#L463) 未重验这些值。
- [storage.py](../../impls/libs/python/whero/doctidex/git/storage.py#L82) 的 `update_runtime()` 在读取后执行 callback 并写回，
  不能检测 callback 计划所依据的 target/manifest 是否已被其他调用改变。

## 影响与后续决定

这会使一次成功返回的 apply 留下 symlink 与两个 durable records 不一致的状态，阻断后续安全管理与恢复。修复应在
同一 lock 内重新观察并比较所有会影响 mutation 的前置条件；若状态变化，返回 preserved/conflict 结果而非写入。
应加入确定性并发回归测试，覆盖两个 source 竞争同一 target 的交错顺序。Issue 目前不授权实现或状态转换。

## 处置

解决：2026-08-05，用户明确要求将本轮六项 Issue 标记为 `resolved`。根据
[DX-REQ-0021.1](../requirements/0021-resolve-confirmed-review-issues/01-external-link-apply-concurrency.md)，
`external link --apply` 取得 root mutation lock 后会重跑完整 preflight；target 已被另一调用发布时，第二次调用返回
`target_occupied`，不会创建或覆盖 runtime/manifest mapping。`external install`、`restore` 与 `remove` 的同类 stale
publication 也在该 Requirement 下补入各自的锁内重验。

验证：`test_link_apply_reobserves_a_target_published_after_its_preflight` 以受控交错验证第二个 source 被阻止，且 symlink、
`runtime.json`、`manifest.json` 保持第一个 source 的 install ID；完整 Python tests、Ruff、全根及 Requirement scope 的
validator、`git diff --check` 均通过。

残余边界：root mutation lock 只协调 doctidex-git 自身调用，不为任意 native Git 或用户进程提供全局 transaction；这类
外部写入仍按当前可观察状态 preserve-first 处理，且中断后的多文件持久状态仍由后续 invocation 诊断和恢复。
