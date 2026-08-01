# 需求 0009：Architecture 与 Impls 文档维护规则调整

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0009` |
| 状态 | `approved` |
| 日期 | 2026-08-01 |
| 来源 | 用户要求重新定义 Architecture 与原 Details 文档的职责，将 Details 改为 Impls，同步重构当前文档，保留归档内容的历史边界，并以当前文档重构质量优先；第一阶段完成后，用户要求从模型、依赖与工作流重新建立面向未来开发的 Architecture / Impls 基准；收口时进一步要求修复已识别问题、不再继续 cold read，并把 Architecture cold-read 验证限制为最多两轮、避免以非关键字节细节阻塞完成；随后用户澄清 Architecture 应规定关键模型、机制与策略而非穷举实现 mechanics，Python Impls 可引用源码展开落地，且不得把 cold read 找到的实现细枝末节批量标成 Python gap；第四阶段要求把繁复且重复的维护规则拆分为 Architecture、Impls、Requirement 三个专用 Skill，压缩 `AGENTS.md` 为 orchestrator，并同步精炼 review Skill |
| 影响范围 | 仓库级实现文档治理、`AGENTS.md`、文档维护与 review Skills、文档导航，以及 doctidex-git 当前和归档的 Architecture / Impls |
| 协议关系 | 非规范性仓库治理需求；当前不改变 [`doctidex` 协议](../../spec/overview.md) |

本文定义本轮文档模型调整的目标。Architecture 保留语言无关、以 user surface 为起点的
职责，并以关键领域模型、机制、策略和可观察语义形成跨实现设计契约；它不能过于笼统，
也不是对某一实现 mechanics 的逐字段、逐算法或逐字节自然语言转写。原 Details 改名为
Impls，并从单纯代码阅读地图提高为特定实现条件下落实 Architecture 的具体方案。现有
`docs/doctidex-git/` 当前文档需要达到新规则；版本归档只同步目录命名和链接，不进行内容
合规性改造。

前三阶段完成了目录迁移、面向关键模型的 Architecture / Impls 重构和抽象层级修正。第四
阶段又把扩充过程中散落在 `AGENTS.md`、综合 design-doc Skill 和 review lens 中的维护规则按
用途拆分并压缩。当前记录所列授权工作已经由 agent 实施和验证；用户于 2026-08-01 明确将
`DX-REQ-0009` 标记为 `approved`，确认当前结果可进入 PR/MR。

## 1. 已确认的需求意图

### 1.1 Architecture 是 artifact 的共同设计权威

Architecture 继续描述语言和具体实现无关的设计，并应完整到足以让相互独立的实现共享
关键模型、机制、策略与可观察语义，而不要求复制同一套内部 mechanics：

1. 定义支撑主要能力所需的关键且稳定的领域模型、逻辑数据模型、数据流和协作关系；
2. 定义全部预期 user surface，准确表达希望 human、agent 和 program 如何使用 artifact、
   每类使用者必须先理解什么，以及操作后能观察到什么；
3. 定义 artifact 必须提供的能力集、主要机制、策略、约束、失败语义和非目标；
4. 让依据同一 Architecture 构建的不同实现，在使用者视角下覆盖相同的规定能力集。

“覆盖相同能力集”不要求不同实现采用相同的语言绑定、安装方式、调用语法、内部对象、算法
或序列化 mechanics。Architecture 定义跨实现不变的能力、关键状态关系和可观察语义；具体
实现可以选择符合自身条件的最佳落地方式，但不能静默遗漏 Architecture 要求的能力。可选
能力也必须由 Architecture 明确标为可选，不能由 Impls 自行降级。

模型是否进入 Architecture 以其设计重要性为准：直接承载用户可见 identity/state/ownership、
被多个主要 workflow 共用、决定跨组件协作，或影响安全与兼容边界的稳定模型应进入
Architecture。只服务于某个算法步骤、parser、serialization、临时聚合或局部函数的辅助模型
留在 Impls 或源码中。除非 exact bytes 本身是明确的 public interoperability contract，
Architecture 不规定字节级 representation、canonicalization 步骤或内部字段布局。

### 1.2 Impls 是特定条件下的具体实现方案

原 Details 文档层改名为 Impls。每个 Impls variant 说明在一组明确条件下如何具体实现
Architecture；条件可以包括 programming language、runtime、platform、deployment form 或
其他会改变实现方案与接入方式的约束。

Impls 不再只是代码地图。它必须同时说明：

1. variant 的适用条件、目标 Architecture、能力覆盖情况与已知限制；
2. 在该条件下采用的主要技术方案，包括具体组件、必要的物理与内部模型、数据流、协作关系、
   算法、状态、存储、并发、失败处理和特殊技巧；
3. variant 自己的 user surface，包括安装与接入方式、调用入口、使用者必须理解的前置概念，
   以及 human、agent 和 program 在该实现下的预期使用“画面”；
4. 该 user surface 如何实现 Architecture 规定的共同能力，以及实现特有的接入选择为何不
   改变跨实现的可观察语义；
5. 源码 ownership、主要类型与函数、测试和限制如何为上述方案提供证据；可直接引用源码文件、
   symbol 或测试来简化对局部 mechanics 和辅助模型的重复描述。

代码地图仍是 Impls 的组成部分，但不能代替对主要 realization 的设计说明；源码引用也不要求
把自解释的实现逐行转写进文档。以软件开发场景为例，Python 与
Rust variant 可以拥有不同的安装、import、CLI 或嵌入方式；各自 Impls 必须给出适合该语言
生态的使用和主要实现方案，同时说明它们如何覆盖同一 Architecture 能力集。

## 2. 经核对的当前事实与差异

当前 [`doctidex-git` Architecture](../doctidex-git/architecture/index.md) 已经从 user surface
出发，包含 CLI / JSON 契约、领域模型、子系统生命周期、约束和 Skill 协作，因此本需求
不是推翻其现有职责。需要补强的是：

- 把关键且稳定的领域模型、逻辑数据模型、端到端数据流和参与者协作关系作为 Architecture
  的显式设计要求；
- 把 Architecture 从“当前产品契约”进一步明确为不同实现必须共同覆盖的 artifact 能力
  契约；
- 用可追踪证据说明每个 Impls variant 对主要 Architecture 能力与机制的落地；辅助实现细节
  可以通过源码引用定位，不制造逐字段 coverage 工作量。

迁移前的 Python Details（当前入口已成为 [`Python Impls`](../doctidex-git/impls/python/index.md)）
以模块、类型、存储、算法、
并发和测试的代码设计地图为主，明确把正常产品使用入口交给 Architecture 与 Published
Skills。新 Impls 模型要求它增加 Python 实现自身的主要方案和 user surface，而不是只在
traceability matrix 中指向共同 surface。

仓库根目录 [`impls/`](../../impls/index.md) 已用于保存源代码和 Published Skills。新的
`docs/<artifact>/impls/` 保存实现设计文档；两者名称相同但 authority 不同，导航和维护规则
必须始终使用完整路径或明确称为“实现 artifact”与“Impls 文档”，避免混淆。

## 3. 目标文档结构

每个具有当前实现设计文档的 artifact 使用：

```text
docs/<artifact>/
|-- architecture/
|   `-- index.md
`-- impls/
    |-- index.md
    `-- <variant>/
        `-- index.md
```

版本归档保持 Architecture 与匹配 Impls 成套保存：

```text
docs/<artifact>/archive/<version>/
|-- architecture/
|   `-- index.md
`-- impls/
    |-- index.md
    `-- <variant>/
        `-- index.md
