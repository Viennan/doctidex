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

`v1.0.0` Architecture、Python 实现与三个 Published Skills 已对齐；`0.1.0` 设计和匹配
Details 已归档。两个版本不能混作同一个当前 surface。

## 按阅读目的进入

| 目的 | 入口 | 内容边界 |
|---|---|---|
| 理解 v1.0.0 当前产品 | [Architecture](architecture/index.md) | 当前 user surface、工作流、公共接口和语言无关模型。 |
| 维护 v1.0.0 Python 实现 | [Implementation Details](details/index.md) | 当前模块、状态、算法、并发、测试与追踪关系。 |
| 排查现有 0.1.0 代码 | [Version Archive](archive/index.md) | 进入旧 Architecture 与匹配 Python Details；不是 v1 使用说明。 |
| 追溯需求如何演进 | [Project Requirements](../requirements/index.md) | 从项目级历史中查找影响 doctidex-git 的需求、状态与双向依赖。 |

正常使用已发布插件时，应优先阅读插件自身的 Skills。Architecture 用于理解产品和
设计，Details 用于维护代码；用户或 agent 不需要理解内部 state、worktree、映射或锁
才能完成公开工作流。

## 信息层级

```text
doctidex protocol                  /spec/overview.md
        |
        v
doctidex-git v1 current design     architecture/
        |                              |
        v                              v
published Skills                  Python Details
                                   details/

doctidex-git 0.1.0 code/design    archive/v0.1.0/
```

箭头表示落实和约束关系，不表示下层可以改变上层语义。当前 Skills、Python Details 与代码
落实 v1 Architecture；归档只用于排查历史，不反向定义当前行为。

## 公开入口与切换状态

- 当前 Skills：Overview、Read、Maintenance；
- 当前 `doctidex-git` CLI 与 JSON：package `1.0.0`、JSON `schema_version: "1.0"`；
- 历史 `0.1.0` surface：只在 archive 中保留设计和代码阅读线索；
- 原生文件、搜索、编辑和 Git 工具：始终是实际读取、修改和审阅文件的主要工具。

Python 包内的类和函数属于参考实现接口，不承诺为稳定的外部库 API。当前模块调用方式见
[Python `1.0.0` 实现地图](details/python/index.md)；归档模块地图只说明 `0.1.0`。

## 文档维护规则

- Architecture 先说明场景和 user surface，再说明内部模型；不包含 Python 文件布局、
  函数名或缓存路径。
- Details 说明当前代码事实，并链接其落实的 Architecture 抽象。
- 项目级 Requirements 使用 `draft`、`implemented`、`approved` 三态，保留用户审阅的
  需求意图、决策、实现影响和双向依赖；只有用户可显式批准实现或回退批准状态。
- 同一事实只保留一个权威说明，其他文档通过链接引用。
- 行为变更时同步更新相关 Architecture、Details、Skills、代码和测试。
