---
type: index
doctidex:
  type: index
---

# Python `1.0.0` Impls

本 variant 说明 `whero-doctidex==1.0.0` 如何实现并映射
[doctidex-git Architecture](../../architecture/index.md)。Architecture 的模型、组件依赖和
workflow 决定主要阅读顺序；本层定义 Python/runtime/platform 下的 physical realization、代码
ownership 和 evidence。辅助对象与局部算法可直接链接源码，不在文档中复制成第二套领域模型。

## 适用条件

| 条件 | 当前 realization |
|---|---|
| Runtime | CPython `>=3.11`；CI 覆盖 3.11/3.12。 |
| Platform | Linux、macOS、Windows；需要 system Git。 |
| Stable user/program API | `doctidex-git` console script、JSON `schema_version: "1.0"`。 |
| Agent API | Overview、Read、Maintenance 三个 Published Skills。 |
| Python import | 没有稳定 public import API；`whero.doctidex.*` 是 internal realization。 |

## 阅读顺序

1. [User surface 与 integration](user-surface-and-integration.md)：Python variant 的安装、human/
   agent/program 入口和平台前置条件。
2. [Platform、package 与 dependencies](platform-package-and-dependencies.md)：交付物、dependency
   direction、OS/Git integration 与限制。
3. [Physical data 与 storage](physical-data-and-storage.md)：文件、JSON、Git objects/worktrees、
   cache、lock 与 publication。
4. 按 Architecture component 进入下方代码设计；每页说明主要 callers/types/functions、effects、
   failures、concurrency 和 tests，并提供 source 入口继续阅读辅助实现。
5. [并发、失败与恢复](concurrency-failures-and-recovery.md)核对跨 component boundary。
6. [Architecture coverage 与 tests](architecture-coverage-and-tests.md)按关键模型与主要 workflow
   定位 realization，并区分 variant choice 与 material limitation。

## Component realization

| Component | Python authority |
|---|---|
| Surface/result | [CLI、results 与 rendering](components/cli-results-and-rendering.md) |
| Tree/root/validation | [Protocol interpreter](components/protocol-interpreter.md) |
| Git source/objects/state | [Git source 与 storage](components/git-source-and-storage.md) |
| Host Git/portable/runtime state | [Git source 与 storage](components/git-source-and-storage.md) + [External installation 与 mapping](components/external-installation-and-mapping.md) |
| Install/link/restore/remove/mapping/checkout hook | [External installation 与 mapping](components/external-installation-and-mapping.md) |
| Worktree/cache | [Worktree 与 cache](components/worktree-and-cache.md) |

总体依赖为 `cli -> protocol/external/hook/worktree/cache -> source/storage -> Git/filesystem`，同时
`errors/results` 是横向结果支持。`protocol` 不导入 Git；source 不读取 doctidex root；renderer
不产生 domain facts；Published Skills 不读取 package internals。

## 实现边界

当前无稳定 import API；logical read-only 是 permission hardening 而非 sandbox；remote failure
分类依赖 Git 可观察输出；symlink 不可用时不采用 copy/junction fallback；worktree creation 与
ownership publication 之间的 orphan 只保留证据。当前实现选择与 material limitation 见
[coverage](architecture-coverage-and-tests.md#4-realization-结论与限制)。

实现来源为 [`impls/libs/python`](../../../../impls/libs/python/)，测试为其 `tests/`；历史 0.1.0
realization 只在 [archive](../../archive/v0.1.0/index.md)。
