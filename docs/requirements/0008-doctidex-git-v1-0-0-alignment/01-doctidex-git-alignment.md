# 子需求 0008.1：doctidex-git 面向协议 v1.0.0 的 Architecture 设计

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0008.1` |
| 状态 | `approved` |
| 日期 | 2026-07-30 |
| 批准日期 | 2026-08-01；用户明确批准大型 Requirement 0008 及其全部子需求 |
| 来源 | 用户补充 doctidex-git 在协议 `v1.0.0` 下的产品定位、Skill 收敛方向、外部 Git 仓库读取方式与多根维护目标，要求拆分 Architecture 与 Details，明确默认 revision、受管路径解析能力与 validation 的根内关注目录集合，将旧设计直接归档后从零编写 v1.0.0 Architecture，并要求新 Architecture 正文以中文组织；后续进一步要求 install 不接受 TARGET_PATH、把安装内容固定在根 `/.doctidex` 的受管路径且排除出宿主 Git 追踪，以可版本化恢复信息重建安装，并使既有 external link symlink 在恢复后无需修改；随后要求延续 v0.x 的环状依赖支持，将直接安装与从安装内容发现的依赖安装分层、按 source selector 隔离安装目录，把 CLI 创建的可写 worktree 扁平置于宿主根 `/.doctidex`，在 Maintenance Skill 中优先引导直接维护当前仓库当前 commit，并明确这些约束只适用于 agent 主动选择 doctidex-git 受管 install/maintenance 工作流的情况；之后要求重新组织 Architecture，消除连续需求补丁造成的内容错位并把事实归入恰当的权威页面；后续要求 Read Skill 在主仓库或 install 仓库中遇到不可访问 symlink 时引导调用 `external link-parse`，并让该命令识别 install 仓库内因依赖尚未在主仓库展开而合法缺失的 link target；本轮确认增加不进入 Published Skills 的 bare source cache cleanup 命令，只允许清理没有有效 linked worktree 且其余登记全部可 prune 的 source cache |
| 所属大型 Requirement | [DX-REQ-0008](overview.md) |
| 前置协议需求 | [DX-REQ-0005：协议升级至 v1.0.0](../0005-protocol-v1-0-0.md) |
| 后续实现需求 | [DX-REQ-0008.2：Python Details 与实现](02-python-details-and-implementation.md) |
| 协议基线 | [`doctidex` `v1.0.0`](../../../spec/overview.md) |
| 设计产物 | [doctidex-git v1.0.0 Architecture](../../doctidex-git/architecture/index.md) |
| 历史设计基线 | [doctidex-git `0.1.0` Archive](../../doctidex-git/archive/v0.1.0/index.md)、8 个旧 Published Skills 与现有 CLI/JSON surface |
| 影响范围 | doctidex-git Architecture、Published Skills 及 metadata、语言无关 CLI/JSON 契约、旧设计归档与导航 |
| 兼容性 | 不兼容重构；不提供 `0.1.0` 配置、状态或工作流的迁移与兼容模式 |

本文保存语言无关设计的需求来源、用户决定和实现边界。完整目标契约现由
[v1.0.0 Architecture](../../doctidex-git/architecture/index.md) 负责；在本子需求完成时，该
设计尚未由 Python 和 Published Skills 实现。`0.1.0` 行为及匹配 Details 已按用户指示成套
归档，不能与 v1 surface 混用；后续 [DX-REQ-0008.2](02-python-details-and-implementation.md)
已完成 Python、Details、Published Skills 与测试落实。

## 1. 需求意图

### 1.1 问题与变更性质

doctidex-git 当前围绕协议 `v0.1.0` 的 mount namespace、旧过滤字段、读取投影和维护
scope 建立了 8 个 Published Skills 与一组相互依赖的命令。协议 `v1.0.0` 已删除
`doctidex.mounts`、`atomic_entries`、`excludes`、`protected` 及其维护语义，改用
`boundary-set`、`atomic-indexing`、`unsafe`、根内 link 和结构化 link 注释。继续在旧
surface 上补丁式修改会保留已经失去协议基础的心智模型，无法达到本需求要求的精简。

本需求因此定义一次不兼容的产品重构，而不是旧插件的兼容升级。新 surface 只面向协议
`v1.0.0`，不向用户继续提供旧 mount、effective commit、projection、maintenance scope
或旧 Skill 工作流，也不提供双版本模式。

### 1.2 目标定位

doctidex-git 仍是供 agent 在 Git 管理的 doctidex 目录树中工作的辅助插件，由一组
Published Skills 和共享的确定性 CLI 组成。一个 Git working tree 的根目录仍可同时
成为 doctidex 根，只要其可观察结构满足协议；Git 身份本身不构成 doctidex 符合性，
也不把整个 Git 仓库自动变成一个 doctidex 根。

产品从“规定完整工作流”转为“解释协议相关注意事项并提供 Git 特有的客观辅助能力”：

- 阅读和搜索主要由 agent 的原生文件、搜索与 shell 工具完成，Skill 提供建议性路径，
  不建立访问网关。
- Maintenance Skill 区分协议强制限制与产品建议原则，并编排确定性 validation、外部
  Git 仓库只读引入和独立 worktree 维护。
- 插件管理状态不是协议事实。用户用 symlink、submodule、文件系统挂载或其他方法呈现
  外部内容，只要最终可观察目录树满足协议，就不影响阅读、搜索或符合性。
- 普通本地维护不依赖插件安装记录；外部仓库维护可以直接从 URL、Git working tree 或
  Git metadata location 建立工作现场。

面向 agent 和程序的稳定集成面是 CLI 及其 JSON 结果。本需求不要求稳定 Python library
API；具体实现边界属于 [DX-REQ-0008.2](02-python-details-and-implementation.md)。

### 1.3 Architecture 目标

1. 把 8 个 Published Skills 收敛为 Overview、Read、Maintenance 三个职责明确的 Skill。
2. 使 agent 仅阅读 Overview 和一个相关专项 Skill 即可完成受支持工作流，不需查看源码、
   Architecture 或 `--help` 猜测命令。
3. 让 Read 保持建议性和原生工具自由，同时完整解释协议 `v1.0.0` 的 link、
   `boundary-set`、`atomic-indexing`、`unsafe` 与结构化注释。
4. 定义只依据可观察目录树判断协议符合性的离线 validation；插件内部状态不得改变
   protocol finding。
5. 定义任意 Git 仓库以根内逻辑只读路径被引用的用户工作流，并正确维护相关边界和
   unsafe 元信息。
6. 定义从受管只读路径、URL、Git working tree、gitdir 或 gitfile 为指定 revision 创建
   独立可写 worktree 的多根维护工作流。
7. 保留 cwd 提供默认上下文的易用性，同时让根作用域命令接受显式根路径，调用方不必
   为选择根而切换 cwd。
8. 为每个公开概念、命令、结果、失败、生命周期和非原子边界形成可直接落实的语言无关
   Architecture 契约，再由 Details 映射到 Python。
9. 允许 validation 以一个或多个 doctidex 根内目录限定关注范围，在不牺牲判断正确性的
   前提下过滤无关 finding 和 semantic candidate，并让调用方明确区分范围结论与全根结论。
10. Architecture 的标题、段落、列表、表格说明和图示说明以中文组织；CLI、JSON 字段、
    枚举、状态标识及无法准确翻译的既有技术术语保留英文，不为追求全中文牺牲精确性。
11. 收紧 external 生命周期：install 只建立工具分配的 `/.doctidex` 内部安装，不接收
    `TARGET_PATH`；link 才建立可由宿主 Git 追踪的相对 symlink；版本化恢复信息必须能在
    安装内容缺失时重建相同内部路径，使已存在的 symlink 无需改写即可恢复读取。
12. 延续环状依赖支持：direct install 进入恢复清单；从既有 install 发现的 dependency
    install 扁平落在同一宿主根而不递归、不进入恢复清单；宿主仓库成为依赖时仍使用独立
    fixed-commit install，不能折叠到可写当前目录。
13. 同一 canonical Git source 的不同 normalized selector 使用不同 install ID/path，即使
    resolved commit 相同也不能合并；同 selector 的重复请求才可幂等复用。
14. CLI 创建的可写 worktree 也扁平置于 selected root 的 `/.doctidex` 受管命名空间，不能
    在 install 或另一个 worktree 中递归创建；Maintenance Skill 对当前仓库当前 commit 的
    维护优先使用当前 working tree，但保留显式隔离 worktree 的选择。
15. Read Skill 在任一正在阅读的 doctidex 目录树中遇到原生工具无法访问的 symlink 时，
    引导 agent 先调用 `external link-parse` 获取客观映射；命令既支持主仓库路径，也支持
    受管 install 中携带的 portable external link，并把依赖未在 owner root 展开与 mapping
    损坏区分开。
16. 提供独立、显式且默认 dry-run 的 `cache clean` 管理命令，以 source URL 定位 shared
    bare object cache；只有 Git 证明没有有效 linked worktree 且其余登记全部 prunable 时
    apply 才可删除。该命令不进入三个 Published Skills，也不由其他生命周期隐式触发。

### 1.4 非目标

- 不改变或扩充 doctidex 协议；实现行为不能被描述为新的符合性条件。
- 不提供从 doctidex-git `0.1.0` 到新 surface 的升级教程、状态转换器或兼容读取模式。
- 不要求所有外部仓库符合 doctidex，也不把 `unsafe` 解释为不可信、不可读或不可维护。
- 不以 CLI 包装成熟的 `find`、`rg`、文件读取、`git status`、`git diff`、commit、push、
  merge 或普通 worktree 操作。
- 不让 CLI 生成 index 说明、link 文本、log 内容或其他需要 agent 语义判断的正文。
- 不把逻辑只读入口描述为安全沙箱或访问控制；写入应转到明确的可写 worktree。
- 不在 Architecture 中规定 Python 模块、类、函数、内部目录、cache key、锁或算法。
- 不把 doctidex-git 的 install/worktree 生命周期设为 agent 的唯一外部读取或维护方式；本
  需求中的扁平安装、恢复清单和 worktree 位置只约束明确选择这些受管命令的调用。

## 2. Architecture 设计决策

### 2.1 三 Skill 产品结构

| Skill | 职责 | 不负责 | 使用的 CLI 能力 |
|---|---|---|---|
| `doctidex-git-overview` | 建立共同心智模型、术语、根选择、输出/失败约定、安全边界，并把任务路由到一个专项 Skill。 | 重复专项步骤，或要求每次调用前重新阅读 Overview。 | 只说明共享命令语法与结果约定。 |
| `doctidex-git-read` | 建议如何沿 index 和 Markdown link 渐进阅读、如何结合原生搜索、如何识别边界、unsafe 与结构化 link 注释；主仓库或 install 中遇到不可访问 symlink 时引导解析 current-owner 或 portable mapping。 | 强制阅读顺序、替代原生工具、自动安装/恢复依赖或修改外部内容。 | 普通读取不依赖 CLI；不可访问 symlink 按需使用 `external link-parse`，需要完整结构判断时可路由到 Maintenance 的 validation。 |
| `doctidex-git-maintenance` | 说明维护 safe/unsafe、index、log、可达性和 link 时的强制限制与建议原则；编排 validation、外部 Git 只读引入和 worktree 维护。 | 替用户作语义决策或 Git 交付决定。 | `validate`、外部仓库呈现/解析和 worktree 生命周期命令。 |

阅读链必须显式且无环：不熟悉共同模型的专项 Skill 可以先要求读取 Overview，然后回到
原专项 Skill；Overview 只路由，不反向要求重读专项 Skill。已经加载过的 Overview 不得
因工作流切换而重复加载。原 Setup、Mount、Workspace、Validate、Review 和 Maintain
Skill 中仍有价值的用户信息，应分别并入上述三个 Skill；旧 mount/filter 专属内容删除，
不得作为历史兼容说明继续占用 published Skill 上下文。

### 2.2 Read 工作流

Read Skill 应先建立“建议而非网关”的使用画面：agent 可以从负责 `index.md` 开始，也
可以根据任务直接使用原生搜索定位候选，再回到负责 index 和适用 `log.md` 理解范围。
Skill 必须覆盖：

1. `/` 是当前 doctidex 的链接根，不是宿主文件系统根；相对路径词法规范化后不得越出
   doctidex 根。
2. 读取 link 时检查其后连续 HTML 注释块中是否存在 `doctidex:` 结构化注释，并理解
   `cross-boundary-point` 与 `unsafe`；其他注释不阻断关联。
3. 读取负责 index 的 `boundary-set`、`atomic-indexing` 和 `unsafe`，按最近负责制理解
   作用域，不把祖先配置带过接管边界。
4. `boundary-set` 只表示根内路径视角的内容边界；`unsafe` 只表示符合性例外；两者都
   不限制普通文件读取，也不表达信任、权限或维护授权。
5. 可达性只沿有效 Markdown 文件路径 link 计算，但 agent 搜索内容不受可达图限制。

Read 不再需要旧 `context`、`inspect`、`resolve` 或 lazy `mount prepare` 才能使用原生
文件工具。根或 link 语义存在歧义时，Skill 先用协议结构和原生路径事实消歧；需要完整
符合性判断时运行 `validate`，而不是恢复旧 mount 状态。

当 agent 已到达一个目录，但需要判断它是否为 doctidex-git 管理的外部呈现、内容来自
哪个 Git revision，或后续维护现场应从仓库内哪个相对路径继续时，可以按需运行
`external link-parse`。该命令提供辅助事实，不是读取外部路径的必经步骤，也不替代
协议结构判断或 validation。

### 2.3 Maintenance 的维护指导

Maintenance Skill 必须把信息分成两层：

- **协议强制限制**：直接来自 `v1.0.0` 的 frontmatter、索引/日志连续性、局部配置、
  可达性、根内 link、结构化注释与符合性规则。
- **产品建议和 Git 安全边界**：例如先读负责 index、保持 unsafe 范围紧凑、保留无关
  用户变更、先看 diff、避免静默切换 branch，以及何时使用独立 worktree。这些不得
  冒充协议要求。

Git 根兼作 doctidex 根时，`.git` 可按其生成内容现状声明为 `unsafe`，但仍需从负责
index 建立入口并按协议给 link 添加 `unsafe: true`。这是一种有效组织方式，不是协议
对所有 Git 仓库的固定要求。

当任务维护当前宿主 Git working tree 且基准 selector 就是其当前 commit 时，Maintenance
Skill 应优先引导 agent 在当前 working tree 直接使用原生文件与 Git 工具；不要求先调用
`worktree open`。已有无关变更、需要隔离或用户明确要求时，agent 仍可选择受管 worktree。
这一建议不自动确认写入权限、交付 branch 或 dirty changes 兼容性。

### 2.4 Validation 用户接口

目标 surface 使用 `doctidex-git validate [ROOT] [--scope INTERNAL_DIRECTORY]...`。显式
`ROOT` 必须是现有 doctidex 根目录本身；省略时从 cwd 选择唯一包含它的根，找不到或存在
多个候选时 blocked。`INTERNAL_DIRECTORY` 是不带 anchor 的 doctidex 根绝对目录路径，
例如 `/docs/api`；必须词法规范化后仍位于所选根内，并对应现有、可读取目录。该选项可
重复；省略表示关注整个根。实现先规范化并去重，且祖先 scope 已覆盖后代 scope 时只保留
祖先。非法 scope 以稳定 `scope_invalid` blocked，不降级成全根扫描。命令始终离线、只读、
确定性，不调用 AI，不获取 Git remote，也不创建外部读取或维护现场。

validation 必须区分 `full` 与 `scoped` coverage。scoped validation 仍可读取关注目录之外
为正确解释它们所必需的支持内容，包括根与祖先负责 index、适用局部配置、可达性所需的
负责 index/导航文档，以及关注范围内 link 的必要目标；这不把所有根外内容纳入输出。
findings 与 semantic candidates 只返回关注目录内的问题，以及直接阻止解释或验证关注
目录的支持路径问题。collection total 在该过滤之后计算。

一次扫描分别产生：

- `coverage: full|scoped` 与规范化后的 `scopes`：明确结论覆盖整个根还是调用方选择的目录
  集合；有效 scope 集合为 `["/"]` 时 coverage 为 full，否则为 scoped；
- `protocol_structure: pass|fail` 和 `findings`：在声明的 coverage 及其必要支持闭包内逐项
  覆盖根、UTF-8 Markdown、frontmatter、
  index/log 连续性、三个局部配置及最近负责制、atomic/unsafe 约束、可达性、根内 link、
  边界穿越、结构化注释和保留名称；
- `semantic_review: clear|required` 和 `semantic_candidates`：只报告协议中需要人或 agent
  判断的 index 说明充分性、unsafe 范围紧凑性等候选，不把候选算作确定性缺陷；
- `scan_complete`：只有当前 coverage 和必要支持闭包中所有应检查 safe 内容都被读取并
  判断时为 true；读取失败会形成 protocol finding 并令该字段为 false，不能用已扫描部分
  宣称当前 coverage 通过；
- `collection`：分别给出 findings 与 semantic candidates 的 total、returned、truncated，
  以及恢复两个列表位置的同一个 opaque cursor。

协议 finding 使用第 2.8 节定义的稳定结构；至少区分 `root_invalid`、`document_unreadable`、
`frontmatter_invalid`、`index_continuity_invalid`、`log_continuity_invalid`、
`local_config_invalid`、`local_config_scope_invalid`、`atomic_indexing_invalid`、
`unsafe_declaration_invalid`、`path_unreachable`、`link_path_invalid`、
`link_annotation_invalid` 与 `reserved_name_conflict`。一个文件可产生多个独立 finding，
同一客观问题不得同时作为 semantic candidate 重复报告。

`protocol_structure: pass` 只表示声明 coverage 及其必要支持闭包中未发现协议 error。
当 `coverage: scoped` 时，它不能被表述、显示或消费为全根符合；全根结论必须省略
`--scope` 重新运行。pagination cursor 必须绑定规范化 scope 集合，调用方翻页时必须提供
规范化后相同的集合；原始输入次序、重复项或被祖先覆盖的后代不影响集合 identity。

结果不包含独立的“插件安装就绪”符合性域，也不因路径没有 doctidex-git 管理记录、不是由
外部命令创建、存在普通 submodule，或缺少实现级状态而失败。Git status、remote 新旧、
credentials 和外部 presentation 完整性不是 protocol finding；受管 mapping 损坏只由
`external link-parse` 报告。未来若需要 Git 或网络检查，必须是显式、非协议的独立操作。

### 2.5 外部 Git 仓库的只读引入与恢复

Maintenance 提供 `external install`、`external link`、`external restore` 和
`external link-parse`。install 在所选根的 `/.doctidex` 下建立工具分配的稳定内部安装；
link 从该安装或既有受管 link 的子目录建立用户指定的相对 symlink；restore 从可版本化
恢复信息重建缺失安装；link-parse 为 Read 与 Maintenance 共同提供按需路径事实。四个命令
都只管理 doctidex-git 自己创建的状态；手工 symlink、submodule、文件系统挂载和其他根内
呈现仍由原生工具维护，且不因“未受管”而降低协议地位。

本节的 install role、扁平位置、manifest inclusion、link 与 restore 规则只在 agent 决定
使用 doctidex-git external 工作流时生效。agent 可以选择其他安装或呈现方式；CLI 不登记
它们，也不能把未登记状态转化为 validation、读取或维护失败。

`TARGET_PATH` 只属于 `external link`：它是相对于所选 doctidex 根的非空 POSIX 路径，
不得以 `/` 开头，不得包含空段、`.` 或 `..`，规范结果必须位于根内。
`SOURCE_DIRECTORY`、`PATH` 和 `ROOT` 是文件系统路径，相对值以 cwd 为基准。
`--root ROOT` 必须指向根目录本身；省略时 install、link 和 restore 从 cwd 选择唯一根，
link-parse 则从 `PATH` 的外层受管 presentation 或可读父目录恢复 owner root。创建命令不得
覆盖未受管文件、目录或 symlink，也不得与同一根中的既有受管对象冲突。

`external install` 的精确语法是：

```text
doctidex-git external install --url URL [--root ROOT]
  [--commit COMMIT | --tag TAG | --branch BRANCH]
  [--dependency-of INSTALL_ID]
  [--dry-run | --apply] [--json]