```

`<artifact>` 表示被设计的产品、library、plugin 或其他实现 surface；`<variant>` 表示在一组
明确实现条件下的一种 realization，例如 `python`。一个 variant 可以拆成多个页面，但
`impls/<variant>/index.md` 必须导航其主要方案、源码入口和 Architecture coverage。

## 4. Architecture 内容与设计边界

Architecture 至少覆盖以下内容；页面可以按 artifact 的稳定工作流、接口和领域概念组织，
不要求每项独立成页：

| 主题 | 必须回答的问题 |
|---|---|
| Scope 与 authority | 设计哪个 artifact、服务哪些使用者、规定什么、不规定什么。 |
| User surface | human、agent、program 分别在什么场景下如何使用，入口、前置概念、结果和下一步是什么。 |
| 能力与接口 | 必需或可选能力的可观察契约，以及影响使用决策的输入、默认值、权限、副作用和失败。 |
| 领域模型 | 支撑主要能力的关键稳定概念，以及理解其 identity、state、ownership、关系、不变量和 lifecycle 所需的属性。 |
| 逻辑数据模型 | 对跨实现协作或公共语义有约束力的数据对象、schema、状态、identity、所有权和约束；不规定 variant 的物理存储。 |
| 数据流 | 关键输入如何经过参与者与子系统形成输出、状态变化和部分结果。 |
| 协作关系 | human、agent、program、外部系统和内部子系统各自的职责、非职责与交互顺序。 |
| 系统约束 | 并发、非原子边界、恢复、安全、兼容、容量和 bounded-output 约束。 |
| Traceability | 需求来源，以及每个当前 Impls variant 的 coverage 入口。 |

Architecture 不能使用某一 variant 的 module、class、内部路径、storage engine 或语言技巧
填补设计缺口。确实只在特定条件下成立的内容归入相应 Impls；若该内容改变 artifact 对
用户承诺的能力或语义，则必须先回到 Architecture 明确共同契约或可选边界。

“完整性”在本节中表示关键设计闭合，而不是内部实现穷举。读者应能确定主要模型是什么、
它们如何组合、关键状态由谁拥有、主要 workflow 采用什么机制与策略，以及失败后如何决策；
读者不需要仅凭 Architecture 复刻某个 variant 的辅助对象、parser 步骤、缓存布局、函数调用
序列或字节表示。当前 Python 实现中的 module-level 模型可作为识别关键领域模型的重要证据，
但是否提升到 Architecture 仍按跨实现设计意义判断，而不是按源码中是否存在一个类型判断。

## 5. Impls 内容与 realization 充分性

每个 `impls/<variant>/` 至少覆盖：

| 主题 | 必须回答的问题 |
|---|---|
| Variant 条件 | 使用的语言、runtime、platform、deployment、版本和其他设计前提。 |
| Variant user surface | 在这些条件下，human、agent、program 最适合怎样安装、接入和使用。 |
| Architecture coverage | 主要必需能力由什么入口和组件落实，并以代表性测试或源码证据定位；可选能力是否实现。 |
| 技术设计 | variant 的组件、依赖方向、必要的物理与内部模型、主要数据流和协作顺序。 |
| Implementation choices | 算法、storage、protocol/library 选择、语言技巧、平台处理及其理由。 |
| Runtime behavior | side effects、失败、并发、原子或非原子边界、恢复和 cleanup。 |
| Code map | 主要 callers、modules、types、functions、数据 ownership，以及可继续深入的源码入口。 |
| Evidence | 代表性 tests、compatibility、material known limitations，以及 Architecture 与代码的双向追踪。 |

Impls 中的 user surface 不是重复 Architecture。Architecture 是跨实现的能力与语义权威；
Impls 是该 variant 的具体接入和使用权威。共同契约通过链接引用，variant-specific 的安装、
调用、前置知识、示例和限制在 Impls 中完整定义。

Impls 应展开 Architecture 没有规定的落地机制，但不要求复制源码中已经自解释的局部实现。
对辅助类型、临时中间状态、parser/serialization 步骤和低层调用链，可以引用准确的 source
file、symbol、test 或小段示例，并在文档中只解释其责任、重要约束、side effects 和失败边界。

Published Skills 仍应作为安装后 agent 的自足使用说明，不能要求使用者读取仓库 Impls。
Impls 可以把 Published Skills 作为该 variant user surface 的一个交付 artifact 和证据，但不
复制 self-explanatory Skill usage。

## 6. 维护与同步规则

1. 新需求和未实现目标先保存在 `draft` Requirement；只有行为与 artifact 已经存在时，
   Architecture 和对应 Impls 才描述其为当前事实。
2. Architecture 的能力、共同 user surface、关键逻辑模型或跨实现约束变化时，必须评估每个
   当前 Impls variant，并同步受影响的实现文档、代码、测试和 Published Skills。影响公共语义
   或主要机制的未覆盖能力必须显式标为未落实，并按 Requirement 的实际代码范围判断是否
   阻塞；文档型 Requirement 可以准确记录范围外的既有实现差异后进入 `implemented`。
3. 仅改变某个 variant 的接入方式、内部设计、代码或平台处理且不改变共同能力时，更新该
   Impls、实现和测试；若变化暴露出新的共同能力或语义，再先更新 Requirement 与 Architecture。
4. 新增 variant 时，必须建立足以解释主要 realization 的 Impls、提供 Architecture capability
   coverage，并清楚定义自己的 user surface；不能以未经解释的代码清单替代方案设计。
5. 同一事实只在最窄的权威层定义：Requirement 保存经审阅的意图与决策，Architecture 定义
   跨实现关键设计，Impls 定义 variant realization，代码与测试承载自解释的低层 mechanics
   并提供落实证据。
6. 归档时把匹配版本的 Architecture 与全部 Impls 一起归档，并保持版本内链接和使用入口
   自洽；归档不反向定义当前设计。

### 6.1 与现行维护规则的整合

本需求只改变 Architecture / Details 模型及其直接维护关系，不废除其他现行文档、
Requirement、review 或 Skill 规则。实施时必须以 `AGENTS.md` 和 `.agents/skills/` 的全部
现有内容为基线逐项整合：

1. 对每条现行规则明确执行保留、按本需求改写，或因被本需求取代而删除；不能通过整体
   重写遗漏语言、authority、Requirement 生命周期、用户 comment、双向依赖、review 授权、
   Published Skill audience boundary、验证或 forward-test 等既有约束。
2. `AGENTS.md` 继续是仓库级维护边界的权威；repository Skills 把这些边界转化为具体工作流，
   不能互相产生不同的 Architecture / Impls 定义。
3. 对 `.agents/skills/` 下每个 Skill 目录检查 `SKILL.md`、全部 `references/` 和
   `agents/openai.yaml`。受影响的内容必须修改并验证；判断无需修改的内容也必须记录其与新
   模型兼容的理由，不能因未出现 `Details` 字样而跳过。
4. Published Skills 的 installed-product wording 与自足使用边界继续成立。Impls 增加
   variant user surface 不授权 Published Skills 读取 repository docs，也不把 repository
   开发信息暴露给产品使用者。

当前三个 repository Skill 的处理要求如下：

| Skill | 当前关联 | 实施要求 |
|---|---|---|
| `write-doctidex-design-docs` | 直接定义 Architecture / Details / Requirements 的类型、阅读链、生命周期和校验 | 全面改为 Architecture / Impls 模型，并同步 `references/document-types.md`；保留现行 Requirement lifecycle、comment、authority 和知识网络规则。 |
| `review-doctidex-repository` | 以 Architecture、Details 和设计文档规则作为 review authority 与 repair 同步面 | 更新主 Skill 与 `references/review-lenses.md` 的 authority 顺序、Impls realization 充分性和 capability coverage 检查；保留显式 review/repair 授权及 finding contract。 |
| `write-doctidex-agent-skills` | 规定 Published / repository Skill audience、Architecture 输入和 Skill 验证 | 核对 Impls user surface 不突破 installed-product boundary，并检查两个 references 与 metadata；只有新模型需要改变现有表述时才修改。 |

每个发生变化的 Skill 都必须依据 `write-doctidex-agent-skills` 的现行验证规则更新或确认
metadata，并通过 local Skill validation；复杂工作流变化继续使用独立 agent 对 raw artifacts
做 forward test。

### 6.2 当前文档重构质量优先

本需求实施时，首要交付物是设计闭合、层级适当且自洽的当前 Architecture 与 Impls。历史
Requirements 和 archive 用于解释意图与旧版本事实，不是当前文档的结构、篇章、术语或
内容充分性模板，也不得反向降低当前文档质量。

1. 当前文档以当前代码、测试、public surfaces、本 Requirement 确认的目标和仍适用的现行
   规则为事实与质量依据；不得为了与历史 Requirement 或 archive 的旧组织方式逐段对应，
   省略 user surface、模型、数据流、协作关系、variant 方案或 capability coverage。
2. 可以自由重组、合并、拆分或重写当前页面，使每项事实归入最合适的唯一 authority。
   旧页面边界、标题和术语不构成兼容要求。
3. 不得只为让旧链接继续工作而在当前文档树保留 `details/` 兼容目录、占位页面、重复说明
   或过时术语。当前 `impls/` 目标结构确定后，再按用户授权机械修复历史 Requirements、
   archive 和其他导航的 link targets。
4. 历史材料与当前事实不一致时，当前 Architecture / Impls 准确描述现状；历史记录保持原有
   意图和结果，只通过链接进入新的当前权威，不为表面一致而改写任一侧的事实。
5. archive 继续按其历史版本自洽，不接受新内容标准的追溯改造；这项豁免不能被用来降低
   当前 Architecture / Impls 的关键设计闭合或验证门槛。

实施顺序应先收敛当前 Architecture / Impls 的目标结构和内容并验证关键设计与 realization，
再处理归档目录迁移、历史 Requirement link targets、导航与其他机械兼容工作。规则与 Skills
的最终文本必须支持该顺序，不能把“尽量少改历史材料”误写成“当前文档尽量沿用历史结构”。

## 7. 现有文档迁移范围

用户已明确要求重构当前 `docs/doctidex-git/` 文档，同时保留归档内容的历史边界：

1. 将当前 `details/` 迁移为 `impls/`，将 `details/python/` 重构为充分解释主要 realization 的
   Python Impls；
2. 依据第 4 节检查当前 Architecture，补足领域模型、逻辑数据模型、数据流、协作关系、
   用户使用“画面”和跨实现能力边界；
3. 将 `archive/v0.1.0/details/` 同步迁移为 `archive/v0.1.0/impls/` 并修复导航和交叉链接，
   但不为已归档 Architecture 或 Impls 补写新规则要求的 user surface、模型、数据流、
   capability coverage 或其他内容；归档继续准确保留当时已有的说明；
4. 更新 `docs/`、doctidex-git、archive、Requirements 和 repository `impls/` 导航，以及
   Architecture / Impls 内部交叉链接；
5. 按第 6.1 节逐项整合 `AGENTS.md` 和 `.agents/skills/` 下全部内容，并校验每个发生变化的
   Skill 与 agent metadata；
6. 当前没有产品行为或代码变更要求。重构若发现文档目标与当前实现、测试或 Published
   Skills 不一致，应先在本 Requirement 中记录具体差异，不能用文档迁移静默改变产品。

上述工作按第 6.2 节执行：第 1、2 项的当前文档质量优先于第 3、4 项的历史与归档调和。
先确定高质量的当前目标结构，再让历史链接和归档导航适应该结构，不反向以旧路径限制当前
重构。

用户已明确授权修复现有 `approved` Requirements 中因 `details/` 目录迁移而失效的链接。
该授权只允许机械修改链接 target，以及维持链接有效所必需的导航；不得改变这些记录的
`approved` 状态、历史术语、需求意图、决策、结果或其他正文。归档文档同样只做目录和链接
迁移，不以当前规则重写历史内容。

实施前的 scoped validation 已确认 `DXG-REQ-0002` 中指向
`details/python/maintenance.md` 和 `details/python/repository-relations.md` 的两个链接当前已
失效。这是本需求建立前已存在的基线问题，纳入上述机械链接修复；它不授权改写 0002 的
其他内容。同期发现的 repository root unsafe-link annotation findings 不由本需求造成，也不
属于本次 Architecture / Impls 规则与迁移范围。

## 8. 实施影响

| 层面 | 目标处理 |
|---|---|
| Requirement 历史 | 本记录保存新模型、迁移决定和实施结果；已批准历史只在当前目标结构确定后修复失效链接。 |
| Repository rules | 把 Architecture / Impls 模型整合进全部现行文档维护规则，保留未被取代的约束。 |
| Documentation Skill | 改写文档类型、阅读链、维护生命周期、内容清单和验证门槛，同时保留 Requirement 规则。 |
| Review Skill | 将 review authority、追踪和 repair 同步到 Impls，并检查 capability coverage。 |
| Agent Skill authoring | 核对 audience boundary、Architecture 输入、references 与 metadata，按实际影响更新。 |
| Current docs | 作为实施重点，优先重构 doctidex-git Architecture，迁移并补足 Python Impls 的主要 realization。 |
| Archive | 当前文档收敛后，把 `v0.1.0` Details 路径迁移为 Impls 并修复链接，不做内容合规性改造。 |
| Code/tests/public Skills | 当前只作为事实与 coverage 证据读取；不改变公共行为。 |
| Protocol | 无变更。 |

## 9. 第一阶段验收标准

1. `AGENTS.md` 与全部 repository Skill 目录均以现有内容为基线完成逐项影响检查；受影响的
   主 Skill、references 和 metadata 已更新，未受影响的内容有兼容理由，且未遗漏或削弱
   Requirement lifecycle、comment、review authorization、Skill audience 和验证等既有规则。
2. `AGENTS.md` 与相关 repository Skills 对 Architecture、Impls 和 Requirements 的职责、
   authority、路径与生命周期给出一致且可执行的规则，不再把 Impls 限定为代码地图。
3. Architecture 定义 artifact 的 user surface、能力集、关键领域与逻辑模型、主要数据流、
   协作机制、策略、约束和失败；独立实现者不需要借用某一 variant 补足关键共同契约，也不被
   要求复制该 variant 的低层 mechanics。
4. 每个当前 Impls variant 定义适用条件、variant user surface、主要技术方案、必要物理模型、
   数据流、特殊处理、code map、测试与限制，并说明 Architecture capability coverage；辅助
   实现细节可由准确源码引用承载。
5. 不同当前 Impls 可以使用不同的最佳接入方式和内部模型，但必需能力与公共语义覆盖一致；
   影响主要能力的未覆盖项和 Architecture 声明的可选能力在相应层显式可见。
6. 当前 doctidex-git `details/` 迁移为符合新规则的 `impls/`，当前 Architecture 达到关键设计
   闭合要求；归档 `details/` 迁移为 `impls/` 且链接有效，但历史内容不接受当前完整性
   标准的追溯性改写或合规判定。
7. 当前 Architecture / Impls 已先按当前事实和新质量标准独立收敛，没有为了贴合历史
   Requirements 或 archive 而保留旧页面结构、`details/` 兼容层、占位页、重复权威、过时
   术语或内容缺口；历史和归档链接随后适配当前目标结构。
8. `approved` Requirements 只发生迁移所需的链接 target 修复，没有状态、历史术语、意图、
   决策、结果或其他正文变化。
9. 本次迁移和规则改动触及的导航、Requirement、Architecture、Impls、代码、测试和
   Published Skill 追踪链接全部有效，没有孤立文档或把 docs `impls/` 与 repository root
   `impls/` 混为同一 authority；不把无关的既有 repository findings 扩入本需求。
10. 发生变化的 local Skills 及其 `agents/openai.yaml` 均通过验证；复杂工作流变化通过独立
   raw-artifact forward tests；文档链接、索引、anchors、
   diagrams 和 whitespace 通过相应校验。
11. 完成迁移和验证后，本记录进入 `implemented`；只有用户明确接受结果后才可成为
   `approved`。

## 10. 第一阶段实施结果与验证

### 10.1 当前规则与文档

实施已完成以下结果：

1. `AGENTS.md` 已把原 Architecture / Details 模型整体改为 Architecture / Impls，并明确
   Architecture 设计闭合、Impls variant realization、capability coverage、当前文档质量优先、archive
   非追溯改造和历史链接授权边界。
2. `write-doctidex-design-docs` 及其 `document-types.md` 已同步类型、authority、成熟度、
   Requirement 触发、archive 处理和验证规则；`review-doctidex-repository` 及其 review lenses
   已同步 authority 顺序、Impls 检查、published/local Skill 边界、comparison base、失败降级和
   changed-Skill 验证门槛。
3. `write-doctidex-agent-skills` 的主 Skill、两个 references 与 metadata 已逐项核对后保持不变：
   它已明确区分 Published 与 repository-local audience，使用 Architecture 作为公共设计输入，
   并完整规定 metadata、local Skill validator、published plugin validator 与 raw-artifact forward
   test；Impls 增加 variant user surface 不改变这些职责或授权边界。
4. 当前 doctidex-git Architecture 新增能力、逻辑数据流与协作权威，并补足 user surface、领域
   模型、生命周期和跨 variant coverage 入口。当前 Python `details/` 已迁移为 `impls/python/`，
   新增 variant user surface 与完整系统设计，coverage matrix 已为每项 Architecture capability
   给出 user entry、realization 和测试证据。当前树没有保留 `details/` 兼容目录。
5. `archive/v0.1.0/details/` 已迁移为 `archive/v0.1.0/impls/`。逐文件比较确认迁移后的 Impls
   正文与迁移前 Details 正文相同；归档 Architecture 和版本导航只修复相对 link targets，没有
   按新完整性规则补写或判断历史内容。
6. `DXG-REQ-0001`、`DXG-REQ-0002` 与 `DX-REQ-0008.2` 的 `approved` 状态、历史术语、意图、
   决策和结果均保持不变，只修复用户授权范围内的链接 targets。0002 中两个既有失效链接已
   指向保留其历史事实的 `v0.1.0` archive Impls 页面。

### 10.2 验证证据

| 验证 | 结果 |
|---|---|
| 三个 repository-local Skill 与各自 `agents/openai.yaml` | `quick_validate.py` 全部通过。两个发生内容变化的 Skill metadata 仍准确，因而无需机械改写；未变化的 Skill 也通过验证。 |
| 复杂工作流 forward test | 两组 fresh independent agents 仅使用 raw Skills、rules、Requirement 与场景进行多轮测试；发现的成熟度、Requirement 触发、archive authority、published/local audience、comparison base、失败降级与验证证据歧义均已回写规则。 |
| Python regression | `.venv/bin/python -m pytest impls/libs/python/tests -q`：31 项通过。 |
| Python lint | `.venv/bin/python -m ruff check impls/libs/python`：通过。 |
| Whitespace | `git diff --check`：通过。 |
| 文档树 scoped validation | `doctidex-git validate . --scope /docs --scope /impls` 完整扫描；本次范围没有新增 finding。 |
| 路径与归档边界 | 没有 Markdown link target 继续指向 `details/`；当前无 compatibility 目录；归档 Impls 正文与迁移前文件逐项一致。 |

Scoped validation 仍返回 repository root `index.md` 的 5 条
`link_annotation_invalid`。它们都是实施前已记录的 unsafe-link annotation 基线问题，路径不在
本需求改动的当前 Architecture / Impls、Requirements 或 repository implementation 导航中；
本需求没有授权借文档模型迁移修复该根索引，因此保留为明确的范围外 finding。

## 11. 第二阶段：面向未来开发基准的结构性重构

### 11.1 用户复盘与问题定义

第一阶段完成了 Details -> Impls 的类型迁移，也补入了 capability、data flow、variant user
surface 和 coverage，但主要工作方式仍是沿用旧页面边界后逐页修补。由此形成的当前状态有
三个根本问题：

1. Architecture 的组织入口仍以旧的 user surface、CLI、领域模型、生命周期等页面为主，
   没有先建立一套关键且互相依赖的产品模型，再让接口与工作流从这些模型自然导出。
2. Git source、revision、repository relation、cache、root-owned state、install identity、
   recovery、mapping、worktree ownership、operation result 等决定产品形态的概念分散在
   Architecture、Python Impls 和代码地图中；共同语义的 authority 不够集中。
3. Python Impls 仍明显继承原 Details 的模块说明结构，既重复部分 Architecture，又承担了
   一些本应先由 Architecture 定义的概念与工作流，因此 Architecture、Impls、Published
   Skills 和实现之间还不是一套从设计到实现自然展开的系统。

第二阶段不再以修补现有页面为主要方法，而是从 fresh implementation 的阅读与设计顺序重新
构造当前文档：先定义关键模型、依赖与状态关系，再定义工作流和公共 surface，最后建立
Python realization 与代码证据。现有页面边界、标题和篇章顺序均不构成目标结构约束。

第三阶段复盘确认，上述“完整”不能解释为把 Python 的每个内部选择提升为跨实现契约。
Architecture 的目标是把产品层面的模型、机制和策略说清楚；mechanism 的具体算法、物理状态、
辅助模型与平台做法由 Python Impls 展开。以 Python source 为当前事实基础时，重点是补齐文档
对现有主要设计的解释，不是通过 cold read 发掘尽可能细的实现差异并建立 gap backlog。

### 11.2 Architecture 目标形态

Architecture 应成为 doctidex-git 的跨实现自然语言设计，而不是 Python 实现的自然语言副本。
一个不了解 Python 实现的开发者只读 Architecture，应能理解关键模型、组合关系、状态
ownership、主要机制与策略、workflow 的核心状态变化，以及影响用户下一步决策的失败和并发
边界；具体算法、内部临时状态和物理落地仍由其 Impls 决定。

目标知识结构如下；实施时可以按关键设计密度合并或拆分页面。这些目录名提供导航基准，
不要求为低价值辅助模型制造独立 authority：

```text
architecture/
|-- index.md
|-- product-and-users.md
|-- models/
|   |-- doctidex-tree-and-configuration.md
|   |-- root-ownership-and-paths.md
|   |-- git-source-revision-and-repository.md
|   |-- external-installation-and-mapping.md
|   |-- worktree-and-cache.md
|   `-- operation-result-and-failure.md
|-- system/
|   |-- components-and-dependencies.md
|   |-- validation-workflow.md
|   |-- external-workflows.md
|   |-- worktree-and-cache-workflows.md
|   `-- concurrency-publication-and-recovery.md
|-- interfaces/
|   |-- cli.md
|   |-- cli-schema.md
|   `-- programmatic-integration.md
`-- skill-system.md
```

Architecture 以以下模型组检查关键设计是否闭合。表内条目是识别领域 authority 的线索，
不是要求把每个 Python 字段、临时对象或实现状态逐项提升为公共模型：

| 模型组 | 必须形成的共同设计 |
|---|---|
| doctidex tree 与 configuration | document、index/log、最近负责制、局部配置、link、safe/unsafe、reachability、scope 与 support closure 如何构成可解释的 tree。 |
| Root、ownership 与 path | root identity、owner root、content root、host repository、internal namespace、responsible index 和 target path 的关系与选择歧义。 |
| Git source、revision 与 repository | source locator、canonical identity、repository/gitdir/worktree、host relation、revision selector、exact commit、object availability 与 credentials boundary。 |
| External installation | install key/identity、direct/dependency role、parent edge、fixed snapshot、logical read-only publication、portable recovery 与幂等提升。 |
| Link 与 mapping | presentation target、relative symlink、repository-relative mapping、safe state、current/portable record、available/missing/damaged/unmanaged 状态。 |
| Worktree | source kind、owner root、managed identity、base/exact commit、path ownership、clean/changed/unavailable 与 open/list/close lifecycle。 |
| Cache | canonical-source cache identity、object store、linked worktree registration、valid/prunable/unknown、mutation boundary 与 cleanup eligibility。 |
| Operation 与 result | command context、selection、plan/apply、changed/network/affected、finding、partial success、pagination/cursor、diagnostic 与 next decision。 |

关键模型与组件之间必须给出明确的依赖方向；设计若存在必要回路，应说明 ownership 和打破
运行时耦合的边界，而不是为形式上的无环拆出无意义模型。至少表达：protocol interpretation 不依赖 Git；
Git source/revision 不依赖 doctidex root；external installation 组合 root、source、host Git 与
recovery；link 依赖完整 installation mapping；worktree 组合 source 与 owner root；cache 只按
canonical source 与 Git registration 管理共享 objects；surface orchestration 只组合这些领域
能力，不重新定义它们。

validation、external install/link/restore/link-parse、worktree open/list/close 和 cache clean 等
主要工作流从上述模型出发，说明主输入、关键决策、状态转换策略、可观察结果、部分成功和
恢复边界。只有影响公共语义或跨实现一致性的 publication/concurrency 顺序进入 Architecture；
其算法步骤和物理原子性手段留在 Impls。CLI、JSON 和 Skills 是这些工作流的公共入口，不能
反向成为领域设计的组织骨架。

### 11.3 Python Impls 目标形态

Python Impls 应围绕 Architecture 的概念与组件边界解释主要 realization，并可按源码 ownership
组织具体落地；既不延续旧 Details 的薄代码清单，也不重复转写源码中自解释的低层细节。目标
知识结构为：

```text
impls/python/
|-- index.md
|-- user-surface-and-integration.md
|-- platform-package-and-dependencies.md
|-- physical-data-and-storage.md
|-- components/
|   |-- cli-results-and-rendering.md
|   |-- protocol-interpreter.md
|   |-- git-source-and-storage.md
|   |-- external-installation-and-mapping.md
|   `-- worktree-and-cache.md
|-- concurrency-failures-and-recovery.md
`-- architecture-coverage-and-tests.md
```

Impls 对 Architecture 的主要 model/component 给出 Python 类型与函数、模块 ownership、必要
物理字段和 serialization、filesystem/XDG/Git layout、Git command 与 library dependency、lock
与 atomic publication、platform handling、failure translation、代表性测试证据和 material
limitations。辅助类型、临时模型和局部算法可以通过 source file、symbol 与 test 链接定位，
文档只补充源码不易表达的意图与边界。Architecture 已定义的共同概念和工作流只链接，不在
Impls 中重新发明另一套语义；Python 特有的安装、subprocess、package 和 internal API 只留在
Impls。

### 11.4 可复用的文档维护原则

第二阶段应从实际重构结果中抽象出可用于其他 artifact 的维护原则，并补入当前 repository
维护规则与相关 Skills。至少沉淀以下原则：

1. **关键模型优先**：结构性 Architecture 工作先识别承载主要能力与公共语义的稳定 artifact
   models，并定义理解其 identity、state、ownership 和 invariants 所必需的属性，再组织
   interfaces、workflows 与页面；辅助或临时模型不因源码中存在便自动提升。
2. **关键依赖先行**：在展开流程前先给出主要模型与组件的依赖、组合关系和需要禁止的反向
   依赖；workflow 只使用已经定义的领域 authority，但不要求把局部调用图变成 Architecture。
3. **共同概念提升**：当多个公共工作流依赖某个稳定概念时，该概念的共同语义属于
   Architecture；variant-specific 类型、存储、算法与 mechanics 留在 Impls。
4. **Architecture 可实现但不复制实现**：Architecture 不只是 public contract 摘要；它必须让
   独立实现者能选择符合共同模型、机制、策略和可观察语义的 realization，而不要求得到相同
   内部对象、算法、存储布局或 exact bytes。
5. **Impls 展开 realization**：Impls 解释 Architecture 的主要 model/component/workflow 如何由
   variant 的 physical state、代码 ownership 和代表性 tests 落实；可引用 source file、symbol
   和 test 简化辅助细节，源码目录结构本身也不能代替设计解释。
6. **Surface 消费领域设计**：CLI、JSON、program API 和 Skills 是 models/workflows 的使用
   surface，不应反向成为 Architecture 的主要分篇骨架，也不能在各自页面复制领域语义。
7. **用户授权下替换旧树**：只有用户明确许可结构性重构及其目标范围后，才可以先建立全新
   target tree，再迁移唯一 authority 并删除被取代的旧页面；获得许可后，不以逐页修补、旧
   标题保留或最小 diff 作为质量目标。
8. **有界双重理解验证**：用 Architecture-only cold read 验证关键共同设计是否足够明确，再用
   Architecture + Impls cold read 验证 variant realization 是否可准确定位；一个结构性重构最多
   执行两轮，每轮发现的实质缺口回写唯一 authority。第二轮后不再自动启动第三轮；只有缺失
   关键 required model、dependency、主要 state transition、observable result、safety/compatibility
   boundary 或 concrete realization owner 才阻塞通过。不得以 cold read 穷举 Python implementation
   deltas；序列化、parser、canonicalization、辅助模型或平台 mechanics 的差异，只有在它们违反
   Architecture 已明确的公共语义或 exact interoperability contract 时才属于 gap，其余保留为
   Impls choice 或直接由源码承载。

这些原则应与现有 user-surface-first、Requirement lifecycle、current-quality priority、archive
和 approved-history 边界共同成立。实施时更新 `AGENTS.md` 的 Implementation Documentation
Design、`write-doctidex-design-docs` 及其 document-types reference；仅在 review authority 确实
受影响时同步 `review-doctidex-repository`，并按 changed-Skill 规则完成验证。

## 12. 第二阶段实施计划

1. **建立 authority inventory**：列出当前 Architecture、Impls、Published Skills、公共
   CLI/schema 与实现中的关键概念、状态和工作流，形成“保留在 Architecture / 提升到
   Architecture / 留在 Python Impls / 删除重复”的 ownership matrix。
2. **确定全新目标树**：以第 11.2、11.3 节为骨架，为每个事实指定唯一页面；先确定模型之间
   的 dependency graph、state ownership 和公共/内部边界，不沿旧页面逐篇编辑。
3. **重写 Architecture models**：先完成 tree/configuration、root/ownership、Git、external、
   link/mapping、worktree、cache、operation/result 的关键模型，定义跨实现机制需要的属性、关系、
   不变量、lifecycle 和失败状态；辅助实现模型留给 Impls。
4. **从模型重写系统与工作流**：建立 components/dependencies authority；分别重写 validation、
   external、worktree/cache 数据流、sequence/state transitions、publication order、并发与恢复，
   让每个工作流只引用已定义模型。
5. **重新接入公共 surface**：收敛 product/users、CLI、JSON、program integration 和 Skill
   system，使它们解释如何使用共同模型与工作流；删除被新模型页取代的重复自然语言实现。
6. **重建 Python Impls**：以新 Architecture 为主线并结合 Python source ownership 重写 variant
   integration、physical data、component realization、算法、storage、locks、failures 和 platform
   choices；为主要模型与 workflow 建立 source/test evidence，辅助细节直接引用源码。
7. **切换导航并移除旧结构**：在本 Requirement 已明确许可的当前 Architecture / Impls 范围
   内，新树完整后一次性切换 indexes 与 current cross-links；删除已被新 authority 取代的旧
   页面，不保留兼容页、重复概念或旧篇章占位。
8. **沉淀维护原则**：依据完成后的 Architecture / Impls 重构抽象第 11.4 节的通用原则，更新
   `AGENTS.md` 与受影响的 repository Skills/references；核对 metadata，验证每个 changed Skill，
   并对复杂工作流变化执行 independent raw-artifact forward tests。
9. **执行结构与理解验证**：校验 Markdown links/anchors/diagrams、doctidex reachability、
   Architecture 主要 capability coverage、Python source/test traceability 和 whitespace；最多两轮
   cold read 只判断关键设计能否理解、主要 Python realization 能否定位，不以发现更多内部
   delta 为目标。第二轮后按第 11.4 节的 materiality threshold 收口。
10. **记录实施结果**：把最终页面树、ownership 迁移、删除项、规则变化、验证证据和范围外
    finding 写回本 Requirement；完成并验证后回到 `implemented`，等待用户另行决定是否
    `approved`。

本阶段重构当前 `docs/doctidex-git/architecture/`、`docs/doctidex-git/impls/` 及其当前导航，
并把可复用原则同步到 `AGENTS.md` 和受影响的 repository maintenance Skills。产品行为、Python
source/tests、Published Skills、archive 与已批准 Requirements 不在本阶段的修改范围；它们
作为接口、实现和历史证据读取。

## 13. 第二阶段验收标准

1. Architecture 以关键模型、依赖、机制、策略和状态 ownership 为核心，而不是以 CLI 页面或
   旧文档篇章为核心；第 11.2 节中影响主要能力和公共语义的模型有唯一、可导航的 authority，
   辅助或临时实现模型不被强制提升。
2. Architecture 明确给出关键模型依赖、组件职责、主要数据流、状态转换策略、公共 publication
   语义、并发、部分成功和恢复边界；fresh implementer 不需要读取 Python Impls 或代码补足
   关键共同设计，但可自行选择具体算法、内部模型和物理 mechanics。
3. 所有公共 user surface、CLI、JSON 与 Skills 都可追踪到同一组 Architecture models 和
   workflows，没有以接口字段清单代替领域设计。
4. Python Impls 以 Architecture 的主要机制和 Python source ownership 说明 current realization；
   关键 model/workflow 映射到 Python entry、主要类型/函数、physical state、算法、failure
   boundary 与代表性测试证据，辅助细节可以直接引用 source。只有影响公共语义、主要机制、
   safety/compatibility 或明确 interoperability contract 的未落实项才列为 coverage gap。
5. Architecture 不包含 Python 文件、private class/function、XDG path、Python-specific
   serialization、lock primitive 或 library mechanics；跨实现可版本化或 public schema 可以作为
   logical contract 存在，其 Python physical realization 只存在于 Python Impls。
6. 在用户明确许可的当前 Architecture / Impls 重构范围内，不再存在由旧页面边界造成的重复
   authority、过时自然语言实现、兼容页、占位页或只剩导航意义的孤立页面；范围外结构没有
   因本原则被推定为可替换。
7. 已执行的 cold-read 场景能区分“关键设计可理解/主要 realization 可定位”“阻塞性设计缺口”
   和“非规范内部差异”；最多两轮中发现的实质问题回写相应 authority。不得为了产出 gap 而
   继续追踪非公共 byte-level choice、辅助模型或局部 mechanics，也不自动启动第三轮。
8. `AGENTS.md` 与相关 maintenance Skills 已吸收第 11.4 节中经本次重构验证的通用原则，且
   没有把 doctidex-git 页面结构或一次性迁移步骤误写成所有 artifact 的固定模板。
9. 每个 changed Skill 及其 metadata 均通过 validator；复杂工作流规则通过 independent
   raw-artifact forward tests，测试发现的歧义已回写规则。
10. 当前导航、cross-links、anchors、diagrams、doctidex reachability 和 whitespace 通过校验；
    本阶段没有修改产品行为、代码、Published Skills 或 archive；approved history 只发生用户
    明确授权的 mechanical link-target repair，不改变状态或历史正文。

## 14. 第二阶段实施进展

### 14.1 已建立的当前基准

当前 Architecture 已按第 11.2 节建立 model-first tree：六个 `models/` 页面分别拥有 tree/config、
root/path ownership、Git source/revision、external/mapping、worktree/cache 与 operation/result；五个
`system/` 页面拥有 component DAG、validation、external、worktree/cache 与 publication/recovery
workflow。Public product/users、CLI、JSON、program integration 与 Skill system 作为这些模型和
workflow 的 consumer 保留，不再承担替代领域设计的职责。

Cold read 暴露后，Architecture 曾进一步补齐 canonical source 算法边界、requested-default
lookup、portable manifest `1.0` schema 与 identity、Git clean/cache classification、restore unknown
filter item、partial publication `changed`、link mapping-first publication 和 stable failure
discrimination；同时删除了协议与实现均不存在的 `exclude` 概念。后续 fresh pass 又推动闭合了
restore page-first batch、finding/candidate emission、provisional validation root、support closure、
payload integrity、content-root、path normalization、stale close、YAML/CommonMark profile、Markdown
destination、symlink discovery、request-class identity、durable local locator、Finding path/order 和
damaged mapping decision。这些是第二阶段的实际编辑记录，不表示其中每项都应继续作为
Architecture contract；第三阶段按关键模型、机制、策略和公共语义重新判断其归属。

Python Impls 已按第 11.3 节建立 variant surface、platform/dependency、physical state、component、
concurrency/recovery 与 coverage authorities。它现在给出主要 root/cache layout、runtime/manifest
字段类型与约束、Host Git helper ownership、Command Context/Plan 的 Python 表示、Architecture tree
fact 的 transient/owned field mapping，以及可直接定位到 test function 的证据。

### 14.2 待重新分类的 realization differences

第二阶段 coverage authority 曾把 17 项 Architecture 与 Python 差异统一列为 current realization
gaps。用户复盘确认，该清单混合了三种性质不同的事项，不能整体作为后续产品实现 backlog：

1. Python 当前主要模型、机制或可观察行为尚未被 Architecture / Impls 准确解释的文档缺口；
2. Architecture 因过度规定 parser、serialization、canonicalization、内部排序、临时状态或
   publication mechanics 而制造出的表面实现差异；
3. 确实影响公共语义、主要机制、safety/compatibility 或明确 interoperability contract 的
   material implementation gap。

第三阶段以 Python source、tests 和 public surfaces 为当前事实证据逐项重分类：第 1 类通过补全
Architecture 或 Impls 解决；第 2 类通过降低 Architecture 的无必要规定、在 Impls 记录
variant choice 或直接引用源码解决；只有有明确 Architecture authority 和实际用户/协作影响的
第 3 类保留为 gap。不得仅因 cold read 可以观察到更细差异，就把辅助字段、临时模型、低层
算法步骤或字节表示转成产品需求。本阶段仍不修改 Python source、tests 或 public behavior。

### 14.3 已沉淀的维护规则

`AGENTS.md`、`write-doctidex-design-docs` 与 `document-types.md` 已加入 model-first、dependency-first、
共同概念提升、surface-consumes-domain、Architecture implementability、Impls realization evidence、
结构替换用户授权和双 cold-read 规则。Forward test 发现的权限与完成状态、一对多历史链接、
Architecture/Impls authoring 顺序、required capability gap 和 cold-read pass criteria 歧义也已闭合。
`review-doctidex-repository` 的 implementation-document lens 只同步受影响的结构性验证与 cold-read
门槛；其 review/repair authorization 和其他 finding contract 保持不变。后续 forward test 还闭合
了无 active Requirement 时的未授权链接状态、Architecture stability/current-navigation gate、
documentation-only Requirement 与既有 code gap 的关系、fresh fallback、affected-pass 重跑矩阵、
combined-reader source boundary 和无 Requirement 时的证据 handoff。

用户要求停止本需求的进一步 cold read，并把 Architecture cold-read validation 固定为最多
两轮。维护规则因此增加 materiality threshold：required model/dependency/state/observable behavior、
safety/compatibility 和 realization ownership 仍是阻塞项；未被 Architecture 声明为 exact public
wire/storage/identity contract 的字节级 parser/serialization/canonicalization/platform choice 不再
触发无界迭代。第三阶段进一步澄清：这类差异默认是 Impls choice 或源码细节，不应机械登记为
known gap；只有证明其违反关键 Architecture authority 后才保留为 gap 或 follow-up。

### 14.4 当前验证与未完成项

三个 repository-local Skills 及 metadata 已通过 `quick_validate.py`；Python tests 31 项通过，Ruff
通过，`git diff --check` 通过。最终 scoped doctidex validation 的 13 条 approved-history broken links
已在用户授权后全部消失；修复只替换 user surface、workflow、model、component/failure 与
Architecture coverage 的唯一 successor targets，不改变 approved 状态、历史术语、意图、决策、
结果或其他正文。Validation 目前只剩既有 root `index.md` 的 5 条
`link_annotation_invalid`，继续属于本需求范围外基线。

Fresh raw-artifact forward tests、Architecture-only 与 Architecture + Python Impls reads 已为第二
阶段提供两轮问题发现。用户明确决定本需求不再启动新的 cold read；第三阶段不把原 17 项清单
直接视为产品 gap，而通过 source/code read、现有 tests、public surfaces 和文档 traceability
重新判断层级。后续验证使用现有 read evidence、规则/链接校验、Python regression、Ruff 与
whitespace 结果，不把缺少第三轮读者视为未完成。

## 15. 第三阶段：恢复 Architecture / Impls 平衡

### 15.1 实施计划

1. 以当前 Python modules、主要 module-level types、public CLI/schema、Published Skills 和 tests
   建立事实清单，区分关键领域模型、主要 realization、辅助/临时模型和纯 mechanics。
2. 对 Architecture 逐页检查：保留关键模型、机制、策略、invariants 和可观察语义；把仅由
   Python 落地需要的算法、字段布局、parser/serialization 步骤、physical ordering 和平台选择
   下沉到 Python Impls 或源码；删除无公共契约依据的 exact-byte 规定。
3. 对 Python Impls 逐页补齐 Architecture 机制的具体落地、主要组件协作、物理状态、失败与
   concurrency/recovery，并使用准确 source file、symbol 和代表性 test 引用简化辅助细节。
4. 按第 14.2 节重新分类原 coverage differences，删除由 Architecture 过度规定产生的 gap，
   修正文档未准确描述 Python 现状的部分；只有 material implementation gap 继续显式保留。
5. 把本轮确认的分层原则同步到 `AGENTS.md`、`write-doctidex-design-docs`、相关 reference 和
   review lens；保持 cold-read 两轮上限，本需求不再执行新的 cold read。
6. 校验 links/anchors、doctidex reachability、关键 capability traceability、Skill metadata、Python
   tests、Ruff 和 whitespace；记录范围外既有 findings 后把本 Requirement 恢复为
   `implemented`。

### 15.2 验收标准

1. Architecture 对关键领域模型、主要机制、策略、ownership、invariants、状态转换与可观察
   失败给出足够明确的共同设计，同时不规定没有公共 interoperability 意义的字节表示、辅助
   模型、局部算法或 Python-specific mechanics。
2. 模型进入 Architecture 有可解释的重要性依据；当前 Python 的主要 module-level 模型已被
   纳入或映射到合适 authority，临时 DTO、parser 中间对象和局部 helper state 不被强制提升。
3. Python Impls 展开主要 Architecture realization，并可通过 source file、symbol、test 与小型
   示例承载低层证据；文档既不是薄代码清单，也不是源码逐行复述。
4. 原 17 项 differences 已重新分类，Architecture 过度规定或非规范内部差异不再标作 Python
   gap；保留的 gap 每项都能说明被违反的 Architecture authority 及其实际公共、主要机制、
   safety/compatibility 或 interoperability 影响。
5. 本轮不修改 Python product behavior，不进行新的 cold read，不为满足旧 Requirements 或
   archive 链接降低当前 Architecture / Impls 质量。
6. 受影响的仓库规则和 local Skills 与上述边界一致并通过 validator；文档导航、追踪、Python
   regression、Ruff 和 whitespace 通过，范围外既有 findings 被明确报告。

### 15.3 Architecture / Python Impls 实施进展

用户本轮授权的 Architecture / Python Impls 调整已经实施：

1. Architecture 保留关键 tree/root、Git source/revision、external mapping、worktree/cache、
   operation/result 模型及其 ownership、机制、策略和 observable semantics；明确 parser profile、
   canonical encoding/hash、physical storage、lock、辅助模型和局部算法属于 Impls。
2. Validation 不再规定 CommonMark 精确版本、strict destination decode、固定点 closure、逐 clause
   suppression、content-addressed cursor 或 provisional invalid-root flow；保留 protocol conclusion、
   scope/support、deterministic candidate 和 stale-cursor rejection 的产品边界。
3. External design 已与 Python 当前机制对齐：install key 以 owner/source/fixed selector 为主，
   default provenance 的 physical key 处理下沉 Impls；manifest identity 不再指定 RFC 8785；link
   publication 只要求可诊断和可重试，不固定 mapping-first；generic `content_root`、stale worktree
   record、blocked partial effects 与 `requires_user` 采用当前可观察语义。
4. Python Impls 为 protocol、root、validation、CLI/results、source/storage、external 和 worktree
   主要 modules 增加直接 source links，并把 helper facts、parser 中间状态和低层 algorithms 留给
   source，不再逐项建立 Architecture coverage row。
5. 原 17 项 differences 中，16 项已重分类为 Python realization choice、当前 operating boundary
   或由过度 Architecture contract 制造的表面差异，不再标作产品 gap。唯一保留的 material
   limitation 是 restore 重建 runtime install 时遗漏 validator required 的 `requested_default`，
   可能使 payload 恢复后的后续 runtime read blocked。

该 limitation 的后续修复由 [DX-REQ-0010](0010-fix-restore-runtime-record.md) 负责；本链接经用户
明确授权添加，不改变 `DX-REQ-0009` 的 `approved` 状态或既有结论。

本轮没有修改 Python source/tests/public behavior，也没有执行新的 cold read。Architecture / Python
Impls 的链接、回归、静态检查和 doctidex scoped validation 已完成；第三阶段尚余 `AGENTS.md`、
design/review Skills 与 references 中偏向逐 module、逐 attribute 穷举的持久规则收敛。该规则同步
不在用户本轮只调整 Architecture / Impls 的授权范围内，因此本 Requirement 保持 `draft`。

### 15.4 Architecture / Python Impls 验证结果

- `git diff --check` 通过。
- Python tests 31 项通过；`python -m ruff check impls/libs/python` 通过。
- 当前 Architecture / Python Impls 的本地 Markdown targets 均存在；新增 source links 可定位到
  对应 Python modules 与 tests，页面 anchors 与当前 headings 一致。
- `doctidex-git validate . --scope /docs --scope /impls --json` 完成完整 scoped scan；结果只包含
  根 `index.md` 的 5 条既有 `link_annotation_invalid`，没有新增 `docs/` 或 `impls/` finding。
- 按用户要求没有启动新的 Architecture-only 或 Architecture + Impls cold read。

## 16. 第四阶段：维护规则拆分与精炼

### 16.1 需求意图与 authority 边界

当前 `AGENTS.md` 和 `write-doctidex-design-docs` 在多次迭代后同时保存了 Architecture、Impls、
Requirement 的详细维护规则，`review-doctidex-repository` 也复制了部分相同判断标准。第四阶段
把规则按用途集中到唯一 authority，减少 agent 每次任务需要加载的无关上下文：

1. 以 `write-doctidex-architecture-docs` 取代综合 Skill 中的 Architecture authoring authority，
   负责共同模型、机制、策略、surface、workflow、语言中立边界、结构替换和有界 cold-read
   validation。
2. 以 `write-doctidex-impls-docs` 负责 variant 条件、具体 realization、physical state、代码
   ownership、source/test evidence、material limitation 与 Architecture coverage；辅助实现细节
   可以直接引用源码，不要求逐 module 或逐 attribute 转写。
3. 以 `write-doctidex-requirement-docs` 负责 Requirement 创建、状态、large Requirement、依赖和
   历史边界，并完整保存当前用户与 agent 的协作机制：创建意图即落盘、active Requirement
   先更新、question/answer、用户 comment、授权边界、`approved` 保护和反馈后的状态回退。
4. 删除被三个专用 Skill 取代的 `write-doctidex-design-docs` 及其重复 reference；三个新 Skill
   只在真实跨层边界互相路由，不复制彼此规则，也不形成循环 reading chain。
5. `AGENTS.md` 保留 repository layout、通用 working rules、文档三层关系和 Skill 选择顺序；
   Architecture、Impls、Requirement 的具体维护与验证规则分别指向对应 Skill，不再维护第二份
   完整清单。
6. `review-doctidex-repository` 保留 review authorization、scope、independent pass、finding、repair
   和 handoff contract；文档类型的具体合规标准链接到三个 authoring Skills，review lens 不再
   复制其完整规则。

### 16.2 实施计划

1. 盘点 `AGENTS.md`、综合 design-doc Skill、references 和 review lens 中的规则，按
   Architecture / Impls / Requirement / repository orchestration / review process 指定唯一 owner。
2. 使用 Skill 初始化工具建立三个 repository-local Skills 和各自 `agents/openai.yaml`；将规则
   精炼迁移到对应 Skill，必要时只保留一层浅 reference。
3. 收敛 `AGENTS.md`：保留目录介绍、authority order、触发和跨层顺序，删除已由专用 Skill
   拥有的详细 lifecycle、模型 completeness、Impls module checklist 和 cold-read procedure。
4. 更新 `review-doctidex-repository` 及其 lens，使其按审查对象读取对应专用 Skill，并保留
   review-only / repair authorization 和 finding contract 的唯一 authority。
5. 删除旧 `write-doctidex-design-docs`，检查仓库内所有名称和路径引用，修复当前维护入口但不
   改写无关历史文档。
6. 验证所有新增和修改的 Skills、metadata、链接、whitespace 与 doctidex scoped structure；使用
   不泄露预期答案的任务验证 Architecture、Impls、Requirement 和 review 路由能够独立触发。

### 16.3 验收标准

1. 三类文档各有一个明确的 authoring Skill authority；旧综合 Skill 和重复 reference 不再存在。
2. `AGENTS.md` 能让 agent 选择正确 Skill、理解跨层更新顺序和仓库边界，但不复制专用 Skill
   的详细规则。
3. Requirement Skill 完整覆盖当前用户-agent 协作和生命周期语义，拆分过程中没有弱化 comment、
   question/answer、授权、依赖、large Requirement 或 approved-history 保护。
4. Architecture Skill 保持关键模型与机制的平衡边界及两轮 cold-read 上限；Impls Skill 保持
   complete realization 要求，同时允许通过准确源码和测试引用承载辅助细节。
5. Review Skill 仍可执行授权、scope、independent lenses、finding aggregation、repair 和 re-review，
   但 Architecture / Impls / Requirement 标准来自对应 authoring Skill 而不是本地副本。
6. 新 reading chain 浅且无环；metadata 与触发描述能区分三类 authoring 请求，review 不会因普通
   写作请求隐式触发。
7. 所有 changed Skills 和 `agents/openai.yaml` 通过 validator；当前链接、whitespace 与 scoped
   doctidex validation 没有新增 finding。

### 16.4 实施结果与验证

第四阶段已经完成：

1. 新建 `write-doctidex-architecture-docs`、`write-doctidex-impls-docs` 和
   `write-doctidex-requirement-docs`，各自拥有对应文档类型的 authoring 与 validation contract。
   三者不共享综合 reference；跨层路由明确只加载尚未读取的 Skill，并在原 workflow 继续。
2. Requirement Skill 集中保留 lifecycle、large Requirement、question/answer、user comment、active
   artifact update、dependency、authorization 和 approved-history 保护。Forward test 暴露了
   “向 approved Requirement 添加回链也属于改写历史”的歧义，规则已改为未经用户授权只记录
   pending reciprocal edit，并保持 active record incomplete。
3. `AGENTS.md` 从 392 行压缩为 100 行，保留 repository layout、doctidex organization、通用
   working rules、三类文档 authority 表和跨层执行顺序；不再复制具体 lifecycle、model、Impls
   module 或 cold-read checklist。
4. `review-doctidex-repository` 保留显式 review/repair authorization、scope、independent lenses、
   finding aggregation、repair loop 和 handoff。Requirement、Architecture、Impls lens 改为读取
   对应 authoring Skill，旧 implementation-document checklist 已删除。
5. 已删除 `write-doctidex-design-docs`、其 metadata 和 `document-types.md`。当前 `AGENTS.md` 与
   `.agents/skills/` 不再引用旧入口；Requirement 中的旧名称仅作为阶段实施历史保留。

验证结果：

- 五个当前 repository-local Skills 及其 `agents/openai.yaml` 均通过 `quick_validate.py`。
- 四个 fresh raw-request forward tests 分别覆盖 Architecture、Impls、Requirement 和 review；
  Architecture-first / Impls-only / Requirement collaboration / review-only 路由均能独立确定
  authority、授权边界与下一步，Requirement finding 已按上文修复。
- 当前维护入口和 Requirement 的本地 Markdown targets 均存在；无 template TODO 或旧综合 Skill
  的 current reference；`git diff --check` 通过。
- `doctidex-git validate . --scope /docs --scope /impls --json` 完成 scoped scan，只保留根
  `index.md` 的 5 条既有 `link_annotation_invalid`，没有新增 finding。
- 本阶段没有修改产品代码、tests、Published Skills、Architecture / Impls 内容、archive 或
  approved Requirement history，也没有启动新的 Architecture cold read。

本 Requirement 已达到第四阶段验收标准，并在用户于 2026-08-01 明确确认后从
`implemented` 转为 `approved`。
