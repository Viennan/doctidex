---
type: index
doctidex:
  type: index
---

# doctidex-git Impls

本层说明特定语言、runtime、platform 或 deployment 条件怎样实现
[doctidex-git Architecture](../architecture/index.md)。Architecture 定义所有 variant 必须保持的
user surface、工作现场语义、handoff 和 safety boundary；Impls 定义当前 variant 的 installation、
physical representation、component/code owner、algorithm、effect、recovery、test evidence 和 material
limitation。

## 当前 variants

| Variant | 适用条件 | 实现 authority | 工作现场 evidence |
|---|---|---|---|
| [Python `1.0.0`](python/index.md) | CPython `>=3.11`、system Git、Linux/macOS/Windows。 | package、console CLI、JSON subprocess、Published Skills。 | [worksite inventory and construction](python/worksite-inventory-and-construction.md)。 |

## 两层边界

- Architecture 拥有共同产品能力、public contract、配置/artifact 的 identity/option semantics、
  lifecycle、handoff、compatibility、failure/recovery 和 safety boundary。
- Impls 拥有具体 package/module、physical layout/encoding、library、source identity/hash、Git argv、
  lock/temp/publication primitive、platform behavior、source/test evidence 与 current limitation。
- 一个存在于 user-surface 工作现场的 file/option/artifact 不能因当前只有一个 variant 就成为
  无法解释的 private state；Impls 必须链接它的 Architecture authority，同时说明本 variant 如何
  materialize、validate、convert、preserve 或 diagnose。
- 不影响 user surface 正确实现或工作现场解释的 local helper、algorithm、call graph、byte ordering、
  lock strategy 和 optimization 不需进入 Architecture。

Requirements 保存用户审阅的历史意图；source/tests/Published Skills 是事实 evidence，不能静默覆盖
Architecture 或 Impls authority。重构前说明保留在
[DX-REQ-0015 前 baseline](../archive/baselines/pre-dx-req-0015/index.md)，不定义当前 realization。