```

`URL` 必须标识完整 Git repository；该命令不接受 repository subtree selector。三个
revision 选项互斥，值必须是单一 full commit object ID、tag name 或 branch name，不能
使用任意 revspec。tag 会 peel 到 commit；任何不能唯一解析为 commit 的输入都 blocked。
不带 `--apply` 与显式 `--dry-run` 等价，允许联网和使用调用期临时数据完成 source、
revision 与 safe/unsafe 规划，但不得写 doctidex 根、受管 registry、持久 Git object store
或 presentation。`--apply` 才能持久获取 objects 并发布结果。

首次创建的用户可观察契约是：

1. 将 source revision 解析为不可变 commit，并建立可重新创建的逻辑只读工作状态；
   branch/tag 只保留为输入来源，任何 install 与 link 都固定到 `resolved_commit`。
2. 以 selected root、canonical source identity 和 normalized revision selector 组成
   `install_key`，为每个 key 分配唯一、稳定且不透明的 `install_id`，并由它确定
   `/.doctidex` 下的稳定 `install_path`。用户不选择该路径；精确子命名空间和编码属于
   0008.2 Details，不成为公共路径语义。
3. 在 `install_path` 发布 repository 根的逻辑只读工作状态，并返回 install ID、根内路径、
   原生文件工具可用的 working path、source、resolved commit、网络效果、发生的写入和
   下一步。同 source、不同 selector 即使解析到同一 commit 也使用不同 install ID/path；
   只有同 key 重试才幂等复用。
4. 把 `/.doctidex` 内受管命名空间作为一个保守的协议边界处理，并在其负责 index 中建立
   一次可达入口；安装载荷即使被 Git 忽略，仍是协议可观察内容，不能绕过 validation。
   该命名空间按实现扩展的 unsafe 内容处理，不能提升为协议固定子路径。
5. 不生成 index 正文或内容 Markdown link。结果提示 agent 在需要的位置用 external link
   建立可达 symlink，并按协议补充从 safe 文档进入 unsafe 内容所需的 link 注释。
6. apply 先持久准备固定 commit，再写恢复信息与精确 Git 排除规则，最后发布稳定安装路径；
   任一步失败都逐项报告已完成和未完成结果，不宣称 Git 状态、安装、恢复信息与文档写入
   跨系统原子。

安装载荷必须排除在包含所选 doctidex 根的宿主 Git repository 的追踪范围之外。工具通过
宿主 repository 根 `.gitignore` 中仅覆盖受管安装载荷的精确 root-relative 规则保证这一
点；恢复清单及 `external link` 创建的 symlink 不得被该规则覆盖。工具不执行 `git add`、
`git commit`、`git rm --cached`，也不改写无关 ignore 规则。若无法唯一确定宿主 Git
repository、安装载荷已有 tracked entry、已有 ignore 规则与目标可追踪性冲突，或恢复清单
及 link target 被有效 ignore 规则排除，install/link 必须 blocked，并给出由用户使用原生
Git 工具处理的动作。结果分别报告 ignore 文件和恢复清单的
`absent|tracked|modified|untracked` 状态，让用户知道哪些可恢复信息仍需提交。

恢复清单位于安装载荷的 sibling 且不被 ignore。普通调用建立 `direct` install，并把它写入
清单；带 `--dependency-of INSTALL_ID` 的调用建立或复用 `dependency` install，只写运行期
受管关系而不进入清单。清单设计为可由宿主 Git 追踪，至少包含 schema version、direct
install 的 ID、去除凭据的 source identity、revision selector、默认分支来源、固定
resolved commit、稳定 root-internal install path，以及每个可恢复 external link 的 target
和 repository-relative base。它不得包含 dependency-only install、credentials、宿主绝对
路径、cache 路径或 lock。CLI 报告清单是 absent、tracked、modified 还是 untracked，但不
代替用户提交它。

`--dependency-of` 的 INSTALL_ID 必须属于 selected root 中现有、完整的 install。该参数明确
表示 agent 是从该 install 的内容进一步发现依赖；命令仍以 selected root 为 owner，把新
install 与所有 worktree 并列放在该根的 `/.doctidex`，绝不在 parent install 内递归创建。
dependency 关系只用于检测/表达图边，CLI 不递归读取依赖声明或自动安装下一层。B 依赖 C、
C 又依赖 B 时，同 install key 命中既有 B 即结束，不继续展开；同一 dependency 被多个 parent
请求时也复用同一 install。

如果 dependency request 指向宿主 Git repository 自身，仍须创建或复用独立 fixed-commit
install，不能返回当前可写 working tree。source identity 和 commit 可以可靠匹配且对象已在
宿主 `.git` 中时，实现可以直接复用这些本地 Git objects 创建逻辑只读 install，不联网也不
复制可写 working tree；对象复用机制属于内部信息，Skill 只需说明返回路径仍是独立快照。

direct 与 dependency 使用相同 install key。dependency-only install 后续被普通 install
请求时原地提升为 direct 并加入恢复清单，不创建第二份目录；direct install 被 dependency
请求时保持 direct，不能降级。`external link` 只能指向 direct install 或其 link；若 agent
需要为 dependency-only 内容建立可由宿主 Git 追踪且可恢复的 symlink，必须先以相同
source/selector 运行普通 install 完成提升。

调用方显式提供 commit、tag 或 branch 时，安装保留该 selector，并将它解析为当前 commit。
省略 revision 时，安装只在首次创建该受管呈现时发现远端默认分支并解析其当时指向的
commit；默认分支名作为来源信息保存，有效 `revision_selector` 则归一化并持久化为该
immutable commit，而不是保存默认分支这一移动 selector。结果同时返回初次发现的默认
分支名、固定 commit selector 和 `resolved_commit`，不能只返回含糊的“latest”。

此后该 install key 始终对应已保存的 commit。普通文件读取、`external link-parse` 和重复
解析保持离线，不能改变呈现。同 key 再次省略 revision 执行 install/apply 时，必须幂等
复用已保存 commit，不得因远端默认分支移动而隐式重新解析或切换内容。需要另一个 revision
时，调用方显式提供新的 selector；它创建另一个 install，不替换、删除或重定向原 install。
目标 surface 因此不提供 `--replace`。

`external link` 的精确语法是：

```text
doctidex-git external link SOURCE_DIRECTORY TARGET_PATH [--root ROOT]
  [--dry-run | --apply] [--json]
