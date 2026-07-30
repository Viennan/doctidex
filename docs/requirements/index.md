---
type: index
doctidex:
  type: index
---

# Requirements 导航

本目录是项目共用的 Requirements 历史。每份记录标明受影响的实现或仓库 surface，
并用双向链接保存依赖、细化、取代和后续关系。Requirements 解释意图与演进，不替代
当前接口权威；doctidex-git 的当前行为见
[Architecture](../doctidex-git/architecture/index.md) 和
[Python Details](../doctidex-git/details/python/index.md)。

状态只允许使用以下小写值：

| 状态 | 含义 |
|---|---|
| `draft` | 用户与 agent 正在讨论需求、完善方案。 |
| `implemented` | agent 已按当前记录完成实现，但用户尚未确认。 |
| `approved` | 用户已明确认可当前实现，可进入 PR/MR。 |

`draft` 与 `implemented` 可在批准前反复转换。只有用户的明确指令可以设置
`approved`，或将 `approved` 回退为其他状态。

| ID | 记录 | 来源与范围 | 状态 |
|---|---|---|---|
| 0001 | [初始 Agent Plugin 需求](0001-agent-git-plugin.md) | doctidex-git 初始 user surface、工作流、实现约束和验收标准。 | `approved` |
| 0002 | [根自引用场景的用户提示](0002-root-self-reference-and-maintenance.md) | doctidex-git Skills 和 CLI 关系提示，以及同 source/revision 范围复用。 | `approved` |
| 0003 | [维护范围的规划与执行语义](0003-maintenance-scope-semantics.md) | doctidex-git scope 观察语义与协议 `v0.1.0` 维护边界。 | `approved` |
| 0004 | [项目文档组织与 Requirement 生命周期](0004-project-docs-and-requirement-lifecycle.md) | 根级 docs、共享 Requirements、三态生命周期、双向依赖和默认 review 范围。 | `approved` |
| 0005 | [协议升级至 v1.0.0](0005-protocol-v1-0-0.md) | 移除 mount 与旧 flags，保留最近负责制并重构根内 link、边界和索引语义。 | `approved` |

新记录按全项目连续编号。`draft` 中可使用 `<question>` 与紧邻的 `<answer>` 块协作；
答案被方案吸收后应删除这些块，除非用户明确保留。每一项 Requirement 依赖必须在关系
两端都提供可导航链接，不能只在本索引中表达。
