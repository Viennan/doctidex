---
type: index
doctidex:
  type: index
---

# doctidex-git v1.0.0 架构

状态：当前 `v1.0.0` 设计；Python 实现与 Published Skills 由
[DX-REQ-0008.2](../../requirements/0008-doctidex-git-v1-0-0-alignment/02-python-details-and-implementation.md)
落实。

本目录从用户 surface 出发，定义 doctidex-git 面向 doctidex 协议 `v1.0.0` 的语言无关
设计。当前 Python `1.0.0` 代码地图见 [Details](../details/index.md)；先前 `0.1.0` 设计与
实现说明只保留在[版本归档](../archive/v0.1.0/index.md)，不构成当前 surface。

其中 external install/link/restore 与 worktree 生命周期是 agent 可选择的受管产品工作流，
不是读取、安装、维护或协议符合性的强制入口。agent 也可以使用原生 Git、手工 worktree、
submodule、symlink 或其他适合任务的方法；受管路径、恢复和关闭承诺只覆盖 doctidex-git
创建或登记的对象。

此外，CLI 为 human/program operator 提供独立的 shared bare source cache 清理接口。该接口
不是 Published Skill 工作流，不选择 doctidex root，也不改变任何 root-owned payload、
manifest 或 runtime record。

## 文档职责

| 文档 | 权威内容 | 不重复的内容 |
|---|---|---|
| [用户接口](user-surface.md) | 产品定位、使用者、场景、心智模型和责任边界。 | 命令参数、JSON 字段和内部机制。 |
| [用户工作流](workflows.md) | 任务选择、操作顺序、可观察结果和失败后的下一步。 | 字段清单、identity 属性和发布算法。 |
| [CLI 用户接口](interfaces/cli.md) | 精确 invocation、参数约束、省略行为、读写与网络效果。 | JSON 字段类型和内部生命周期。 |
| [CLI JSON Schema](interfaces/cli-schema.md) | envelope、operation payload、字段类型、枚举、failure code 和退出码。 | 教程步骤和内部存储。 |
| [领域模型](domain-model.md) | 公开/内部概念、全部属性、关系和不变量。 | 命令执行顺序与用户教程。 |
| [子系统与生命周期](subsystems-and-lifecycles.md) | 语言无关子系统、依赖、状态变化、并发和非原子边界。 | Python 模块和用户参数说明。 |
| [约束与失败](constraints-and-failures.md) | 跨工作流安全约束、失败信息、保留原则和人工升级边界。 | 逐命令矩阵和重复 failure schema。 |
| [Skill 系统](skill-system.md) | Published Skills 的分工、阅读链、信息暴露和发布要求。 | 普通产品文档或内部实现说明。 |
| [程序集成](interfaces/programmatic-integration.md) | 程序如何组合稳定 CLI/JSON surface。 | 重定义 schema 或依赖 Python import。 |

首次了解产品按表格自上而下阅读。已知任务从[用户工作流](workflows.md)进入；实现者先读
公开 CLI/Schema 和领域模型，再进入子系统生命周期与跨工作流约束。

## 权威边界

- 协议语义只由 [`spec/overview.md`](../../../spec/overview.md) 定义。
- 本 Architecture 是 doctidex-git `v1.0.0` 的当前产品契约。
- [DX-REQ-0008.1](../../requirements/0008-doctidex-git-v1-0-0-alignment/01-doctidex-git-alignment.md)
  保存该设计的需求来源与决策历史。
- Python 模块、storage、算法、锁和测试属于 [Details](../details/index.md)。
- `0.1.0` 的 Architecture 与 Details 已成套进入 [archive](../archive/index.md)。