```

`SOURCE_DIRECTORY` 必须位于所选 target root 中一个可完整解析的 install/link 受管路径
内。命令离线，不 fetch、不解析 remote，也不改变 source install。它在 `TARGET_PATH`
建立指向稳定内部 install path 或其子目录的相对 symlink；禁止绝对 symlink 和目录复制
fallback，不支持 symlink 的平台必须 blocked。symlink 的词法 target 不得被宿主 Git
ignore，因而调用方可以用原生 Git 工具 stage/commit 该 symlink。

每个新 link 单独处理 `boundary-set`；只有 source directory 自身可作为通过 validation 的
完整 `v1.0.0` doctidex 根时才标为 safe，否则同步声明该 link 为 unsafe。工具不得因 source
已位于另一个边界，就假定新 link 继承原路径的边界或 unsafe 声明。

source 可以是 repository 内任意目录；alias mapping 保存该目录相对于 repository 根的
起始路径，使其下任意子目录仍能恢复正确的 `repository_relative_path`。同一 target 和
同一 mapping 的重试幂等；不同 mapping、未受管占用、presentation overlap 或损坏 mapping
blocked，external link 不提供隐式替换。apply 创建相对 symlink、更新结构化 frontmatter
和恢复清单，但不 stage 任何文件；dry-run 不写入。两种模式都不联网、不写 Git objects。

`external restore` 的精确语法是：

```text
doctidex-git external restore [--root ROOT] [--install INSTALL_ID]...
  [--limit N] [--cursor TOKEN]
  [--dry-run | --apply] [--json]
