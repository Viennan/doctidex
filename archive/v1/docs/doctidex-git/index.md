---
type: index
doctidex:
  type: index
---

# doctidex-git 设计与实现文档

状态：当前 `v1.0.0` 非规范性实现文档

本目录记录 `doctidex-git` 的版本化设计、对用户暴露的接口，以及 Python 参考实现的
落实状态。它不是 doctidex 协议正文；协议要求只以
[`spec/overview.md`](../../spec/overview.md) 为准。

当前 `v1.0.0` Architecture 与 Python Impls 以可解释的跨 variant 工作现场重新组织；
[DX-REQ-0015](../requirements/0015-architecture-and-impls-document-principles.md) 已记录 paired reader/verifier
evidence 和当前 Python limitation。`0.1.0` 设计、以及本次重构前的文档基线均已归档，不能与当前
surface 混用。

## 按阅读目的进入

| 目的 | 入口 | 内容边界 |
|---|---|---|
| 理解 v1.0.0 的共同能力或已有工作现场 | [Architecture](architecture/index.md) | 当前 user surface、共同 state/workflow、配置/artifact 语义、跨 variant handoff 与 public interface。 |
| 使用或维护具体 variant | [Impls](impls/index.md) | 按实现条件进入 Python 等 variant 的接入、工作现场构造、physical realization、source/test evidence 与 limitation。 |
| 排查历史 | [Archive](archive/index.md) | `0.1.0` 版本 archive 与 DX-REQ-0015 前文档 baseline；都不是当前 authority。 |
| 追溯需求如何演进 | [Project Requirements](../requirements/index.md) | 从项目级历史中查找影响 doctidex-git 的需求、状态与双向依赖。 |

正常使用已发布插件时，应优先阅读插件自身的 Skills。Architecture 定义不同实现共同覆盖
的能力与 observable semantics；Impls 定义某个 variant 的最佳接入与完整 realization。
安装后的用户或 agent 不需要阅读 repository Impls 或理解内部 state、映射和锁才能完成
公开工作流。

## 信息层级

```text
doctidex protocol                  /spec/overview.md
        |
        v
doctidex-git v1 common design      architecture/
        |                              |
        v                              v
published Skills                  Python Impls
                                   impls/python/

doctidex-git 0.1.0 code/design    archive/v0.1.0/
```

箭头表示落实和约束关系，不表示下层可以改变上层语义。当前 Skills、Python Impls 与代码
落实 v1 Architecture；归档只用于排查历史，不反向定义当前行为。

## 公开入口与切换状态

- 当前 Skills：Overview、Read、Maintenance；
- 当前 `doctidex-git` CLI 与 JSON：package `1.0.0`、JSON `schema_version: "1.0"`；
- 历史 `0.1.0` surface：只在 archive 中保留设计和代码阅读线索；
- 原生文件、搜索、编辑和 Git 工具：始终是实际读取、修改和审阅文件的主要工具。

Python 包内的类和函数属于当前实现内部接口，不承诺为稳定的外部库 API。Python variant 的
安装、subprocess 接入、系统设计和模块 ownership 见
[Python `1.0.0` Impls](impls/python/index.md)；归档只说明 `0.1.0`。

## 文档维护规则

- Architecture 先说明场景和 user surface，再完整定义共同能力、逻辑模型、工作现场配置/artifact、
  交接、协作、约束与失败；它不承担不影响正确 user-surface 实现的 Python 算法、函数名、lock 或
  cache/temp mechanics。
- Impls 完整说明 variant 的使用入口、适用条件、工作现场构造、技术方案、物理数据、代码 ownership、
  测试和 Architecture coverage，不只是代码地图。
- 项目级 Requirements 使用 `draft`、`implemented`、`approved` 三态，保留用户审阅的
  需求意图、决策、实现影响和双向依赖；只有用户可显式批准实现或回退批准状态。
- 同一事实只保留一个权威说明，其他文档通过链接引用。
- 行为变更时同步更新相关 Architecture、Impls、Skills、代码和测试。
