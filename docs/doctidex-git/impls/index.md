---
type: index
doctidex:
  type: index
---

# doctidex-git v1.0.0 Impls

本层保存特定实现条件下落实
[doctidex-git Architecture](../architecture/index.md) 的完整方案。Architecture 定义所有实现
必须覆盖的共同能力与 observable semantics；每个 Impls variant 定义自己的安装、接入、
物理数据、组件、数据流、特殊处理、代码 ownership 和验证证据。

## 当前 variants

| Variant | 适用条件 | User surface | 实现方案 | Coverage |
|---|---|---|---|---|
| [Python `1.0.0`](python/index.md) | CPython `>=3.11`、Git executable、Linux/macOS/Windows | console CLI、JSON subprocess、三个 Published Skills；无稳定 Python import API | package、protocol、Git source/storage、external、worktree/cache | [Architecture coverage](python/architecture-coverage-and-tests.md) |

## 本层 authority

Impls 是当前实现方案的权威，但不能改变 Architecture 的共同能力：

- variant-specific 安装、调用入口、runtime/platform 前提和示例归 Impls；
- 物理 schema、内部 path、module、type/function、algorithm、lock 和 test 归 Impls；
- 共同 user problem、能力、public contract、逻辑模型和失败语义归 Architecture；
- Requirements 保存经用户审阅的历史意图与决定，不作为当前使用说明；
- source、tests 和 Published Skills 是落实证据，不能静默覆盖任一文档 authority。

新增 variant 必须建立自己的完整 user surface、系统设计和 coverage，而不是复制 Python
代码地图。当前 Python artifact 位于 [`impls/libs/python`](../../../impls/libs/python/)，
Published Skills 位于
[`impls/agent-plugins/doctidex-git`](../../../impls/agent-plugins/doctidex-git/)；这里的
`docs/doctidex-git/impls/` 是设计文档，不是实现 artifact 存放目录。

历史 `0.1.0` 实现说明位于[版本归档](../archive/v0.1.0/index.md)。归档只说明旧版本，不
按当前 Impls 完整性标准追溯改写。