```

restore 从版本化恢复清单读取记录，不从 remote 重新发现 default branch，也不重新解析任何
移动 ref。它在记录的稳定 install path 重建记录的 exact resolved commit。现有内容已匹配时
返回 `unchanged`；缺失内容在 dry-run 确认可重建时返回 `planned`，在 apply 成功重建时返回
`restored`；冲突、清单损坏或 source 不可访问时返回 `blocked` item。一个 install 失败不
撤销其他 install 的成功结果。

省略 `--install` 时按稳定 install ID 顺序处理清单中的有界第一页；重复 `--install` 过滤并
去重，只处理指定记录。cursor 绑定 root、恢复清单 identity、规范化 install filter、limit
和 dry-run/apply mode；清单变化令 cursor invalid，单纯恢复本地安装载荷不令其失效。
restore 从同一清单重建必要的内部 install/link mapping 状态，但不重写、不重建也不 stage
已存在的 external link symlink。由于 install path 稳定，恢复成功后这些 symlink 无需任何
修改即可重新工作。

`external link-parse` 的精确调用形式是：

```text
doctidex-git external link-parse PATH [--root ROOT] [--json]
```

`PATH` 可以是现有可读目录，也可以是 symlink 本身，包括 target 不存在的 broken symlink；
相对值以 cwd 为基准。显式 `--root` 选择拥有该 mapping 的 owner root。省略时，若 PATH
位于受管 install/link 内，命令优先恢复该 presentation 的 owner root；否则从 PATH 或其
可读取父目录选择唯一包含根。install 内容自身包含 `doctidex.root: true` 时，该 content root
只用于解释正在阅读的树，不取代 owner root。命令离线、只读，无 dry-run/apply，也不修改
symlink、Git 状态、presentation、registry 或 doctidex 文档。

命令先识别 PATH 是否位于当前 owner root 的受管 install/link；若 PATH 是 install 内容中的
symlink，还会读取该安装仓库版本化的 portable recovery manifest/link mapping。后者描述
该仓库作为原宿主时创建的 external link，其物理 target 可以不存在：依赖应由当前 owner
root 通过扁平 dependency install 提供，而不是在只读 install 内递归 restore。只要 portable
mapping 完整，该状态就是 `dependency_not_installed`，不是 mapping damage；命令返回依赖
source/selector/commit、当前 parent install ID 和 repository-relative path，供 agent 决定
是否调用 `external install --commit RESOLVED_COMMIT --dependency-of PARENT_INSTALL_ID`；
portable branch/tag 只作 provenance，不能重新解析。

若 owner root 已有匹配 source/selector 的 install，link-parse 把原 link suffix 映射到该
install 并返回可由原生工具读取的 `working_path`；它不要求或改写安装仓库内的原 symlink。
主仓库 durable link 的 target 缺失则保持不同语义：返回 `owner_install_missing` 并引导按
恢复清单执行 restore。上述产品解析状态不改变 protocol validation 对最终可观察目录树的
判断。

| 字段 | 类型与缺省 | 含义 |
|---|---|---|
| `managed` | boolean，必需 | 是否识别到 PATH 的 current-owner 或 installed-repository 受管 mapping 身份；不表示 target 可用或 mapping 完整。 |
| `mapping_origin` | `owner_root`/`installed_repository`/null | mapping 来自当前 owner root，还是受管 install 中的 portable manifest。 |
| `created_by` | `install`/`link`/null | 命中的最内层 mapping 由哪个 external operation 建立。 |
| `root` | path，必需 | 拥有当前外部安装与 dependency 展开的 owner root。 |
| `content_root` | path/null | PATH 所在的 doctidex root；主仓库通常等于 root，安装内容可为嵌套 root。 |
| `input_path` | path，必需 | 规范化后的输入目录或 symlink。 |
| `input_kind` | `directory`/`symlink` | PATH 的词法种类；broken symlink 仍为 symlink。 |
| `presentation_path` | path/null | 命中的受管 presentation 根内路径。 |
| `install_id` | string/null | 当前 owner root 中实际提供 target 的 install；依赖尚未安装时为 null。 |
| `install_path` | path/null | 当前 owner root 中 target install 的稳定根内路径。 |
| `install_role` | `direct`/`dependency`/null | 安装是否进入恢复清单；direct 也可能同时被其他 install 依赖。 |
| `dependency_of` | bounded object | parent install ID 的 total、当前最多 100 项、truncated；未受管或没有 parent 时为空摘要。 |
| `dependency_parent_install_id` | string/null | installed-repository mapping 所在的当前 parent install ID；供可选依赖安装使用。 |
| `target_state` | `available`/`owner_install_missing`/`dependency_not_installed`/`unavailable`/`not_applicable` | symlink/目录目标在当前 owner root 中的产品解析状态。 |
| `source_url` | string/null | 去除 credentials 后的 Git URL 或可公开 source identity。 |
| `source_relation` | `host_repository`/`other`/`unknown`/null | 能否可靠确认 source 就是 selected root 的宿主 Git repository。 |
| `revision_selector` | object/null | 显式提供的 commit/tag/branch；省略 revision 时为初次解析后持久化的 full commit selector。 |
| `default_branch` | string/null | 省略 revision 时初次发现的远端默认分支名，仅作为来源信息；显式提供 revision 时为 null。 |
| `resolved_commit` | full commit/null | 只读呈现固定对应的 immutable commit；省略 revision 时与 commit selector 指向同一 commit。 |
| `repository_relative_path` | POSIX relative path/null | 输入目录相对于 Git repository 根的内部路径；仓库根使用 `.`。 |
| `working_path` | path/null | 可直接交给原生文件工具的当前目录路径。 |
| `safe_state` | `safe`/`unsafe`/null | 命中 presentation 时的产品接入分类；未受管时为 null。 |
| `responsible_index` | path/null | 拥有该 presentation boundary/unsafe 条目的 index；未受管时为 null。 |

当 `managed: false` 时，命令返回 `status: ok`，mapping/source/install 字段为 null；
`content_root` 在可确定时仍可返回。该结果只表示“没有可识别的 current-owner 或 portable
mapping”，不表示路径不能阅读或维护。已识别但不完整的 mapping 保持 `managed: true`，
通过 `target_state: unavailable` 和 finding 报告损坏。对于由
`external link` 映射的 repository 子目录，`repository_relative_path` 必须包含 link 的
source 起始路径和输入目录在别名下的后续路径。agent 可以把该相对路径接到选定
maintenance worktree 根，规划同一内容的可写目标，但仍须独立确认 revision、写权限和
交付意图。

current-owner 或 portable record 存在，但 source identity 不可恢复、manifest/link 对不上或
repository-relative mapping 越界时，命令返回 `warning`/`blocked` 并保留可靠字段；不得把
损坏静默降级为 unmanaged，也不得把合法 `dependency_not_installed` 报成损坏。该命令不
判断协议符合性、内容信任或 maintenance 授权，也不访问 remote 或重新解析默认分支。

手工建立的 symlink、submodule、文件系统挂载或其他呈现方式同样有效。validation 只看
最终可观察结构；未使用上述命令不会阻止普通阅读，也不会成为 maintenance worktree 的
失败原因。

### 2.6 多根维护与 worktree

worktree 命令的精确语法是：

```text
doctidex-git worktree open SOURCE [--root ROOT]
  (--commit COMMIT | --tag TAG | --branch BRANCH) [--json]
