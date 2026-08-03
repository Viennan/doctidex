# Checkout hook reconciliation 的实现

[`git/hooks.py`](../../../../../impls/libs/python/whero/doctidex/git/hooks.py) 负责 Python 的 host-hook 注册和
离线 reconciliation。它落实 [managed checkout hook](../../../architecture/external-snapshots-and-presentations.md#6-受管-checkout-hook)
contract：明确的 owner-root registration、foreign-hook protection、只协调既有 payload，以及 hidden
dependency preservation。

## 注册

`HookService.install()` 向 Git 获取 host `hooks/post-checkout` path，序列化带有 managed marker 和精确
owner-root command 的当前 Python v1 launcher，再在 hook-local lock 内写入可执行文件。只有既有 hook 的
完整当前 script content 与该 launcher 一致时，它才将该 hook 视为 Python-managed；任何其他 file 或
symlink 都返回 `hook_occupied` 并保持不动。

精确的 shell bytes、`shlex` quoting、executable mode 和 text equality 是 Python 的互操作实现机制。共同的
managed identity/conflict/preserve 规则由 Architecture 负责；不能产生 Python-compatible launcher 的另一
variant 必须保留此 hook 并报告 migration/interoperability boundary，不能覆盖它。

## 协调流程

```text
post-checkout launcher
  -> doctidex-git hook --run --root owner
  -> read current manifest/runtime
  -> classify direct records and dependency forest
  -> for existing payload: verify exact commit / checkout / sync runtime provenance
  -> for unprovable dependency: move to hidden namespace + publish hidden record
  -> recheck hidden nodes when an aligned ancestor becomes available
  -> emit per-install item and aggregate result
```

`hook --run` 离线运行，绝不 materialize 缺失的 direct install、刷新 moving ref、修改 manifest 的 fixed
commit 或重写 foreign hook。它通过 result/finding 让 missing/damaged/blocked item 保持可观察。unhide 时，
它先 align hidden payload，再将其移至 normal presentation 并发布完整 runtime record；hide 时，则先保留
Git/payload/parent evidence，之后 record 才标记 hidden state。共同 lifecycle 由 Architecture 定义；这个
顺序是 Python realization 的 evidence。

## 记录、失败与证据

Hook code 读取和写入 `runtime.json` install records，并移动实际 payload；其 physical inventory 的唯一
authority 是 [worksite inventory](../worksite-inventory-and-construction.md)。它与 external operations 共享
`RootStorage`/source mutation support，并将 manifest/runtime damage、unavailable commit、dirty payload、path
conflict 和 concurrent change 转换为稳定的 operation results。

[`test_git_plugin.py`](../../../../../impls/libs/python/tests/test_git_plugin.py) 覆盖 managed install idempotence、
foreign hook preservation、direct commit/provenance alignment，以及 hidden dependency recheck/unhide。公开的
`metadata_warning`/非空 `metadata_mismatches` contract 当前没有 Python producer；其已记录的 material
limitation [见此处](../architecture-coverage-evidence-and-worksite-validation.md#5-known-gaps-and-limits)，不能被
本组件 normal-path evidence 掩盖。
