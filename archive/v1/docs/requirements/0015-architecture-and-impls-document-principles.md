# 需求 0015：以可解释的跨变体工作现场重构 Architecture 与 Impls

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0015` |
| 状态 | `approved` |
| 日期 | 2026-08-03 |
| 来源 | 用户基于 DX-REQ-0009 后的维护经验，要求以不同实现变体能够接手同一产品工作现场为 Architecture 完整性的评判基准；随后进一步要求以真实工作现场、Architecture-only 读者和全知独立复核者构成强制验证，并要求检查文档是否以中文组织逻辑、避免大段纯英文说明。 |
| 影响范围 | `docs/` 的 Architecture / Impls 定位、语言组织与导航、Requirement / Architecture / Impls 作者 Skill、当前 `doctidex-git` Architecture / Python Impls、其 archive 基线、导航和 Markdown links。 |
| 协议关系 | 非规范性文档治理与产品设计重构；不改变 [`doctidex` 协议](../../spec/overview.md)。 |

## 1. 背景与目标

[DX-REQ-0009](0009-architecture-and-details-maintenance-rules.md) 已确立 Architecture 为跨实现共同设计、Impls 为条件化 realization 的模型，并完成一次从旧页面边界出发的重构。该模型继续成立，但现有规则对“哪些事实必须成为共同设计、何时必须停止局部补丁而重新组织文档”的判断仍不够直接。

当前 `hook` 并非完全没有系统说明：它已有 [CLI](../doctidex-git/architecture/interfaces/cli.md#10-hook)、
[JSON result](../doctidex-git/architecture/interfaces/cli-schema.md#65-hook_install-与-hook_run)、
[external workflow](../doctidex-git/architecture/external-snapshots-and-presentations.md#6-受管-checkout-hook)、
[Python realization](../doctidex-git/impls/python/components/checkout-hook-reconciliation.md)
和 [coverage/test](../doctidex-git/impls/python/architecture-coverage-evidence-and-worksite-validation.md#1-capability-coverage)
authority。因而本 Requirement 不把问题记录为“缺少 hook 文档”，而是解决更一般的缺口：重大能力即使已有分散段落，也必须能从共同模型、工作现场、跨变体行为和完整阅读路径获得连贯解释，不能只凭对既有页面的增量补充维持表面覆盖。

本次重构以“可解释的跨变体工作现场”作为 Architecture 实现无关性的强制检验。假设存在一个非 Python 的 `doctidex-git` variant：它应能只依据 Architecture 理解 Python variant 已经通过 user surface 留下的工作现场；Python variant 也应能对等地理解另一符合 Architecture 的 variant 留下的工作现场。若某个存在于工作现场的配置文件、配置选项、artifact、状态或操作结果只能从 Impls 或 source 推断，Architecture 就尚未完整定义产品。

最小 diff 是控制改动风险的手段，不是文档质量目标。关键概念、状态机、工作流或交接边界已经足够稳定且影响产品理解时，作者必须先判断是否需要系统性重组、增设 authority 或重写阅读路径；不得因“少改已有文档”而让读者只能在零散页面中自行拼接产品设计。

已有 user surface 要求和 Impls 的基本定位保持有效。本 Requirement 的目标是在不把 Architecture 变成源码转写的前提下，令它完整定义产品的共同设计、工作现场语义和交接规则，并使 Impls 清楚说明每个 variant 如何落实、接入和维护该设计。

## 2. Architecture 的职责与定位原则

### 2.1 完整定义跨变体产品

Architecture 是产品的实现无关定义，而不是某一 variant 的摘要。它必须完整说明所有符合要求的 variant 共同承诺的 user surface space、领域与逻辑数据模型、状态 ownership、主要机制、工作流、可观察结果、失败与恢复边界、兼容性和非目标。语言绑定、package、module、算法和平台技巧仍可不同。

“完整”以跨变体接手检验，而不以是否列出全部源代码事实检验。对一个由 variant A 留下的工作现场，variant B 应能根据 Architecture 确定下列事项：

| 交接对象 | Architecture 必须定义的共同事实 |
|---|---|
| User surface | 可用能力、输入类别、默认值、权限、结果、失败和下一步；若调用语法或 result schema 本身要求跨变体兼容，也定义其稳定 contract。 |
| 工作现场中的配置文件 | 每个文件的 identity、位置、owner、存在条件、lifecycle、每个选项的含义、允许状态、影响与 unknown/migration 处理。 |
| 工作现场中的 artifact | producer、consumer、用途、可用方式、与配置和 workflow 的关系、保留/清理/恢复边界。 |
| 配置产生的行为 | 操作如何读取和改变 state，何时产生部分成功、阻塞、重试、恢复或需用户决策的结果。 |
| 交接与兼容 | 哪些 state 可直接读取、应如何解释、何时必须转换、保留或拒绝，以及读写后仍须保持的 observable semantics。 |
| 共同架构 | 支撑这些承诺的关键模型、依赖与协作关系；所有 variant 遵循同一设计，而不必拥有同样的内部组件。 |

“无缝接手”不要求复用对方的语言运行时、库或算法，但不允许把存在于 user-surface 工作现场的配置或 artifact 留作 Architecture 无法解释的黑箱。某种 representation 若必须由不同 variant 无转换地读写，Architecture 必须定义其位置、schema、version 和 compatibility contract。若允许格式或 layout 不同，Architecture 仍必须对实际出现的文件、选项和 artifact 给出直接语义，并定义转换、保留或拒绝接手的责任；具体 encoding、locking 和写入 mechanics 由 Impls 说明。

对会遗留在 host repository 或产品工作现场的宿主副作用同样适用。例如，若一个 variant 应接手另一个 variant 安装的 hook，Architecture 必须定义 managed identity、owner、version/compatibility、conflict、replacement 或 migration 的共同语义；实际 shell script、filesystem write、lock 与 executable handling 仍由 Impls 负责。

Architecture 的充分性有明确上限：它必须提供独立 variant 正确实现 user surface 所必需的语义与约束，但不要求、也不应承载当前 variant 中不改变该正确性的执行细节。局部算法、调用编排、lock、cache 或临时布局、函数或模块边界和性能优化等，若不改变输入、默认值、配置或 artifact 语义、可观察结果、失败、恢复、交接、兼容性或安全边界，属于 Impls 或 source 的 realization evidence。Architecture 省略此类 mechanics 不是完整性 gap。

### 2.2 用工作现场证明 Architecture 可解释

实施时必须从每个当前 Impls variant 构造其 user surface 能产生或保留的全部语义不同的工作现场类别，包括正常、部分成功、blocked、recovery、迁移/兼容、损坏或隐藏等能遗留不同配置或 artifact 的状态。一个场景必须在隔离 fixture 中暴露该操作实际写入或保留的 selected root、host repository、managed path、variant cache 和其他工作位置，而不接触真实用户凭据或环境。可以把等价场景合并，但必须由 Impls/source/test evidence 证明它们留下的文件、选项、artifact、状态和用户可观察影响相同；不得用少数 happy path 代替状态覆盖。

每个场景由掌握 Impls 的执行者以实际 variant 构造，保留工作现场、其 user-visible action/result transcript 和可定位的 variant 标识。随后由一个受限的 Architecture reader subagent 读取该工作现场、用户可见 transcript 和当前 Architecture；它不得读取 Impls、source、tests、Requirement、构造记录或其他审查报告。

Architecture reader 必须从场景实际可见的文件系统递归盘点文件和 artifact，不能把未知路径直接视为无关；它应逐项列出每个 variant 留下且实际存在的配置文件，并解释每个出现选项的含义、影响和可用/处理方式；scenario matrix 合并后必须覆盖该 variant 能在工作现场 materialize 的每个选项和状态。它也必须解释每个实际 artifact 的 producer、consumer、作用、如何使用、关联配置和 lifecycle。低层文件只有在 Architecture 直接将其归入一个已解释的 artifact 并定义其不单独承载配置语义时，才可作为该 artifact 的组成内容；不得把未解释的配置文件伪称为 opaque internal data。每项解释都必须引用 Architecture 中强且直接的 evidence：该 evidence 应明确规定对应文件、选项、artifact 或语义，不能只凭名称猜测、间接拼接多个无关段落，或以 Impls/source link 代替 Architecture authority。

另一个与 Architecture reader 独立的全知 verifier subagent 必须读取 applicable Requirements、Architecture、全部 Impls、source、tests、public surfaces、场景构造事实和 reader 输出，逐项判断：reader 所引 evidence 是否真实支持结论，是否存在编造或牵强推断，以及其对文件、选项、artifact 和功能的理解是否正确、完整。只要 verifier 无法证实某个必要解释，或 reader 必须越过 Architecture 才能完成理解，该项即为 Architecture gap；不得以 verifier 的全知解释替 Architecture reader 补洞。

功能理解的正确性以“足以正确实现 user surface 行为”为界：reader 的信息应能支撑符合 Architecture 的 variant 正确处理输入、默认值、配置和 artifact、可观察结果、失败、恢复、交接与安全边界，但不要求推导当前 variant 背后的全部执行步骤、局部算法、调用链、lock 或其他不改变上述行为的 mechanics。verifier 应据此判断 reader 的理解是否足够，不能把未复现 source 内部细节本身判为 gap。

### 2.3 以可读的领域建模组织共同设计

Architecture 可以借鉴领域驱动设计（DDD）的共同语言、模型边界、state owner 和协作关系，但不以套用 DDD 术语、模式或页面模板为目标。建模应服务于读者对产品的判断：稳定概念为何存在、由谁拥有、与哪些概念组合、在何种 workflow 中变化，以及其失败或兼容边界是什么。

共同模型应从跨 variant 的 user scenario、工作现场和行为协作中导出，而不是从 Python class、JSON field 或目录树逐项提升。反过来，任何会决定跨变体如何解释配置、接续状态、使用 artifact 或产生用户可观察结果的模型，不能仅因当前只有 Python 实现而停留在 Impls。文档应使用清晰、连贯的叙述和必要的表、图或状态转换表达模型关系，避免形而上学的分类或无助于决策的术语堆砌。

### 2.4 重大能力需要完整的共同叙述

引入或显著改变能力时，Architecture 先确定它是否带来新的共同 user decision、持久状态、配置文件、artifact、身份、生命周期、协作边界或兼容性承诺。若带来，文档必须在合适的 model、workflow 或 dedicated authority 中完整说明这些事实，并从 product/user surface 建立可发现的阅读路径。CLI command、JSON fields 或现有流程中的附加段落可以链接该 authority，但不能成为读者理解该能力唯一依赖的拼图。

## 3. Impls 的职责与定位原则

Impls 仍是一个明确语言、runtime、platform 或 deployment 条件下的完整 realization 设计。它不重新定义产品共同语义，而是说明该 variant 如何接入 Architecture、采用什么组件和 physical state、为何做出这些工程选择，以及使用者和维护者如何验证、诊断、扩展和恢复它。

面对跨变体接手，Impls 至少应说明：

1. variant 如何构造每类 user-surface 工作现场，并为验证提供覆盖 inventory、场景构造步骤和实际留下的文件、选项、artifact 与状态；
2. shared state 在本 variant 的具体 representation、代码 owner、publication/recovery、source/test evidence，以及它与其他 variant 交接时的映射；
3. 每个留在工作现场的配置文件和 artifact 如何对应 Architecture 的直接 authority；即使 serialization 或 layout 是 variant-specific，也不能把其选项语义留作 reader 无法理解的私有知识；
4. 哪些 cache、临时文件、lock、library 或 platform behavior 不会作为 user-surface 工作现场的配置或 artifact 出现，因而可以保持私有，以及 supporting evidence；
5. Architecture 允许的 variant choice、实际 limitation 或 interoperability gap 分别是什么。若共同语义尚未定义，Impls 必须路由回 Architecture，而不能自行填补。

Impls 不是薄代码地图，也不应为证明实现细节而逐行转写 source。它应在逻辑共同设计与当前代码之间建立可维护的 realization path：从 variant 条件和 user entry，到关键组件与 physical state，再到 effects、failure/concurrency/recovery 和代表性 evidence。自解释的 helper、临时对象与局部算法可直接链接到 source 或 tests。

## 4. 两层的边界与协作规则

| 事实或决定 | 唯一正文 authority |
|---|---|
| 产品共同能力、user decision、可观察语义、关键模型、逻辑 state、跨变体状态转换与兼容性 | Architecture |
| user surface 工作现场中实际存在的配置文件、每个选项和 artifact 的身份、语义、影响、使用与 lifecycle | Architecture；Impls 定义具体构造、representation、代码 owner 与 mechanics。 |
| 另一 variant 必须直接读写的 physical interoperation schema、version、位置或 format | Architecture；具体 parser/storage realization 由 Impls 说明。 |
| 不作为 user-surface 工作现场的配置或 artifact 出现，且不改变 user surface 正确实现或其解释的纯局部 cache、临时文件、lock、library、算法和平台处理 | 对应 Impls 或 source，并由 Impls 证明其私有边界。 |
| 将共同逻辑 state 映射到 variant physical state、处理 migration 或解释私有 state 的具体策略 | 对应 Impls，并链接 Architecture 的共同 contract。 |
| 尚未实现或尚未确认的共同能力、交接语义、数据兼容策略或产品取舍 | `draft` Requirement |

工作现场验证同样是决定概念归属的 promotion rule：只要 Architecture reader 为解释场景中的文件、选项、artifact、状态或功能而需要某个 Impls/code 概念，该概念或其所需语义必须进入 Architecture。一个概念只有在全知 verifier 证明它不影响任何 user-surface 工作现场的识别、含义、使用、状态转换、恢复或安全边界时，才可留在 Impls/source。不得以“当前只有一个 variant”或“实现细节”跳过该判断。

同一事实不得在两层以互相独立的表述重复定义。Architecture 定义“所有 variant 必须理解和保持什么”；Impls 定义“当前 variant 怎样做到，以及哪些 mechanics 只在此条件下成立”。实现、tests 和 Published Skills 是相应 authority 的 evidence 或交付物，不能静默改写上层设计。

变更按以下顺序路由：新目标或未决取舍先进入 Requirement；共同产品语义、工作现场或交接边界改变时，先更新 Architecture，再评估每个 Impls variant；仅一个 variant 的内部 realization 改变时更新该 Impls、代码和 tests，只有暴露新的共同契约时才回到 Architecture。重构前先盘点事实 owner、工作现场和阅读路径，再决定页面迁移、合并、拆分或重写，不能把已有文件边界当作设计边界。

## 5. 授权的重构范围与方法

实施须将本 Requirement 与仍有效的 DX-REQ-0009 原则整合为唯一、无冗余的当前 authoring guidance。过时、重复或会诱导机械小修补的规则应删除或改写，但不得弱化 Requirement lifecycle、用户授权、approved-history、Published Skill audience、当前文档优先或 materiality boundary。

当前 `doctidex-git` 是唯一已有 Architecture 与 Impls variant 的 artifact，应以当前 Python implementation、tests、public CLI/JSON surface 和 Published Skills 为事实证据，先建立产品 state、工作现场、交接边界、主要 workflows 与 variant realization 的 authority inventory。接着从零规划当前 Architecture / Python Impls 的目标树、唯一 facts 和阅读路径；现有页面只能作为证据和迁移材料，不能限制目标结构。目标树收敛后再写入当前文档、更新导航和修复 links。

inventory 必须至少对 portable manifest、runtime、hidden dependency state、managed `post-checkout` hook、payload、worktree、cache、lock、diagnostic 与其他可由 user surface 留下的配置/artifact 作出工作现场分类。每项分类都要明确共同语义、variant responsibility、直接 Architecture evidence 和交接结果，不能以“当前只有 Python”或“已有一段说明”为理由跳过。

重写前，将当前 `docs/doctidex-git/architecture/` 与 `docs/doctidex-git/impls/` 保存为非发布版本的 archive baseline，建议路径为 `docs/doctidex-git/archive/baselines/pre-dx-req-0015/`。baseline 及其所有保留页面统一标注 `format-illegal`：这是本 Requirement 定义的非协议文档治理标签，表示该快照不按本次新的 current Architecture / Impls authority、完整性、阅读路径和工作现场验证标准判定为合格；它仍是可读的历史证据，但不定义当前产品。`format-illegal` 不表示 Markdown、doctidex protocol 或产品行为无效，也不等同于或触发 `doctidex.unsafe`。baseline 仍须作为普通 safe doctidex 内容保持连续 `index.md`、可达导航和有效 links；标注的具体 Markdown 或自定义 metadata 形式必须一致、可导航，并且不得为 `doctidex` 配置增加未定义语义。

用户已授权修复本次重构涉及的文档 links。对 approved Requirement 或 archive 的修改仍仅限于唯一 successor 的机械 link repair，不得改变历史状态、术语、意图、决策或结果；未有唯一 successor 时必须保留并报告该差异。代码、tests 或 Published Skills 若显示出真实产品 gap，须先记录为本 Requirement 的具体差异或单独的后续 Requirement，不得借文档重构静默改变行为。

当前 `docs/` 中的说明性内容必须以中文承担逻辑组织：标题、段落、表格中的判断、关系、原因和结论应由中文表达。英文可保留为 identifier、命令、路径、schema/field、代码符号、固定技术术语或必要引用，但不能单独承担一段解释性 prose。中文标题或短引导语后紧接大段纯英文叙述同样不合格。该规则不要求机械翻译代码、协议字面量或行业中更精确的既定英文术语；只要求读者能从中文句法和论证链条理解它们的作用。每次创建、重写或实质修订当前 `docs/` 内容时，作者必须人工检查这一边界，并在相关 Requirement、Architecture 与 Impls Skill 的 validation 中执行同一检查。approved history 和 archive 仅因该规则不被反向改写，除非用户另行授权。

## 6. 影响范围

| Surface | 目标处理 |
|---|---|
| [Requirements](index.md) 与本记录 | 保存已确认意图、archive baseline 决定、工作现场验证矩阵、独立 reader/verifier 证据、中文逻辑组织检查、实施进展与验证结果。 |
| `AGENTS.md`、`docs/index.md`、`docs/doctidex-git/index.md` | 仅在需要处收敛 Architecture、Impls、产品实现、工作现场、evidence 与中文逻辑组织的仓库级阅读和路由说明。 |
| `write-doctidex-requirement-docs`、`write-doctidex-architecture-docs`、`write-doctidex-impls-docs` | 加入中文逻辑组织检查；Architecture / Impls Skill 同时保留工作现场可解释性、强直接 evidence、concept promotion、重大能力系统性重构和 reader/verifier 验证原则。 |
| 当前 `docs/doctidex-git/architecture/` | 以共同产品、工作现场、跨变体 state/behavior、关键模型和 workflow 为 authority，重构结构与内容。 |
| 当前 `docs/doctidex-git/impls/python/` | 以 Python 工作现场构造、对共同设计的接入、physical realization、私有 mechanics 边界和 evidence 为 authority，重构结构与内容。 |
| `docs/doctidex-git/archive/baselines/pre-dx-req-0015/` | 保存重构前 Architecture / Impls baseline，并以 `format-illegal` 统一标注和导航。 |
| archive、导航与交叉链接 | 依照本节的历史边界修复。 |
| implementation、tests、Published Skills | 作为构造场景、全知复核和当前事实的 evidence 读取；除非另有明确产品影响，不改变其行为或受众内容。 |

现有 review Skill 只在其链接的 Architecture / Impls 标准或 reader/verifier validation routing 因本需求而实际变化时同步更新；不以本次文档重构扩大 review/repair 授权。

## 7. 验收标准

1. 当前仓库级路由、Architecture Skill 与 Impls Skill 对两层的读者、authority、内容充分性、工作现场、交接关系和变更顺序给出一致且可执行的原则，且不与现有 Requirement lifecycle 或 protocol boundary 冲突。
2. Architecture 明确完整定义产品的共同 user surface、逻辑 state、行为与交接语义。对于每一种需要直接跨 variant 读写的 durable representation，文档定义可互操作的 contract；对于允许 variant-specific 的 representation，文档明确每个实际文件、选项和 artifact 的语义，以及转换、保留或拒绝接手的规则。
3. 每个当前 Impls variant 都提供 user-surface 工作现场 matrix。该 matrix 覆盖所有语义不同的可遗留工作现场，或记录有证据的等价合并；每个实际出现的配置文件、每个可 materialize 的选项/状态和每个 artifact 均被纳入。
4. 每个 matrix 场景都由受限的 Architecture reader subagent 验证。它只能使用工作现场、用户可见 transcript 和 Architecture，仍能列出并正确解释所有存在的配置文件、每个出现的选项、artifact 的作用与使用方式，并对每项给出 Architecture 内强且直接的 evidence。
5. 与 reader 独立的全知 verifier subagent 使用 applicable Requirements、Architecture、全部 Impls、source、tests、public surfaces 和场景构造事实，逐项判定 reader evidence 是否真实、是否存在编造或牵强推断，以及功能理解是否足以正确实现 user surface 行为。验证覆盖输入、默认值、配置/artifact effects、结果、失败、恢复、交接与安全边界，但不要求推导当前 source 的全部执行细节；任何无法核实或需要越过 Architecture 才能完成的必要解释都被记录为 Architecture gap，不能以 verifier 的解释冒充 reader 的 evidence。
6. 以 reader/verifier 结果判断 Impls/source 概念是否进入 Architecture：凡是解释工作现场所需的概念均已被提升到共同 authority；保留在 Impls/source 的概念有全知证据证明其不影响任何工作现场的识别、含义、使用、状态转换、恢复或安全边界。
7. Python Impls 能使维护者定位其工作现场构造、对 shared state 和 user surface 的接入、具体 physical realization、不会出现于工作现场的 private mechanics、主要 effects/recovery 和 source/test evidence；它不以代码清单或重复 Architecture 替代 realization 说明。
8. 对 `hook` 及其他带来共同状态、配置、artifact 或生命周期的重大能力，当前文档提供从用户入口到共同模型、状态转换、工作现场、variant realization、失败/恢复和交接边界的连贯阅读路径；读者不必通过零散 command 或 schema 段落自行推导产品设计。
9. 当前 Architecture / Impls 在已确认的结构性替换范围内从零重组，每个事实只保留一个 authority。重构前 baseline 已归档于非发布版本路径并统一标注 `format-illegal`；archive 和 approved history 不被反向用作当前结构模板。相关 links、anchors、导航、doctidex reachability 和 whitespace 通过 scoped validation。
10. reader/verifier 验证至少完成一组完整 paired round；若修复 material gap，只能再进行一组 targeted paired round。总计至多两组，不得为追求 source 细枝末节自动启动第三组。只有共同模型、工作现场文件/选项/artifact、交接 state/behavior、关键 dependency、主要 transition、observable result、安全/兼容边界或 concrete realization owner 缺失时才阻塞完成。
11. 文档重构不修改 doctidex protocol、产品行为、代码、tests 或 Published Skill audience，除非经本 Requirement 记录并另行授权；发现的真实产品 gap 被明确记录而非以文档承诺掩盖。
12. 本次创建、重写或实质修订的 `docs/` 内容，以及 Requirement、Architecture、Impls 作者 Skill 的写作和 validation 规则，均以中文组织说明性逻辑。英文仅作为精确的 identifier、命令、路径、schema/field、代码符号、固定技术术语或引用出现；不保留大段纯英文解释性 prose，也不以中文标题掩盖英文论证主体。

## 8. 进展、依赖与后续关系

创建和细化本记录时已核对 `spec/overview.md`、DX-REQ-0009、当前 `doctidex-git` Architecture / Python Impls、hook 的实现文档与 coverage、三个作者 Skill，以及当前 Python implementation/tests/public surfaces 的入口。上述核对确认：现有设计已经建立共同模型、portable manifest 和 hook 的多层文档；本 Requirement 的新增目标是以可解释的跨变体工作现场和独立 evidence verification 为完整性标准，并以此驱动必要的系统性重构。

用户已确认重写前 archive 并统一标注 `format-illegal`，原有 question/answer 已吸收。`format-illegal` 目前没有既有 protocol 或仓库语义，本记录在第 5 节定义其唯一用途和边界。实施已从 `4f4576e` 复制当前 Architecture 与 Impls 到 [pre-DX-REQ-0015 baseline](../doctidex-git/archive/baselines/pre-dx-req-0015/index.md)，全部 30 个保留页均带统一标签；archive、`docs/doctidex-git` 与 `docs/requirements` scoped validation 均通过。

实施盘点确认一项当前文档矛盾：旧 Architecture 的 worktree workflow 声称 path 与 Git registration 都缺失时 `close` 会清理 stale ownership；当前 JSON contract、Python Impls、`WorktreeService.close` 与测试依据均为保留 unavailable record 并返回 `worktree_unavailable`。新的共同 authority 采用后者作为当前事实，并把旧说法留在 baseline；这属于文档对齐，不授权代码、tests 或产品行为变更。

工作现场验证使用 `.tmp/dx-req-0015/build_worksites.py` 以实际 Python CLI 在本地 Git fixture 中构造 `basic`、`missing-payload`、`foreign-hook`、`unavailable-worktree` 与 `damaged-runtime`，并保留 selected root、host、managed path、shared cache 与每个 `transcript.json`。受限 Architecture-only reader 只读取这些现场、transcript 与当前 Architecture：它正确解释 direct/dependency/hidden payload、manifest/runtime fields、durable link、managed/foreign hook、worktree/cache、damage 与 preserve/block behavior，并逐项引用相应 Architecture authority。它发现 `index.md` 的 top-level `type`、关联 `unsafe` link annotation 和空 cache coordination container 尚无直接共同层说明；这些均已补入 tree/worksite/safety authority 和 Python inventory。独立的全知 source/Impls inventory 复核了该 reader 的 evidence、fixture construction、public surface、source 与 tests：确认这些补写足以支撑 user-surface 实现，不要求推导 JSON bytes、Git registration layout、lock primitive 或 call graph；native Git internals、fixture transcript/container 与 private cache naming 不是缺失的产品 configuration。损坏 runtime 场景暴露的 JSON operation discriminator 差异被列为下面的 implementation gap，而不是用 Architecture 补写掩盖。

同一盘点发现三项不在本次文档重构中静默修复的差异。第一，当前 JSON hook contract 包含 `revision_alignment: metadata_warning` 与非空 `metadata_mismatches` 的语义，但 Python `HookService` 没有生成该 state，现有 hook tests 也未覆盖它；这是已记录的 public-contract implementation gap。第二，损坏 `runtime.json` 由 `worktree list` 读取时，`RootStorage.read_runtime()` 产生 `operation: "external"`，而 JSON contract 对该 command 定义 `worktree_list` discriminator；现有测试只覆盖 `mapping_damaged` finding。blocked caller 仍可按 common envelope/finding 安全 preserve，但 Python 没有满足 command-specific contract。第三，旧 Python Impls 声称所有 External/Worktree/Cache/Hook mutation 在 lock 内重读相关 state；`WorktreeService.close` 在进入 source/root mutation boundary 前完成其 runtime/status 观察，缺少相应 race evidence。新的 Python Impls 将前两项标为 material limitation、将第三项改为不作未证实保证的 realization evidence boundary。三项都需要单独的产品/测试授权才可改变代码或 public contract。

最终验证已执行 `git diff --check`、`doctidex-git validate --scope /docs/doctidex-git --json`、`doctidex-git validate --scope /docs/doctidex-git/archive --json`、`doctidex-git validate --scope /docs/requirements --json`，以及 `.venv/bin/python -m pytest impls/libs/python/tests -q`（45 passed）。所有 authorized documentation work 已完成；本记录进入 `implemented`，仍等待用户明确批准后才可成为 `approved`。

用户随后要求将“文档内容由中文进行逻辑组织，避免大段纯英文叙述”作为独立校验规则。该反馈使本记录回到 `draft`：须将规则写入仓库和三个作者 Skill 的 validation，并把本次重构产生的现行 Architecture / Python Impls 说明性英文 prose 改为由中文组织，再重新完成 scoped validation 与测试。

本轮已将规则写入 `AGENTS.md`，并纳入 Requirement、Architecture、Impls 三个作者 Skill 的写作与 validation。规则约束当前说明性文档，不以语言形式反向改写 approved history 或 archive baseline。现行 Python Impls 的标题、段落、表头和说明性表格单元已改由中文组织；命令、路径、代码符号、schema/field 和必要技术术语仍保留英文。Architecture 的少量叙述性英文标题也已中文化，并保留或同步了相关 fragment links。人工语言扫描只剩命令或架构示意图中的英文 token，没有由英文承担的段落或表格论证。`git diff --check`、`doctidex-git validate --scope /docs/doctidex-git --json`、`doctidex-git validate --scope /docs/doctidex-git/archive --json`、`doctidex-git validate --scope /docs/requirements --json` 均通过；`.venv/bin/python -m pytest impls/libs/python/tests -q` 通过（45 passed）。所有本次授权的工作已完成，本记录恢复为 `implemented`，仍等待用户明确批准后才可成为 `approved`。

用户已明确指令将本 Requirement 转为 `approved`。本记录的实现、验证结果和当前内容据此获准作为 PR/MR-ready 历史；后续变更须遵守 approved history 的边界。

本记录细化 [DX-REQ-0009](0009-architecture-and-details-maintenance-rules.md)。`DX-REQ-0009` 是 approved history，当前未添加反向链接；新增关系不是失效链接修复，若需要完整双向关系，仍须获得用户对该 approved record 的明确编辑授权。当前没有其他已确认的阻塞依赖。
