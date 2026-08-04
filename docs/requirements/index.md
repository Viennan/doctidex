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
[Python Impls](../doctidex-git/impls/python/index.md)。

状态只允许使用以下小写值：

| 状态 | 含义 |
|---|---|
| `draft` | 用户与 agent 正在讨论需求、完善方案。 |
| `implemented` | agent 已按当前记录完成实现，但用户尚未确认。 |
| `approved` | 用户已明确认可当前实现，可进入 PR/MR。 |

`draft` 与 `implemented` 可在批准前反复转换。只有用户的明确指令可以设置
`approved`，或将 `approved` 回退为其他状态。

Requirement 通常使用 `<NNNN>-<title>.md` 单文件记录。用户也可以为大型 Requirement
选择 `<NNNN>-<title>/` 目录：`overview.md` 保存整体描述、聚合状态与子需求导航，每份
子需求文档独立维护状态。所有子需求至少为 `implemented` 或 `approved` 时，overview
才可成为 `implemented`；只有所有子需求均为 `approved` 且用户明确批准整体时，
overview 才可成为 `approved`。详见 [DX-REQ-0006](0006-large-requirement-directories.md)。

| ID | 记录 | 来源与范围 | 状态 |
|---|---|---|---|
| 0001 | [初始 Agent Plugin 需求](0001-agent-git-plugin.md) | doctidex-git 初始 user surface、工作流、实现约束和验收标准。 | `approved` |
| 0002 | [根自引用场景的用户提示](0002-root-self-reference-and-maintenance.md) | doctidex-git Skills 和 CLI 关系提示，以及同 source/revision 范围复用。 | `approved` |
| 0003 | [维护范围的规划与执行语义](0003-maintenance-scope-semantics.md) | doctidex-git scope 观察语义与协议 `v0.1.0` 维护边界。 | `approved` |
| 0004 | [项目文档组织与 Requirement 生命周期](0004-project-docs-and-requirement-lifecycle.md) | 根级 docs、共享 Requirements、三态生命周期、双向依赖和默认 review 范围。 | `approved` |
| 0005 | [协议升级至 v1.0.0](0005-protocol-v1-0-0.md) | 移除 mount 与旧 flags，保留最近负责制并重构根内 link、边界和索引语义。 | `approved` |
| 0006 | [大型 Requirement 目录与聚合状态](0006-large-requirement-directories.md) | 大型需求的目录形式、子需求独立状态与 overview 聚合门槛。 | `approved` |
| 0007 | [Requirement 用户评论块](0007-requirement-comment-blocks.md) | 用户在需求文档中插入的评论、question/answer 配合与完成门槛。 | `approved` |
| 0008 | [doctidex-git 与协议 v1.0.0 对齐](0008-doctidex-git-v1-0-0-alignment/overview.md) | 分阶段完成三 Skill Architecture，以及 Python validation、外部 Git 与 worktree 实现。 | `approved` |
| 0009 | [Architecture 与 Impls 文档维护规则调整](0009-architecture-and-details-maintenance-rules.md) | 建立 Architecture / Impls 基准，并将 Requirement、Architecture、Impls 维护规则拆分为专用 Skills。 | `approved` |
| 0010 | [修复 restore 生成无效 runtime record](0010-fix-restore-runtime-record.md) | 修复 restore 遗漏 `requested_default` 后产生不可读 runtime state 的 Python bug。 | `approved` |
| 0011 | [优化 doctidex-git Skill 文档内容](0011-optimize-doctidex-git-skill-documentation.md) | 梳理并优化 doctidex-git Published Skills 的内容、阅读路径与使用引导。 | `approved` |
| 0012 | [增加 doctidex-git external remove 命令](0012-doctidex-git-external-remove.md) | 以 `INSTALL_ID` 移除 owner root 的受管 external install，并保护可见引用且不处理 shared Git cache。 | `approved` |
| 0013 | [增加 doctidex-git cache clean --auto](0013-doctidex-git-cache-clean-auto.md) | 自动枚举 shared bare Git cache，并仅回收无有效 linked worktree 的 cache；不修改 Published Skills。 | `approved` |
| 0014 | [增加 doctidex-git checkout Git hook 命令](0014-doctidex-git-checkout-hook.md) | 以 `hook --install` 配置 checkout 后 direct/dependency install 的 commit 与 revision metadata 对齐，并以 hidden dependency 保留无法安全确定 revision 的子树。 | `approved` |
| 0015 | [Architecture 与 Impls 文档重构](0015-architecture-and-impls-document-principles.md) | 以可解释的跨变体工作现场、强直接 evidence、独立全知复核与中文逻辑组织为基准，重构 Architecture / Impls 职责、当前文档和作者规则。 | `approved` |
| 0016 | [在 doctidex-git Skill 中引导主动执行 hook run](0016-doctidex-git-hook-run-skill-guidance.md) | 在 `post-checkout` hook failure/warning 的可恢复问题解决后，引导 agent 直接运行 `hook --run` 重试协调，无需通过无业务目的的 `git checkout` 间接触发。 | `approved` |

新记录按全项目连续编号。`draft` 中可使用 `<question>` 与紧邻的 `<answer>` 块协作；
用户也可以用 `<comment>...</comment>` 在相关位置留下评论。agent 不得代用户创建评论，
必须将每项评论吸收到方案，或通过 question/answer 获得所需决定。答案被方案吸收后应
删除 question/answer；所有评论得到实质解决并删除其块之前，非 `approved` 记录必须
保持 `draft`。`approved` 记录中的评论需要用户明确决定重新打开或创建后续记录。每一项
Requirement 依赖必须在关系两端都提供可导航链接，不能只在本索引中表达。
