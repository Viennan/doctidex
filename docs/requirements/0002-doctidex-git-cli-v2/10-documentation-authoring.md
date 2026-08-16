# 需求 0002-10：user / architecture 文档编写

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002-10` |
| 状态 | `implemented` |
| 日期 | 2026-08-16 |
| 来源 | 用户要求专门确定 user / architecture 文档编写问题 |
| 父需求 | [需求 0002：设计 doctidex-git 命令行工具 v2.x.x](overview.md) |
| 关联子需求 | [需求 0002-01](01-cli-arguments-results.md) 至 [需求 0002-09](09-repair.md) |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)、[doctidex-git v2 Architecture](../../architecture/doctidex-git-v2.md) |
| 影响范围 | `docs/user/`、`docs/architecture/`、`AGENTS.md` 及相关文档 Skills |
| 文档性质 | 子 Requirement；确定文档定位、组织与编写要求，并记录交付完成证据 |

## 1. 需求意图

确定 doctidex 的 user 文档与 Architecture 文档的定位、权威边界、内容组织、表达原则和后续交付要求。

本文为 user 与 Architecture 文档、相关维护规则和 Skills 调整提供需求依据。实际交付物见第 7 节和
第 9 节。

## 2. 设计依据

- 父需求 [0002 overview](overview.md) 已确认，代码库开发完成后需要交付 user 与 Architecture 文档；
  Architecture 文档应重新组织语言和结构，并整合各子需求中分散的有效设计信息。
- 父需求先前排除 user 文档撰写的决定已作废。本次需求完成代码库开发后，必须同时交付 user 与
  Architecture 文档。
- `AGENTS.md` 当前将 `docs/architecture/` 表述为产品当前状态的权威描述；该表述需要在后续维护中与本文
  的 user-surface 权威边界保持一致。
- 文档 Skills 应记录文档维护的操作规则，而不承载产品或仓库的具体事实；具体事实仍由对应文档作为权威来源。

## 3. 文档范围与角色

### 3.1 user 文档

`docs/user/` 是产品 user surface 的权威文档位置，说明用户在使用产品时可见、可调用或需要据以处理的
信息，包括：

- 命令行命令、参数、返回结果与退出语义等 CLI 接口契约；
- 错误处理与诊断使用方式；
- 使用场景、预期使用模式及其他操作指引。

### 3.2 Architecture 文档

`docs/architecture/` 记录产品当前的设计思路和实现架构。它是架构、设计约束、模块职责与取舍的权威来源，
不再承担 user surface 的完整权威说明。

Architecture 文档还应说明产品所要解决的问题、演进方向和长期目标，使设计选择可以在其产品语境中被理解。

### 3.3 权威边界与维护规则

Requirements 记录增量设计过程，不替代 user 或 Architecture 文档对其各自领域的权威说明。代码准确表现
当前实现，但不能单独表达模块不应承担的职责、设计约束和取舍；Architecture 文档需要明确这些边界。

后续应调整 `AGENTS.md` 的文档角色表述，以及 `user-docs`、`write-architecture-docs` 等相关文档 Skills，
使其与本节的权威边界一致，并删除不协调或重复的说明。

## 4. 完整设计视角与文档组织

user 与 Architecture 文档必须从产品当前完整、已知的设计形态反向组织，而非沿用 Requirement 的编号、子需求或
迭代顺序。Requirement 记录设计逐步形成时的局部决策；在其编写过程中，无法预先依赖最终形态来组织内容。文档
编写阶段已经掌握完整设计，因此应利用这一视角，选择更符合读者理解路径、模型关系和稳定产品边界的结构。

Requirement 是确认事实和追溯设计来源的输入，不是 user 或 Architecture 文档的目录模板。两类文档应分别按其
读者和目标组织：user 文档围绕完整的 user surface、使用路径和决策；Architecture 文档围绕完整的产品模型、
责任和工作流。不得因为某项设计分散在多个子需求中，就在最终文档中保留该分散结构。

此原则应同步写入 `user-docs` 与 `write-architecture-docs` Skills，作为两类文档的共同编写约束。

## 5. Architecture 文档要求

Architecture 文档的组织应从稳定的产品模型和设计关系出发，不照搬 Requirement 的编号或阶段结构。其内容
包括但不限于：

- 产品问题、架构纵览、演进方向与长期目标；
- 工作模型与工作区设计；
- RuntimeStore、CacheStore、Git cache 与事务设计；
- 模块职责、设计约束、已作取舍及其理由。

例如，Architecture 文档应区分 CacheStore 对缓存记录和 bare repository 存在性的可恢复保护，与 Git
fetch 等不可回滚的外部副作用；也应明确 `repair` 的目标是让仓库回到可继续工作的合规状态，而非恢复到
故障或事务中断前的历史状态。

Architecture 文档不得罗列具体实现代码的执行步骤。需要帮助读者定位实现时，可直接链接相关源码；设计说明
本身应集中解释模型、责任、约束和取舍。职责与约束应随架构演进维护，并为后续迭代与 review 提供判断依据。

## 6. User 文档要求

### 6.1 命令簇文档

每个命令簇必须完整说明其使用方式、参数和结果格式。user 文档必须同时按信息深度和命令簇组织，
使读者能够只加载当前要使用的命令簇文档：

- `init`、`boundary-set`、`import`、`worktree`、`validate` 和 `repair` 均必须有各自的文档入口；
  一个命令簇的子命令可在同一篇文档中组织。
- 命令簇文档必须包含该簇的完整调用方式、参数、结果和相关的用户可处理错误；共同接口可链接到
  公共参考，不在每篇命令簇文档中重复。
- overview 和诊断/恢复等跨命令主题可以独立成文，并通过链接将读者引导到所需命令簇文档；不得要求
  为查阅一个命令簇而顺序阅读所有其他命令簇的说明。

在此基础上，文档可按但不限于以下层次提供信息：

1. 面向高频使用路径的 quick start 或 overview；
2. 完整使用文档，严谨说明全部参数及命令在不同场景下的行为；
3. 错误处理文档。

### 6.2 整体 overview

整体 overview 应简洁、准确地建立使用者需要的 doctidex 目录树心智模型，并说明必要的使用注意事项。它可
适量介绍有助于理解 doctidex-git 使用方式的架构背景，例如工作区和 Git cache，但必须控制篇幅，不替代
Architecture 文档的详细设计说明。

### 6.3 导航

user 文档应善用 Markdown link 建立知识网络。overview 必须导航至每个命令簇文档；命令簇文档应在需要时
链接共同接口、诊断/恢复说明和 Architecture 中的对应权威说明。

## 7. 交付与验证

user 与 Architecture 文档均应以准确、简洁为目标，不用冗长文字穷尽信息。应在确有助于理解关系、流程、
层级或接口时使用 Markdown 可渲染的图表、表格和代码块。

本次需求已交付 Architecture 文档，并同步更新 `AGENTS.md` 及相关文档 Skills。已有单篇 user 指南将被
重组为以下文档：

- 一个 overview，建立心智模型、前提和常见使用路径，并导航至其余文档；
- 一个共同接口与恢复说明，集中定义 Git root、仓库内部路径、缓存配置、JSON envelope、退出码、通用错误
  和跨命令恢复边界；
- 分别面向 `init`、`boundary-set`、`import`、`worktree`、`validate`、`repair` 的六篇命令簇文档。

命令簇文档可链接共同接口与恢复说明，但必须独立完整说明其命令。审阅验证包括链接、术语一致性、命令接口
覆盖和从 overview 到每个命令簇入口的可达性检查。

## 8. 验收标准

- [x] user 与 Architecture 文档的权威边界已定义。
- [x] user 文档的命令簇、整体 overview、错误处理与导航要求已定义。
- [x] Architecture 文档的范围、表达重点、职责/约束/取舍要求已定义。
- [x] 两类文档的简洁表达和图表/表格/代码块使用原则已定义。
- [x] `AGENTS.md` 与相关文档 Skills 的后续同步要求已记录。
- [x] user 与 Architecture 文档实际撰写均属于需求 0002 的交付范围。
- [x] 两类文档从完整设计视角组织、不照搬 Requirement 增量结构的原则已定义。
- [x] `user-docs` 与 `write-architecture-docs` Skills 的对应同步要求已记录。
- [x] 每个顶级命令簇均有可独立按需加载的 user 文档入口，并完整覆盖该簇的调用、参数、结果和可处理错误。
- [x] overview 可导航至全部命令簇文档，共同接口和诊断/恢复信息按需链接而非集中阻塞阅读。
- [x] [doctidex-git v2 Architecture](../../architecture/doctidex-git-v2.md) 已交付，覆盖模型、状态、工作流、约束和实现责任。
- [x] user 文档已交付为 overview、共同接口与恢复说明及六篇命令簇文档；已检查调用、参数、结果、错误、导航链接和术语与当前 CLI 实现一致。

## 9. 实施与状态

本子需求为 `implemented`。Architecture 文档、相关规则同步以及 user 文档均已完成。user 文档由
[overview](../../user/doctidex-git-v2.md)、[共同接口与恢复说明](../../user/doctidex-git-v2/common.md) 及
`init`、`boundary-set`、`import`、`worktree`、`validate`、`repair` 六篇命令簇文档组成；overview 可直接
导航至全部入口，每篇命令簇文档可独立阅读，并按需链接共同接口、诊断/恢复与相邻命令簇。
