---
type: index
doctidex:
  type: index
---

# doctidex-git 设计与实现文档

状态：Draft，非规范性实现文档

本目录记录 `doctidex-git` 当前解决的问题、对用户暴露的接口、语言无关的设计模型，
以及 Python 参考实现如何落实这些抽象。它不是 doctidex 协议正文；协议要求只以
[`spec/overview.md`](../../../spec/overview.md) 为准。

## 按阅读目的进入

| 目的 | 入口 | 内容边界 |
|---|---|---|
| 理解产品解决什么问题、如何使用 | [Architecture](architecture/index.md) | 当前 user surface、工作流、公共接口、语言无关模型和设计约束。 |
| 开发或排查 Python 参考实现 | [Python Details](details/python/index.md) | 模块职责、对象属性、调用模式、运行时、测试和已知限制。 |
| 追溯需求如何演进 | [Requirements](requirements/index.md) | 保留明确指定的初始需求基线，以及此后需求的设计与实现结果。 |

正常使用已发布插件时，应优先阅读插件自身的 Skills。Architecture 用于理解产品和
设计，Details 用于维护代码；用户或 agent 不需要理解内部 state、worktree、映射或锁
才能完成公开工作流。

## 信息层级

```text
doctidex protocol                  spec/overview.md
        |
        v
doctidex-git current design        architecture/
        |                    \
        v                     v
published agent guidance       Python reference implementation
impls/agent-plugins/.../skills  details/python/
```

箭头表示落实和约束关系，不表示下层可以改变上层语义。Skills 与 Python 实现分别落实
公开使用层和运行能力：Skills 只暴露完成任务所需的用户信息；Python Details 可以说明
内部机制，但不得把这些机制变成用户前置知识。

## 当前公共入口

- Skills：面向 agent 的自解释工作流与使用规则；
- `doctidex-git` CLI：面向人、agent 和程序的确定性命令接口；
- CLI `--json`：当前推荐的程序化集成方式；
- 原生文件、搜索、编辑和 Git 工具：始终是实际读取、修改和审阅文件的主要工具。

Python 包内的类和函数目前属于参考实现接口，不承诺为稳定的外部库 API。代码模块间
的预期调用方式见 [Python 模块地图](details/python/package-and-module-map.md)。

## 文档维护规则

- Architecture 先说明场景和 user surface，再说明内部模型；不包含 Python 文件布局、
  函数名或缓存路径。
- Details 说明当前代码事实，并链接其落实的 Architecture 抽象。
- Requirements 保留明确指定的初始基线；后续记录经用户审阅的需求意图、最终决策和
  实现影响，不以当前设计反向改写历史。
- 同一事实只保留一个权威说明，其他文档通过链接引用。
- 行为变更时同步更新相关 Architecture、Details、Skills、代码和测试。