doctidex-git worktree list [--root ROOT]
  [--source SOURCE | --worktree WORKTREE]
  [--limit N] [--cursor TOKEN] [--json]
doctidex-git worktree close WORKTREE [--json]
doctidex-git cache clean --url URL [--dry-run | --apply] [--json]
```

`SOURCE` 按以下顺序分类：现有目录若位于受管 presentation 内则是 `managed_path`；否则
若是 Git working tree 或 bare gitdir 则分别分类；现有普通文件只有内容可解析为 gitdir
指针时才接受为 `gitfile`；其他值按 Git URL 处理。不存在且不是有效 URL 的本地路径
blocked。submodule working tree 中的 `.git` 是 gitfile，不得误报为无 repository。
所有 open 调用都必须选择 owner root：显式 `--root` 指向 root 本身；managed path 省略时
从 SOURCE mapping 选择唯一 root；其他 source 省略时从 cwd 选择唯一 root。SOURCE 位于
install 或另一个受管 worktree 时，owner 仍是最外层 selected root，不能把只读 install 或
worktree 当作新的存放根。

open 的 revision 必填且三个形式互斥，解析规则与 install 的显式 revision 相同。操作把
它解析为 `base_commit`，在 selected root 的 `/.doctidex` 受管命名空间中创建并登记一个
新的 detached、可写 Git worktree，并返回稳定 owner root、root-internal worktree path 和
filesystem working path。若 SOURCE
是受管 presentation 内的子目录，结果同时返回 repository 根 worktree 和把原
`repository_relative_path` 接到该根后的 `working_path`；其他 source 的相对路径为 `.`。
URL 在本地 objects 不足时可以联网，其他 source 默认离线；网络、凭据或 revision 失败
时不产生伪就绪记录，已有 presentation 与 worktree 不变。

worktree payload 与 install payload 一样由宿主 Git 精确 ignore，但不进入 external 恢复清单；
dirty/clean 生命周期仍由 worktree record 和原生 Git 状态决定。open 是显式创建动作，不
提供 dry-run/apply，也不自动复用另一个现场。存在相同 canonical
source 与 base commit 的受管现场时，结果返回 `reuse_candidate_count` 并使用 warning
提醒调用方；新现场仍保持隔离，因为 commit 相同不足以证明写权限和交付目标兼容。CLI
不自动创建用户 branch、commit、push、merge 或切换其他 working tree；这些动作由 agent
使用原生 Git 工具完成，并在权限、目标 branch 或交付方式不明确时请求用户决定。

list 离线、只读，显式 `--root` 或 cwd 选择 owner root，默认列出该 root 全部受管现场的
有界第一页；`--source` 以同一 source 分类规则
过滤，`--worktree` 只接受受管 worktree 的 exact path，二者互斥。每项返回 source kind、
sanitized source、原始 selector、base commit、worktree path、最初请求对应的
repository-relative path、`clean|changed|unavailable` 状态和可行动 finding。单项不可读
不会丢弃其他项；调用方用原生 `git status`/`git diff` 查看具体变化。

close 只接受 exact 受管 worktree path，是显式生命周期动作，无 dry-run/apply。它必须
重新检查归属和 Git status，仅在现场可证明 clean 时移除 worktree 与受管记录；changed、
unavailable、归属不明或 Git 检查失败均 blocked 并完整保留路径。移除不自动回收共享 Git
objects，也不影响 source repository、只读 presentation 或其他 worktree。

手工创建的 Git worktree 可直接用于维护，但不进入受管 list/close。相同 source/base
commit 只形成 agent 可考虑的复用候选，不能自动合并任务、扩大权限或把不同交付目标视为
兼容。每个最终维护根分别运行 validation、审阅原生 Git diff 和完成交付；跨根结果不是
事务，一个根失败不撤销其他根的已保存工作。

当维护目标就是 selected root 所在当前 Git working tree，且要求的 selector 等于其当前
commit 时，agent 可以并应优先直接在当前 working tree 工作，无需调用 open。若需要隔离
现有变更、并行任务或交付目标，仍可显式 open；CLI 不禁止为当前 source/current commit
创建独立 worktree。上述位置与生命周期约束只适用于 agent 选择 doctidex-git 受管 worktree
命令的情况，手工或其他工具创建的工作现场不受它们约束。

旧 `maintenance scope/open/status/handoff/close` 中仍有价值的原则——按 source/base
commit 识别复用候选、保持不同交付目标隔离、clean 才能安全关闭、handoff 前运行
validation 并审阅原生 Git diff——改写为 Maintenance Skill 指导，不再要求持久化 scope
规划命令。

### 2.7 CLI 与结果约束

目标命令族为：

```text
doctidex-git validate [ROOT] [--scope INTERNAL_DIRECTORY]...
  [--limit N] [--cursor TOKEN] [--json]
