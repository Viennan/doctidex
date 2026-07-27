# Architecture 导航

Architecture 描述 `doctidex-git` 当前是什么样子。它以 user surface 为起点，随后解释
支撑这些接口的语言无关模型、子系统职责和设计约束。

## 推荐阅读顺序

1. [User Surface](user-surface.md)：问题、使用者、心智模型和公开/内部边界。
2. [用户工作流](workflows.md)：每个预期场景如何使用接口完成任务。
3. [CLI 用户接口](interfaces/cli.md) 与 [结果契约](interfaces/cli-schema.md)：精确命令和字段。
4. [程序集成](interfaces/programmatic-integration.md)：如何把 CLI 作为确定性组件组合。
5. [领域模型](domain-model.md)：公开与内部概念及全部属性。
6. [子系统与生命周期](subsystems-and-lifecycles.md)：职责、依赖和状态变化。
7. [约束与失败模型](constraints-and-failures.md)：安全、网络、写入、输出和错误边界。
8. [Skill 系统](skill-system.md)：agent surface 的分工和写作约束。

## Architecture 的边界

- 描述场景、接口、可观察结果、概念模型、职责和不变量。
- 不绑定 Python 模块、类、函数、XDG 路径或具体文件系统映射技术。
- CLI 语法与 JSON schema 属于公共接口，因此可以精确记录。
- Python 如何解析、持久化或呈现这些概念见 [Python Details](../details/python/index.md)。

文档中的“用户”包括直接操作的人、执行 Skill 的 agent，以及消费 JSON 的程序。
