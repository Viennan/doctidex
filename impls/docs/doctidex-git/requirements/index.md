---
type: index
doctidex:
  type: index
---

# Requirements 导航

本目录记录 `doctidex-git` 如何从需求演进为当前设计。Requirements 是历史证据，不是
当前接口权威；当前行为应从 [Architecture](../architecture/index.md) 和
[Python Details](../details/python/index.md) 查阅。

| ID | 记录 | 来源与范围 | 状态 |
|---|---|---|---|
| 0001 | [初始 Agent Plugin 需求](0001-agent-git-plugin.md) | 原 `impls/docs/agent-git-plugin.md`；覆盖初始 user surface、工作流、实现约束和验收标准。 | Initial baseline |
| 0002 | [根自引用场景的用户提示](0002-root-self-reference-and-maintenance.md) | 用户新增并经现状核对后收敛；补充 Skills 和 CLI 关系提示，并优先合并同 source、同 effective commit 的兼容维护范围。 | Implemented |
| 0003 | [维护范围的规划与执行语义](0003-maintenance-scope-semantics.md) | 澄清 scope item 是可重复观察的对象，由 agent 制定或复核最终范围，并将协议升级到 `v0.1.0`。 | Implemented |

后续记录必须保留经用户审阅的需求意图、设计意图、接受或拒绝的方案、实现影响和最终
状态。不得为了与当前设计一致而改写已接受的历史正文；演进关系通过新记录和链接表达。
