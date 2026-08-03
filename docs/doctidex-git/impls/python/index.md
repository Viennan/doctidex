---
type: index
doctidex:
  type: index
---

# Python `1.0.0` 实现文档

本页是 `whero-doctidex==1.0.0` 的 Python 实现入口。它落实[共同 Architecture](../../architecture/index.md)，但不重新定义共同用户界面、manifest/runtime 字段语义、hook/worktree 生命周期或 public JSON contract。读者应先从相应的 Architecture 权威说明理解“必须保持什么”，再在这里定位 Python 如何做到，以及何处存在 limitation 或未证实 evidence。

## 适用条件与稳定边界

| 条件 | Python 实现 |
|---|---|
| 运行时 | CPython `>=3.11`；CI 覆盖 3.11/3.12。 |
| 平台 | Linux、macOS、Windows，且可从 subprocess 调用 system Git。 |
| 稳定的用户/程序 API | `doctidex-git` console script 与 JSON `schema_version: "1.0"`。 |
| Agent API | 已发布 Overview、Read、Maintenance Skills；不要求 agent 读取本页。 |
| Import API | `whero.doctidex.*` 是内部实现，不是稳定的 public import API。 |

## 阅读路线

1. [变体交付与用户界面](variant-delivery-and-surface.md)：package/platform、console/subprocess entry、Published Skill assembly 和变体特有的用户集成。
2. [工作现场清单与构造](worksite-inventory-and-construction.md)：本变体实际产生的 configuration/artifact、物理布局、场景矩阵、transcript 和 Architecture evidence。
3. 按责任进入源码设计：[CLI/结果](components/cli-results-and-rendering.md)、[protocol/root 观察](components/protocol-and-root-observation.md)、[source/state storage](components/source-and-state-storage.md)、[external 呈现/mapping](components/external-presentation-and-mapping.md)、[checkout hook 协调](components/checkout-hook-reconciliation.md)、[worktrees/cache 清理](components/worktrees-and-cache-cleanup.md)。
4. [发布、恢复与私有机制](publication-recovery-and-private-mechanics.md)说明 source-specific concurrency/recovery boundary；[覆盖、证据与工作现场验证](architecture-coverage-evidence-and-worksite-validation.md)连接共同能力、source/tests、配对 reader/verifier outcome 和已知缺口。

## 依赖与责任归属

```text
console CLI / JSON renderer
        |
 protocol validation      external / hook       worktree / cache
        |                      |                     |
      root observation ---- source + RootStorage ----- Git / filesystem
        |
  errors, results, diagnostics
```

`protocol.*` 不导入 Git；source/storage 不将 doctidex root 解释为 Git source；renderer 不产生 domain facts；Published Skills 不读取 package internals。`RootStorage`、Git source/cache、host hook、payload 和 writable worktree 的具体责任归属分别见对应 component 页面；实际工作现场仅在[清单](worksite-inventory-and-construction.md)中作为物理权威说明出现一次。

## 当前实现边界

Python 选择 `pathlib`、argument-array Git subprocess、round-trip YAML、native relative symlink、same-directory temporary publication、directory locks 和 local user cache。它不提供 in-process API、copy/junction symlink fallback、sandbox-style read-only、moving-ref auto refresh 或 implicit cache clean。

已记录的 material limitation/evidence boundary 见[覆盖页面](architecture-coverage-evidence-and-worksite-validation.md#5-known-gaps-and-limits)：JSON hook contract 中的 `metadata_warning` 目前没有 Python producer；`WorktreeService.close` 的 lock revalidation 不应被宣称为已验证。它们不由本次文档重构修复。
