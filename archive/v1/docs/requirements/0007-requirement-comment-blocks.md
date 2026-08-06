# 需求 0007：Requirement 用户评论块

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0007` |
| 状态 | `approved` |
| 日期 | 2026-07-30 |
| 批准依据 | 用户于 2026-07-30 明确要求将需求 0007 转为 `approved` |
| 来源 | 用户明确要求为需求文档增加 `<comment>` 块，并与 `<question>`、`<answer>` 协作 |
| 影响范围 | 全部 Requirements、仓库文档维护规则、文档维护 Skill 与 review Skill |
| 协议关系 | 非规范性仓库治理需求；不改变 [`doctidex` 协议](../../spec/overview.md) |

本文细化 [DX-REQ-0004](0004-project-docs-and-requirement-lifecycle.md) 的 Draft 协作机制，
使用户可以直接在 Requirement 文档的相关位置留下评论，并要求 agent 在完善方案时逐项
解决。它不改变 `<question>` 与 `<answer>` 的决策职责，也不把 Requirement 协作标记
提升为 doctidex 协议语法。

## 1. 评论块语义

用户可以在 Requirement 文档中插入以 `<comment>` 开始、以 `</comment>` 结束的块，
表达针对相邻内容或整个方案的反馈、异议、修正建议或待澄清事项。

1. `<comment>` 只代表用户写入或明确授权写入的评论。agent 不得自行创建评论块、把
   agent 推断伪装为用户评论，或改写评论后仍声称它是用户原话。
2. 评论应尽量紧邻其目标内容。针对整个 Requirement 的评论可以放在相关章节开头，
   但必须保持目标明确。
3. 评论块是 Draft 协作期间的临时未解决反馈，不是最终 Requirement 历史的权威表达。
   最终记录保存吸收后的需求意图、决定与结果，不需要保留原始评论脚手架。
4. `<question>` 与紧邻的 `<answer>` 仍构成一组；`<comment>` 不得插入两者之间，避免
   破坏答案归属。

## 2. 与 question / answer 的协作

agent 完善方案前必须读取当前 Requirement 中的全部评论，并逐项判断处理路径：

| 评论类型 | 处理方式 |
|---|---|
| 可直接落实且不需要新决定 | 对照当前事实修订正文、方案、影响或验收条件。 |
| 需要用户选择或补充信息 | 将待决定事项写成 `<question>`；用户以紧邻的 `<answer>` 或对话回答。 |
| 与其他评论、既有决定或当前事实冲突 | 明确指出冲突并用 `<question>` 请求决定，不得自行选择或静默忽略。 |
| 用户明确决定不采纳 | 在正文中保留足以理解该决定的结果或理由，不把未采纳误写成已实现要求。 |

评论只有在以下条件全部满足后才算解决：

1. 相关正文已经反映评论要求，或用户已经明确决定不改变方案；
2. 评论引出的所有问题均已得到回答并吸收到正文；
3. 实现影响、依赖和验收条件已按处理结果同步；
4. 对应 `<comment>` 块已删除。

agent 不得仅回复、确认看到、移动或删除评论就把它视为已解决。若用户要求保留评论内容，
应把它整理为普通的来源、决定或结果说明；不得保留一个看似仍待处理的 live
`<comment>` 块。

## 3. 生命周期约束

1. 含有 live `<comment>` 块的非 `approved` Requirement 必须保持 `draft`，不得转为
   `implemented` 或 `approved`。
2. 用户向 `implemented` Requirement 插入评论后，该记录回到 `draft`；agent 解决全部
   评论、落实并验证方案后，才可再次标记 `implemented`。
3. 用户向 `approved` Requirement 插入评论不自动授权改写历史或回退状态。agent 必须
   请用户明确选择重新打开该记录，或创建具有双向链接的后续 Requirement，然后在获
   授权的记录中解决评论。
4. 对目录型大型 Requirement，子需求中的评论使该子需求保持 `draft`，并按
   [DX-REQ-0006](0006-large-requirement-directories.md) 的聚合门槛约束 overview；overview
   自身的评论使 overview 保持 `draft`，但不自动改写子需求状态。

## 4. 落实范围

| 层面 | 处理 |
|---|---|
| Repository rules | 定义评论所有权、与 question/answer 的配合、解决标准和状态门槛。 |
| Requirements navigation | 说明 Draft 中允许的三种协作块及完成条件。 |
| Design-document Skill | 读取、处理、移除和校验 live 评论，禁止 agent 伪造用户评论。 |
| Review Skill | 检查评论是否被实质解决，并阻止带 live 评论的记录通过完成状态检查。 |
| Architecture / Details | 本需求只改变仓库维护规则，不产生实现 Architecture 或语言 Details。 |

## 5. Requirement 关系

- 本记录是 [DX-REQ-0004](0004-project-docs-and-requirement-lifecycle.md) 的后续细化；0004
  建立 question/answer Draft 协作，本记录增加用户评论及其完成门槛。
- 本记录应用 [DX-REQ-0006](0006-large-requirement-directories.md) 已定义的 overview 聚合
  规则，但不改变 0006，也不与其建立需求依赖。

## 6. 验收标准

1. 维护规则定义 `<comment>` 只表示用户插入或明确授权的评论。
2. agent 能把评论直接吸收到方案，或在需要决定时转入 question/answer 协作。
3. 评论冲突、拒绝采纳和需要补充信息的情况都有明确处理方式，不能静默删除。
4. 任一 live 评论都会阻止 Requirement 新进入完成状态；`approved` 历史中的评论必须
   先取得明确的重新打开或后续记录决定。
5. 解决后的方案不遗留 live 评论，且正文保存必要的需求意图、决定和实现影响。
6. `implemented` 与 `approved` 记录的评论分别遵守回退和历史保护规则。
7. 相关维护 Skills 通过本地 Skill 校验。