doctidex-git external install --url URL [--root ROOT]
  [--commit COMMIT | --tag TAG | --branch BRANCH]
  [--dependency-of INSTALL_ID]
  [--dry-run | --apply] [--json]
doctidex-git external link SOURCE_DIRECTORY TARGET_PATH [--root ROOT]
  [--dry-run | --apply] [--json]
doctidex-git external restore [--root ROOT] [--install INSTALL_ID]...
  [--limit N] [--cursor TOKEN]
  [--dry-run | --apply] [--json]
doctidex-git external link-parse PATH [--root ROOT] [--json]
doctidex-git worktree open SOURCE [--root ROOT]
  (--commit COMMIT | --tag TAG | --branch BRANCH) [--json]
doctidex-git worktree list [--root ROOT]
  [--source SOURCE | --worktree WORKTREE]
  [--limit N] [--cursor TOKEN] [--json]
doctidex-git worktree close WORKTREE [--json]
doctidex-git cache clean --url URL [--dry-run | --apply] [--json]
```

`context`、`inspect`、`resolve`、`init`、`changes`、整个 `mount` 命令族和旧
`maintenance` 命令族不属于目标 public surface；普通任务使用原生文件/Git 工具，
protocol/Git 特有任务由上述新命令承担。`check` 由 `validate` 取代。

命令与结果的已确认设计原则是：

- 保留 cwd 默认上下文，同时为 root-scoped 操作提供显式 ROOT；嵌套根歧义时不得猜测；
- validate 接受可重复的根绝对目录 scope，省略表示全根；结果回显规范化 coverage/scopes，
  并只把 scoped pass 解释为所选目录及必要支持闭包内未发现错误；
- revision selector 区分 commit/tag/branch，所有 resolved/base commit 使用 repository
  object format 的完整 ID，不能硬编码 SHA-1 长度；
- 为 agent/程序提供 versioned JSON envelope、operation-specific fields、stable failure code
  和不透明 diagnostic ID，不能泄漏 credentials、traceback 或内部布局；
- validate、external restore 与 worktree list 的 collection 默认有界并返回
  total/truncation/cursor，其他命令不保留无效果的 pagination option；
- 明确只读、写入、网络、dry-run/apply 和 batch 行为；可能写公开文件的操作必须支持
  无写 dry-run，并且只有显式 apply 才写入；
- install path 由工具稳定分配且不接受用户目标路径；安装载荷由精确 Git ignore 规则排除，
  恢复清单与 link symlink 保持可追踪，CLI 不替用户操作 Git index 或 commit；
- install identity 绑定 root/source/normalized selector；`--dependency-of` 只记录从既有 install
  发现的扁平 dependency edge，不触发递归安装；dependency-only install 不进入恢复清单，
  但可通过普通 install 原地提升为 direct；
- restore 只消费可版本化清单中的 exact commit 和稳定路径，不重新解析 moving ref，也不
  修改既有 link symlink；
- CLI 受管 install 与 worktree 都以 selected root 为 owner 并在其 `/.doctidex` 下扁平发布；
  这些规则不限制 agent 选择其他原生或第三方读取/维护方式；
- 使用可行动错误，说明未完成事项、已保留结果、重试动作及是否需要用户输入；
- cache cleanup 离线处理单个 source，先用 Git worktree metadata 证明没有有效 worktree；
  active、无法分类或并发变化都完整保留 cache，命令不删除 root-owned payload/records；
- 保持确定性且不调用 AI，不把内部 cache、锁或 Git plumbing 变成用户前置知识。

精确参数、省略规则、路径类型与网络矩阵由
[CLI](../../doctidex-git/architecture/interfaces/cli.md) 统一定义；envelope、Finding、
Collection、每个 operation 的必需字段、failure codes 与 exit codes 由
[JSON Schema](../../doctidex-git/architecture/interfaces/cli-schema.md) 统一定义。

### 2.8 公开概念与边界

Architecture 已定义以下公开概念及全部属性：

| 概念 | 必需属性 | 公开语义 |
|---|---|---|
| command context | cwd、显式 root、selected root、operation、target | cwd 只提供默认值；root 必须明确，歧义时 blocked。 |
| external source | source locator、revision selector、default branch、resolved commit | 描述读取内容的 Git 来源、调用方显式 selector 或省略 revision 时的固定 commit selector，以及当前不可变基准；default branch 只记录初次解析来源，不表达协议符合性。 |
| managed install | doctidex root、install key/ID、stable root-internal install path、source、selector、fixed commit、direct/dependency role、parent installs、Git exclusion state、recovery manifest state | 在 `/.doctidex` 下提供按 selector 隔离、可表达环状依赖且宿主 Git 不追踪载荷的只读 repository 根。 |
| external link | install ID、install path、source directory、target path、relative symlink、repository-relative base、boundary/unsafe state | 提供用户选择且可被宿主 Git 追踪的根内入口；恢复安装时无需重写。 |
| recovery manifest | schema、portable source/commit/path facts、link records、Git tracking state | 用版本化信息重建 exact install；不保存凭据或宿主绝对路径。 |
| external path mapping | input path/kind、managed、mapping origin、owner/content root、presentation path、target state、target install、dependency parent、source/selector/commit、repository-relative path、working path | 为不可访问 symlink 的按需阅读决策和 maintenance 路径规划提供客观映射，不构成读取或写入授权。 |
| restore result | install filter、item state、fixed commit、stable path、collection、failures | 有界地报告每个安装是 restored、unchanged 或 blocked；单项失败不撤销其他项。 |
| maintenance worktree | owner root、root-internal path、source、base commit、filesystem working path、clean/changed state、managed state | selected root 的 `/.doctidex` 下扁平独立可写现场；不自动产生交付 branch 或授权。 |
| cache cleanup result | sanitized source、linked/valid/prunable worktree counts、planned/removed/preserved state、failures | 显式回收没有有效 linked worktree 的单个 shared bare source cache；不触碰 root-owned payload 或 records。 |
| validation result | coverage、scopes、status、protocol findings、semantic candidates、scan complete、collection、next actions | 将客观结构失败与 agent 判断分开，并使范围结论不能被误当作全根结论。 |

逻辑只读只规定工作流入口，不承诺安全隔离。`.doctidex` 是协议保留目录，但协议不要求
固定子路径；doctidex-git 可以定义不冲突的实现命名空间，具体路径属于 Details。若任何
实现状态出现在 doctidex 可见树内，最终可观察结果仍必须满足 `unsafe`、可达入口和 link
注释等协议规则。

字段与可见性的权威定义见 [领域模型](../../doctidex-git/architecture/domain-model.md)，
命令、JSON、生命周期和失败分别见 [CLI](../../doctidex-git/architecture/interfaces/cli.md)、
[JSON Schema](../../doctidex-git/architecture/interfaces/cli-schema.md)、
[子系统与生命周期](../../doctidex-git/architecture/subsystems-and-lifecycles.md)和
[约束与失败](../../doctidex-git/architecture/constraints-and-failures.md)。本记录中的表只
保存这些设计对象为何属于需求范围，不再充当第二份接口权威。

## 3. 文档与实现影响

| 层面 | 本子需求的责任 |
|---|---|
| Architecture | 已从零建立 v1.0.0 文档集，以三 Skill user surface 为起点，定义场景、精确 CLI/JSON 契约、公开概念、外部安装的 Git 隔离/恢复/环状依赖、根内扁平 worktree、不进入 Skills 的 shared cache cleanup、可选工作流边界、生命周期、失败、并发与非原子边界；文档已按用户界面、工作流、公共接口、领域模型、内部生命周期、跨工作流约束和 Skill 设计重新归位并建立交叉链接；正文以中文为主，精确保留必要的英文技术标识。 |
| 旧设计归档 | 已按用户指示把 doctidex-git `0.1.0` Architecture 与匹配 Python Details 放入同一版本化 archive，避免历史层失配。 |
| Published Skills | 按新 Architecture 将 8 个 Skill 收敛为 Overview、Read、Maintenance，并保持 installed-product wording、完整命令契约和无环阅读链。 |
| Python Details/实现 | 由 [DX-REQ-0008.2](02-python-details-and-implementation.md) 以已完成设计为输入继续细化并实现，不在本文指定模块或 storage。 |
| 导航 | 已更新 doctidex-git、Architecture、Details、Requirements 和 archive 导航，使目标设计、历史设计和两个子需求互相可达。 |

本子需求交付的是 Architecture 设计，因此文档完成并验证后进入 `implemented`；在当时，
该状态不表示目标 CLI、Skills 或 Python 行为已经存在。用户已明确要求在代码切换前归档旧
设计，新 Architecture 与 Details 导航据此标出当时的实现阶段差异；后续 0008.2 已完成
代码、测试、Details 和 Skills，并使 overview 满足 `implemented` 聚合门槛。

## 4. Requirement 关系

- 本记录定义语言无关目标；[DX-REQ-0008.2](02-python-details-and-implementation.md) 是其
  后续实现需求，必须以已完成的
  [v1.0.0 Architecture](../../doctidex-git/architecture/index.md) 为公开契约输入。

## 5. 验收标准

1. Architecture 明确三个 Skill 的场景、职责、非职责和无环阅读链；Overview 加一个
   相关专项 Skill 足以完成每个支持工作流。
2. Read 保持原生工具自由，并正确说明根内 link、结构化注释、三个局部配置、最近负责制
   和 safe/unsafe 边界；普通路径不要求先调用 CLI，但主仓库或 install 仓库中遇到原生
   工具无法访问的 symlink 时，明确引导调用 `external link-parse PATH`。
3. Maintenance 清楚区分协议强制限制与产品建议，不把 Git 工作流、安装记录、逻辑只读
   或 `.doctidex` 实现命名空间提升为协议要求。
4. validation 的输入、默认、结构结果、semantic candidates、bounded output 和失败契约
   完整；可重复 scope 使用 doctidex 根绝对目录路径，省略表示全根，非法输入 blocked，
   规范化、去重和祖先覆盖规则确定；不包含旧 plugin-readiness 合规门槛。
5. 手工建立的 symlink、submodule、文件系统挂载和外部仓库不会仅因来源方式而导致
   validation 或普通 maintenance 失败。
6. 外部安装与别名工作流完整定义 source/revision、默认分支来源、初次 commit 固定、只读
   结果、repository 子路径映射、边界/unsafe 更新、部分成功和恢复决定；install 不接受
   `TARGET_PATH`，而是按 root/source/normalized selector 分配稳定 install ID 与
   `/.doctidex` 内部路径；同 source 的不同 selector 不共用目录；远端
   默认分支后续移动、重复解析或再次省略 revision 执行 install/apply 均不改变既有安装。
7. 安装载荷由精确宿主 Git ignore 规则排除，恢复清单和 external link 的相对 symlink
   保持可追踪；工具不 stage/commit、不改写无关 ignore 规则，也不自动处理已有 tracked
   payload。restore 可从清单按 exact commit 和原路径重建安装，且不修改既有 symlink。
8. direct install 进入恢复清单；带 `--dependency-of` 的 dependency install 在 selected root
   扁平创建、不递归且不进入清单。环状依赖通过既有 install key 截止；宿主仓库作为依赖
   时仍读取独立 fixed-commit install，不能折叠到当前可写 working tree；dependency-only
   install 建立 durable link 前必须提升为 direct。
9. `external link-parse` 离线、只读地识别主仓库 current-owner mapping 与 install 仓库
   portable mapping，接受可读目录和 broken symlink，完整返回 owner/content root、mapping
   origin、source、selector、commit、repository-relative path 与 target state；主仓库
   install 缺失、install 内合法 dependency 缺失、未受管和真实 mapping damage 均可区分。
10. worktree 工作流支持受管路径、URL、working tree、gitdir 和 gitfile；CLI open 始终选择
   owner root 并把现场扁平置于该根 `/.doctidex`，完整定义 list/status、close、复用建议、
   dirty 保留和 Git 交付边界。Maintenance 优先引导直接维护当前仓库当前 commit，同时
   保留显式隔离选择。
11. 每个公开命令都有精确语法、参数约束、默认/省略、cwd/ROOT 选择、读写/网络、
   dry-run/apply、结果字段、分页和可行动失败说明。
12. 每个公开概念的全部属性、可见性、责任、非责任、不变量和生命周期均有定义；内部
   Python/storage 细节不泄漏为用户前置知识。
13. `context`、`inspect`、`resolve`、`init`、`changes`、旧 mount/maintenance surface
    均从目标 Architecture 与 Skill 设计中移除；`check` 由 `validate` 取代。
14. Architecture 文档计划、Published Skills 计划和 0008.2 的实现输入互相一致，且旧
    Architecture/Python Details 的版本化归档边界明确。
15. 所有未决用户可观察行为均已获得用户决定并从本文移除 `<question>`；随后才能把
    本子需求视为可供 0008.2 完整细化的稳定输入。
16. scoped validation 只返回所选目录及直接相关支持问题，仍检查保证结论正确所需的祖先
    配置、可达导航和 link 目标；结果显式区分 full/scoped coverage，scoped pass 不得被
    消费为全根符合，collection 与 cursor 均绑定规范化后的 scope 集合。
17. `docs/doctidex-git/architecture/` 的叙述性标题、段落、列表、表格和图示说明以中文为
    主，不保留可准确翻译的大段全英文内容；命令、schema、字段、枚举、代码及必要技术术语
    保持原值，翻译不得改变公开接口或设计语义。
18. Architecture 和目标 Skills 明确上述 install/worktree 约束仅适用于 agent 选择
    doctidex-git 受管工作流的场景；原生 Git、手工 worktree、submodule、symlink 或其他
    可满足协议与任务目标的方法保持可选，不因“未受管”而失败。
19. Architecture 按用户接口、工作流、CLI、JSON schema、领域模型、内部生命周期、失败
    约束、Skill 设计和程序集成的职责重新组织；每项事实具有明确的权威位置，其他页面
    通过交叉链接提供所需上下文，不再因逐次补丁形成重复契约或机制内容前置。
20. install 中的 portable external link 即使物理 target 不存在，也不会被 link-parse 误报为
    mapping 损坏；命令返回当前 parent install、依赖固定来源及可选安装动作，匹配依赖已在
    owner root 展开时返回外层 `working_path`，且始终不递归 restore 或改写只读 install。
21. `cache clean --url URL` 默认 dry-run、显式 apply、离线且不进入 Published Skills；它只在
    Git worktree metadata 证明没有有效 linked worktree 且其余登记全部 prunable 时删除对应
    bare source cache，active、损坏或并发变化均保留，且不触碰 install/worktree path、
    manifest、runtime records 或其他 source cache。
