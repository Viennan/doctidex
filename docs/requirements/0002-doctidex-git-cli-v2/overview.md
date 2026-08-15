# 需求 0002：设计 doctidex-git 命令行工具 v2.x.x

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0002` |
| 状态 | `planned` |
| 日期 | 2026-08-07 |
| 来源 | 用户要求设计在 Git 环境中与 doctidex v2 目录树外观规范配套使用的 `doctidex-git` 命令行工具 v2.x.x |
| 影响范围 | `doctidex-git` CLI 的产品目标、Git 工作区与版本库边界、命令与输出契约、目录树识别与导航、校验/诊断、错误与退出状态、兼容性和交付验证 |
| 配套 Architecture | [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) |
| 文档性质 | 大型 Requirement；仅记录总体设计，不授权实现代码、测试或发布配置 |

本文记录 `doctidex-git` v2.x.x 当前已经确认的总体设计及其子需求。命令契约、工作模型、
事务、校验和修复规则分别由下列子需求展开。

## 1. 需求意图

需要设计一个可在 Git 环境中工作的 `doctidex-git` 命令行工具，使其能够以明确、可脚本化
且与 [doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md) 一致的方式
处理 doctidex 目录树。

## 2. 已确认的范围事实

- 工具名称为 `doctidex-git`。
- 目标版本属于 `v2.x.x` 开发线；具体主、次、补丁版本策略尚未确定。
- 工具当前设计的运行范围为 Linux 和 macOS，并以 Git root 作为仓库级工作模型边界。
- 工具应与 doctidex v2 目录树外观 Architecture 配套使用，而不是定义另一套目录树身份规则。
- CLI 使用通用 `--repos-path` 指定 Git root，省略时从当前路径向上搜索。
- 当前确认的命令簇为 `init`、`boundary-set`、`import`、`worktree`、`validate` 和 `repair`。
- 命令返回机器可读的 JSON 结构；普通命令使用统一成功/错误结构，`validate` 使用
  `valid`、`diagnostics` 和结构化命令错误的分离结果。
- 工作模型由 Git root 的 `index.md` 基础 frontmatter、`CacheStore`、`RuntimeStore`、Installation、Ref、
  Worktree 和 BoundaryPoint 组成；tracked 投影、事务恢复及派生边界规则分别由子需求定义。
- `repair` 以 JSON 描述为基准，使物理安装、引用、worktree、派生边界和 Git ignore 与模型相容；常规
  repair 不从历史恢复旧版本，但处理残留 RuntimeStore journal 时可使用其 backup 收敛混合发布的 JSON。
- 本次需求包含代码库开发；代码开发完成后还必须完成配套 Architecture 文档的撰写。
- 本次需求暂不撰写 user 文档；人类维护者、agent 和自动化程序的差异仅在后续 user 文档中用于
  调整内容组织。

### 并发与外部修改边界

- 并发与 race 设计只覆盖遵守本架构的 `doctidex-git` CLI 命令之间对同一 Store 或工作模型的
  操作；仅同时持有两个 Store 的命令按 `GitCache -> RuntimeStore` 的既定锁顺序协调。普通 RuntimeStore
  事务发现残留 journal 后释放自身锁并报告 `repair-required`，由命令协调器按需运行 repair 后重试对应操作。
- 不对用户、编辑器或其他非 `doctidex-git` 程序直接修改状态文件或物理目录所形成的 race 提供
  防御性保证，也不以提交前 snapshot hash 对比等局部检查伪装为能够解决此类问题。
- 最终交付的 Architecture 文档必须将这一并发保证边界作为设计约束明确说明。

### 删除幂等性

- 删除命令请求的可删除模型记录不存在时，命令成功完成且不修改 Store 或物理状态。
- 此规则不适用于记录存在但由其他模型管理、因而当前命令无权删除的对象；此类操作继续返回其对应的
  受管对象错误。
- 最终交付的 Architecture 文档必须将删除命令的这一幂等性约束作为设计规则明确说明。

### Python 代码库组织

- Python 源代码位于 `src/python/whero/doctidex/`。
- Python 项目配置文件位于 `src/python/pyproject.toml`。
- Python 包的 import 路径前缀为 `whero.doctidex`。
- `whero` 是共享的顶级 package name，其他仓库也维护以 `whero` 为顶级 package name 的
  Python 库；本项目不得改用其他顶级 import 前缀或将 `whero` 视为本项目独占的顶级 package。

### 跨命令簇领域工具要求

`BoundaryPoint`、`Installation`、`Ref`、`Worktree`、仓库内路径和 Markdown link 的关系属于
doctidex-git 工作模型的共同概念，不能由单个命令簇各自解释或维护。实现必须在
`whero.doctidex` 内提供跨命令簇复用的内部领域工具，使 `import`、`validate`、`repair` 及后续需要
这些关系的命令使用同一套语义。

- 共享工具必须从完整 `RuntimeState` 视图浏览和关联 Installation、Ref、Worktree 与派生
  BoundaryPoint，包括按 install-id、install-path、Ref target-dir 及其关系定位模型对象。
- 对多个路径或扫描结果查询 BoundaryPoint 的共享工具，必须提供保序批量接口，并在这类批量流程中
  基于同一份当前模型视图快照完成查询，避免在循环中反复派生完整 boundary-set。单路径查询仍可作为
  调用方只处理一个路径时的便利接口；事务状态更新或建立新的模型视图后，查询自然使用其新的当前快照。
- 共享工具必须按完整 BoundaryPoint 视图枚举当前 doctidex 目录树范围内的 Markdown 文件，不进入任何
  BoundaryPoint 后代或 `/.doctidex-git`；并统一解析本地 link 的仓库内部目标、源文件行号和第一个
  跨越的 BoundaryPoint。
- `InlineAnnotation` 是附着于单个 Markdown link 的有效结构化注释模型，当前包含
  `cross_boundary_point`。共享工具必须公开一个接收 Markdown 源文本和字符位置的解析方法：从该位置
  开始仅考察紧邻的连续 HTML 注释序列，按源码顺序返回首个有效 `doctidex` YAML 映射对应的
  `InlineAnnotation`；无有效映射时返回空。该方法不读取文件、不决定诊断，也不判断字段值是否与某个
  BoundaryPoint 匹配。
- 共享工具还必须将 `InlineAnnotation.cross_boundary_point` 与 link 的原始 path 部分在同一相对或绝对
  路径坐标系中校验为完整路径段前缀，并按 link 所在文档规范化为仓库内部路径。`validate` 只将这一
  规范化结果与第一个跨越的 BoundaryPoint 比较；不得将原始注释字符串直接与仓库内部路径比较。
- Markdown link 的语法识别必须使用已显式声明的成熟 CommonMark 解析器，不得以正则表达式模拟 Markdown
  语法。阶段 4 选用 `markdown-it-py`；领域工具只补充解析器已识别 link 的源行定位、本地路径解释和模型
  关联，不另行定义 Markdown 语法。
- 共享工具必须能将第一个跨越的 `import` 或 `import-ref` BoundaryPoint 分别关联到 Installation，或
  经 Ref 关联到其 Installation。`import remove`、`import unref` 的删除阻塞、`validate` 的 link
  诊断和 `repair` 的受管理路径扫描均复用这一关联语义。
- 工具只负责模型浏览、目录扫描、link 解析和关系关联，不决定命令是否删除、报告诊断或创建物理对象；
  这些命令策略仍由各自工作流定义。具体 Python 模块、类或函数名称由实施确定，但不得继续在各命令
  模块中复制这些语义。

### Architecture 文档交付要求

- Architecture 文档在本次需求的代码库开发完成后撰写，作为实现完成后的独立交付物。
- 撰写时必须重新组织语言逻辑和文档结构，按照 Architecture 文档自身的组织要求表达内容，
  不直接复用或照搬本需求的子需求结构。
- 需要理清并解耦当前混合在各子需求中的定义、规则和概念描述，将分散在各子需求中的有效信息
  整合到 Architecture 文档中。
- 必须纳入本页“并发与外部修改边界”所定义的设计约束与保证范围。
- 本次需求不包含 user 文档撰写。

## 3. 与 Architecture 的已知依赖

`doctidex-git` 设计尊重以下已在 Architecture 中定义的约束；具体校验和跨界行为由需求
0002-03、0002-05 和 0002-07 展开：

- 候选 doctidex 根目录必须直接包含 `index.md`。
- 根 `index.md` 的基础 frontmatter 必须包含 `type: index`、`doctidex.type: index` 和
  `doctidex.root: true`，且字段类型和值必须匹配。
- 当前目录树范围内的 `index.md` 可以按需出现在任意位置，不要求祖先路径连续包含
  `index.md`。
- `index.md` 正文承担渐进式披露、导航和查询入口职责，但没有固定组织格式。
- `boundary-set` 是当前目录树的 escape 节点抽象集合；越过节点后，当前树的
  `index.md`、link 和其他结构规则不再适用，且 v2 不在 frontmatter 中规定其字段或声明格式。
- 当前规则有效范围内的 Markdown 文档可使用 Markdown link；以 `/` 开头的路径从当前
  doctidex 根解释，并鼓励使用相对路径。
- 结构化 link 注释使用 link 后连续 HTML 注释中的 `doctidex` YAML 映射，并支持
  `cross-boundary-point` 字段。

任何需要改变这些模型、字段、边界或语义的方案，都必须先说明对 Architecture 的影响，
并在获得授权后更新对应 Architecture 文档。

## 4. 受影响的产品表面

| 表面 | 预期影响 | 当前状态 |
|---|---|---|
| CLI 命令树 | 定义六个命令簇、子命令、参数、返回结构和退出状态 | 由需求 0002-01 定义 |
| Git 集成 | 定义 Git root、revision、cache、安装仓库和 worktree 的交互 | 由需求 0002-02、05、06、08 定义 |
| doctidex 目录树识别 | 使用 Architecture 规定的根入口、frontmatter 和边界语义 | 约束已知，由需求 0002-03、07 落实 |
| 导航与追踪 | 通过 boundary-set、import-ref、worktree 和 Markdown link 提供稳定定位 | 由需求 0002-03、05、06、07 定义 |
| 校验与诊断 | 报告根入口、目录树、link、工作模型和 worktree 状态问题 | 由需求 0002-07 定义 |
| 输出接口 | 提供统一 JSON 成功、错误和 validate 诊断结构 | 由需求 0002-01 定义 |
| Python 代码库组织 | 定义源码目录、项目配置文件位置和 Python import 包前缀 | 约束已确认 |
| 跨命令簇领域工具 | 统一工作模型关系、boundary-scoped 目录扫描和 Markdown link 跨界关联 | 约束已确认；由阶段 4 实现并供阶段 6 复用 |
| 文档与发布 | 代码开发完成后的 Architecture 文档；user 文档暂不撰写 | Architecture 文档为本次需求后续交付物 |

## 5. 设计决策记录

当前已确认的总体设计决策如下；各项细节以对应子需求为准：

- CLI 采用六个命令簇，并为每个命令使用通用 `--repos-path`。
- 工作模型以 tracked 状态投影和 `runtime.json` 共同提供权威数据，边界点按来源模型派生。
- CacheStore 使用带 `preparing`/`published` 状态恢复的单文件原子更新，RuntimeStore 使用带
  journal 的多文件可恢复事务；两者都不是数据库事务。
- 并发控制只处理遵守协议的 `doctidex-git` CLI 命令；不为外部直接修改提供不完整的 race 防御。
- 除 `validate`、`init` 外，普通 RuntimeStore 事务在准备阶段只检测残留 journal，释放锁并报告内部
  `repair-required` 信号。命令协调器在 RuntimeStore 外部运行 repair，再重试触发该信号的 RuntimeStore
  操作，最多三次。repair 在与 validate 相同的诊断锁定访问内负责 journal 的分类、必要 JSON 收敛、物理修复
  和最终清理；仅已确认 `committed` 的残留可跳过物理修复，但所有残留 journal 统一在本次 repair 的全部修复
  完成后清理。
- 工作模型关系、boundary-scoped 目录扫描和本地 link 的跨界关联由共享领域工具统一解释；命令簇仅在
  此基础上定义各自的修改、校验或修复策略。
- 删除命令对不存在的可删除模型记录保持幂等；对仍受其他模型管理的对象保留明确的禁止删除语义。
- Python 代码库按本页第 2 节的 `src/python/whero/doctidex` 布局组织。
- 代码开发完成后，按本页第 2 节的 Architecture 文档交付要求完成独立 Architecture 文档。
- 当前不额外定义 v2.x.x 的版本兼容或向后兼容承诺。

后续决策应在主题子需求中记录内容、理由、影响面和确认日期，并从本页保持可导航关系。

## 6. 依赖与相关记录

- 上游 Architecture：[doctidex v2 目录树外观规范](../../architecture/doctidex-v2-directory-tree.md)。
- 子需求：[CLI 命令行参数及返回结果结构设计](01-cli-arguments-results.md)。
- 子需求：[设计 doctidex-git 工作模型](02-working-model.md)。
- 子需求：[`boundary-set` 命令簇工作流与生命周期设计](03-boundary-set.md)。
- 子需求：[`init` 命令簇工作流与生命周期设计](04-init.md)。
- 子需求：[`import` 命令簇工作流与生命周期设计](05-import.md)。
- 子需求：[`worktree` 命令簇工作流与生命周期设计](06-worktree.md)。
- 子需求：[`validate` 命令簇工作流与校验设计](07-validate.md)。
- 子需求：[`CacheStore` 与 `RuntimeStore` 事务机制实现设计要求](08-store-transactions.md)。
- 子需求：[`repair` 命令簇工作流与生命周期设计](09-repair.md)。
- 当前没有已确认的 Issue、实现记录或其他 Requirement 依赖。

父需求已进入 `planned` 阶段；各子需求当前状态如下。子需求仍作为设计依据维护，未单独授权实现：

| 子需求 | 状态 |
|---|---|
| 0002-01 CLI 参数及返回结果 | `draft` |
| 0002-02 工作模型 | `draft` |
| 0002-03 `boundary-set` | `draft` |
| 0002-04 `init` | `draft` |
| 0002-05 `import` | `draft` |
| 0002-06 `worktree` | `draft` |
| 0002-07 `validate` | `draft` |
| 0002-08 Store 事务 | `draft` |
| 0002-09 `repair` | `draft` |

后续新增的协议、解析器、仓库结构、发布流程或 Issue 记录，应在相关文档中补充双向链接；
当前没有可补充的已确认记录。

## 7. 验收标准

以下标准用于完成本 Requirement 的定义，不代表当前已满足：

- [ ] 产品目标、适用范围、首要 Git 工作流和非目标已明确；角色优先级不作为本需求前置条件。
- [ ] 支持的 Git 环境、仓库范围、工作区状态、提交/分支/远程语义已明确。
- [ ] 命令树、参数、配置来源、输出格式、退出码和机器接口已明确。
- [ ] doctidex v2 根识别、frontmatter 校验、任意位置 `index.md`、`boundary-set` 和 link
      语义与 Architecture 一致，并有冲突处理方案。
- [ ] 读操作、写操作、暂存区/工作树影响和幂等性已明确。
- [ ] 错误分类、诊断信息、权限与安全边界和性能目标已明确；本次需求不额外定义版本兼容承诺。
- [ ] 每项关键行为都有可执行的验收场景和测试证据要求。
- [x] Architecture 文档作为代码库开发完成后的独立交付物，其重组、解耦和信息整合要求已明确；
      本次需求暂不撰写 user 文档。
- [x] 分阶段实施计划、每阶段具体输出、验证/审阅检查点和 Architecture 后置交付已记录。
- [ ] 需求、Architecture、Issue、实现和测试之间的链接已校验。

## 8. 实施计划

本计划记录父需求从代码库开发到 Architecture 文档交付的分阶段范围。每个阶段均应独立完成并
通过检查点后再进入下一阶段；`planned` 只表示计划已记录，不授权直接修改实现代码、测试、
Architecture 或 Skills。实施前仍需取得明确的实现授权。

### 8.1 分阶段实施原则

- 每个阶段只实现已由本需求及其子需求确定的行为。不能由当前阶段独立确定、且与后续命令工作流
  或诊断模型强耦合的细节，必须在代码中保留可见的最小占位，并在本节说明由哪个后续阶段决定。
- 阶段建立的基础设施可以被后续阶段复用，但不得预先以部分校验、临时错误语义或物理修复行为
  固化后续阶段的公开契约。
- 需要作出实现选择时，必须记录选择、未选择的方案和后续复核点；不得将其分散为没有来源说明的
  helper 或测试假设。

| 阶段 | 状态 | 范围与具体输出 | 验证与审阅检查点 |
|---|---|---|---|
| 1. Python 工程与 CLI 基础 | `completed` | 在 `src/python/whero/doctidex/` 建立 Python 包，在 `src/python/pyproject.toml` 建立项目配置；实现 CLI 入口、通用 `--repos-path`、六个命令簇的分发和基础参数错误/返回结构。依据 [需求 0002-01](01-cli-arguments-results.md) 固化公共 CLI 契约。 | 已验证项目可编辑安装、`whero.doctidex` 可导入和 `doctidex-git` 入口；已为命令分发、通用参数、JSON 成功/错误结构建立自动化检查，并完成与 01 的一致性审阅。 |
| 2. 工作模型、RuntimeStore 与初始化 | `completed` | 实现已确定的领域记录、tracked/runtime 投影、RuntimeStore 锁、journal、恢复骨架和并发保护。RuntimeStore 明确区分只读事务和写事务：只读事务不创建 journal，写事务在进入上下文后立即登记 journal。`init` 在工作空间不存在或为空时创建完整初始状态、根 `index.md` 的基础 frontmatter 和 Git ignore 规则；非空工作空间只返回已运行过初始化并建议执行 `validate --model-structure` 的信息，不执行专用结构校验。CacheStore/GitCache 不属于本阶段的有效实现范围；阶段 2 中遗留的旧 CacheStore 事务实现由新的 phase 3 取代。 | 已通过自动化测试验证状态文件重建、tracked/untracked 投影、RuntimeStore 事务提交/回滚/遗留恢复、读写事务边界、全新及空工作空间初始化、根入口创建与补充、frontmatter 冲突、非空工作空间提示和已有工作空间不被修改；Ruff、`pip check` 和 CLI 入口检查通过。CacheStore/GitCache 协议、既有工作空间的完整 validate、按 journal 状态与目标 hash 区分恢复结果、待恢复事务诊断、残留事务后的内部 repair、跨 Store 协调和物理目录补偿按后续阶段实施。 |
| 3. CacheStore 与 GitCache | `completed` | 已依据 [需求 0002-08](08-store-transactions.md) 重新实现 CacheStore 与 GitCache：CacheItem 的 `preparing`/`published` 状态、CacheStore 的 ReadOnly/Write 事务和立即生效的 `replace_records`、事务进入时的 `preparing` 清理，以及 GitCache 对外的 ReadOnly/Write 事务和 Write `load`。所有缓存访问改经 GitCache 事务；本阶段不实现 revision 选择、fetch 或 Git worktree 操作，也未恢复 boundary-set 或 import 命令工作流。 | 已验证同 URL 的唯一记录、可用 published cache 的复用、load 的 preparing 到 published 转换、clone 失败后的下一次事务清理、ReadOnly 接口限制、立即状态发布、路径清理范围和 bare Git object 残留边界；30 个自动化测试、Ruff、`pip check` 和 `git diff --check` 通过。跨 Store 的命令级协调和 repair 工作流由 phase 6 统一实施。 |
| 4. boundary-set 与 import | `completed` | 已实现 custom/派生边界点、路径解析、`boundary-set add/remove/parse`、完整 import 工作流和共享领域工具。`import install` 以 branch、tag、commit 三选一的 revision selector 执行：branch/tag 同步远程后，当前 commit 不变时 no-op，变化时替换 Installation；commit 命中同一 Git URL 与 commit hash 时 no-op，未命中时获取并安装。`restore` 严格使用记录的 commit hash；Installation 不再持久化 `is-auto-resolved-hash`；install-path 由 Git URL 和 selector 值语义化派生。revision 更新保留既有受管理 Ref 关系并维持其 Installation 的 tracked 约束。跨 Store 协调遵守 `GitCache -> RuntimeStore`，残留恢复由后续 phase 6 的 repair 工作流统一处理。 | 已验证 custom/派生边界、批量 boundary 查询、tracked/untracked 投影、track、受管 ref/unref、query、安装移除阻塞、Markdown link 行号、View 与共享领域工具；另验证互斥 selector 参数、branch/tag 最新 commit 的 no-op 与替换、commit 命中复用、仅按记录 commit restore、语义化 install-path（包含 branch `/` 层级）、`is-auto-resolved-hash` 移除及 revision 更新后的 Ref 关系。55 个自动化测试、Ruff、`pip check` 和 `git diff --check` 通过。 |
| 5. worktree | `completed` | 已按 [需求 0002-06](06-worktree.md) 重新实现 `worktree create/remove/query`。URL 来源使用 branch、tag、commit 三选一，在 GitCache 事务内解析创建时的 base commit；Worktree 在 `runtime.json` 持久化 `base-commit-hash`，不跟踪后续 `HEAD`。默认 work-path 使用 `/.doctidex-git/worktrees/<domain>/<repository-path-without-.git>/<tree-name>`，支持仅用于默认路径的 `--tree-name` 和短随机末级名称；随机名称发生模型或物理路径冲突时重试。Installation 来源、BoundaryPoint、Git ignore、移除和 `GitCache -> RuntimeStore` 协调保持有效。 | 已验证 URL 三种 selector、base commit 持久化及 worktree 后续提交不改变它、URL 层级默认路径、嵌套 tree-name 和短随机名称及其冲突重试，以及 Installation 来源、移除、边界、ignore、路径占用、缺失清理和事务顺序。70 个自动化测试、Ruff、`pip check` 和 `git diff --check` 通过。 |
| 5.1 Git worktree 目标 commit 可用性补充 | `completed` | 已在共享 Git repository 操作中实现目标 commit 的 `cat-file` 检查、按 hash fetch 和复验；`import install`、`import restore` 与 `worktree create` 的 URL/Installation 两类来源均在创建或切换 Git worktree 前接入该流程。GitCache 继续只负责 transaction 与 bare repository 获取，不接管 revision fetch。 | 已验证已发布 bare repository 缺少目标 commit 时的 restore、Installation 来源 Worktree 创建和 URL 来源创建；验证命中时不重复 fetch、已记录 commit 不重新解析 selector、远程无法提供 commit 时使用命令簇既有来源/恢复诊断，以及所有 Git 操作保持在 GitCache transaction 内。81 个自动化测试、Ruff、`pip check` 和 `git diff --check` 通过。 |
| 6. repair、validate 与跨 Store 协调 | `completed` | 已按更新后的 [需求 0002-07](07-validate.md)、[需求 0002-08](08-store-transactions.md) 和 [需求 0002-09](09-repair.md) 重新实现恢复协调：RuntimeStore 仅报告 `repair-required`；`StoreCoordinator` 在 RuntimeStore 外部执行 repair 并重试实际操作，最多三次。repair 核心复用调用方已有的 GitCache Write 事务；ReadOnly 事务退出后才打开 Write。工作流通过独立的 `WorkflowCoordinator` 协议依赖协调能力，避免与 repair 的依赖环；显式 `validate` 保持只读诊断。 | 已验证 RuntimeStore 不含跨 Store 回调或空预检、已有 GitCache Write 事务的 repair 复用、GitCache ReadOnly 退出后再以 Write repair、纯 RuntimeStore 命令不预先打开 GitCache、三次重试与最终 transaction ID、import/worktree 重试中的 revision 固定，以及 validate/repair 物理修复场景。 |
| 7. 集成验收与 Architecture 交付 | `pending` | 完成各命令簇端到端集成、回归验证和需求验收证据；在代码库开发完成后，依据 Architecture 文档自身的组织要求重新撰写并整合 Architecture 文档。此阶段不撰写 user 文档。 | 运行完整自动化测试和跨阶段场景检查，校验需求、Architecture 与实现的链接及术语一致性；完成 Architecture 文档审阅后，才可将父需求转为 `implemented`。 |

阶段 4 的 install-path 补充实施记录：

- `import install` 和 `import restore` 以同一个内部流程检查 install-path 是否为该路径自身的 Git
  worktree，避免将仓库内普通目录误识别为 Git 控制路径。该流程只处理物理安装目录；Installation 的
  selector、tracked 状态、install-id 和 Ref 关系仍按原有工作流决定。
- 同源、干净且 detached 的既有 worktree 在原目录中 checkout 到目标 commit。非 Git 残留目录以及不满足
  复用条件的同源 worktree 均删除后重新创建；Git URL 不同的 worktree 保留原状并终止命令。`restore`
  将无法完成该路径准备的 Installation 目标错误转换为其既有的 `installation.restore.unavailable` 诊断。
- 本次补充新增非 Git 残留、同源复用、dirty 重建和异源拒绝的自动化测试。完整回归 `pytest` 为
  76 passed，`ruff check .`、`pip check` 和 `git diff --check` 通过。

阶段 5.1 的目标 commit 可用性实施记录：

- `repository.py` 在不重新选择 revision 的前提下，先以 `git cat-file -e <hash>^{commit}` 检查 bare
  repository；仅缺失时执行按 hash 的 `git fetch origin <hash>`，并在 fetch 后复验。该操作在调用方
  已持有的 GitCache transaction 内执行，未将 revision fetch 纳入 GitCache 的公开接口。
- `import restore` 使用 Installation 当前记录的 commit；`worktree create --install-id` 同样严格使用
  Installation commit。两者缺失时均可补齐 bare repository object，但远程无法提供时分别返回
  `installation.restore.unavailable` 和 `worktree.source.unavailable`。`import install` 与 URL 来源
  Worktree 创建在 selector 解析后复验目标 commit，保留其 `revision.unresolvable` 语义。
- 新增缺失 commit 的 restore/Worktree 创建、远程不可用错误转换及已命中 commit 不重复 fetch 覆盖。
  完整回归 `pytest` 为 81 passed，`ruff check .`、`pip check` 和 `git diff --check` 通过。

阶段 6 的重新实施记录：

- 显式 `validate` 使用只获取 RuntimeStore 锁的诊断读取事务；不恢复、修复、创建或清理 journal，
  发现 `prepared`/`publishing` 残留时只返回 `transaction.recovery.required` 并跳过后续内容扫描。
- 普通 RuntimeStore 事务只检测残留 journal。检测到后释放锁并报告内部 `repair-required`；它不持有
  recovery handler，不获取 GitCache，也不在 `__enter__()` 中运行 repair 或重试。
- `StoreCoordinator` 围绕实际 RuntimeStore 操作闭包处理该信号：已有 GitCache Write 事务时直接复用，当前
  为 GitCache ReadOnly 事务时先退出再新开 Write，尚未访问缓存时仅在需要 repair 时新开 GitCache Write
  事务；repair 成功后重试闭包，最多 3 次。未使用空的普通 RuntimeStore 事务预检。
- repair 核心在调用方提供的 GitCache Write 事务及 RuntimeStore 诊断锁内完成 journal 分类、必要的 backup
  JSON 收敛、Installation/Ref/Worktree/BoundaryPoint/Git ignore 物理修复和最终清理；显式 `repair` 自行打开
  GitCache Write 事务。repair 不调用或消费 `validate` 诊断，Markdown link 不属于 repair 范围。
- `import install` 和 URL 来源 `worktree create` 在当前 GitCache 事务内只解析一次 branch/tag 的目标 commit
  hash；repair 后的闭包重试复用该 hash。`.command.lock` 覆盖检测、repair 和重试全过程；外部修改 race 仍不在
  设计防御范围内。
- `WorkflowCoordinator` 协议承载 import/worktree 所需的重试和缓存访问能力；具体 `StoreCoordinator` 依赖
  repair 核心。该接口边界消除了协调器、repair 与命令工作流之间的导入环，而不将 repair 责任下沉到命令簇。
- 87 项自动化测试、`ruff check .`、`pip check` 和 `git diff --check` 已通过。Architecture 和 user 文档仍由
  phase 7 负责。
- 命令入口中 `boundary-set`、`import`、`worktree`、`validate` 和 `repair` 的 Git root 解析、领域异常转换、
  JSON 输出及默认错误退出码通过内部装饰器统一；各命令函数只保留自身工作流和成功结果构造。`validate` 显式
  提供其 `valid: false` 的退出码策略，`init` 因初始化专属错误与既有工作模型校验语义保持独立。此项不改变
  命令参数、JSON 结构或退出码契约。
- `validate` 提供完整的显式只读校验，以及校验 RuntimeStore 工作模型结构和根入口基础 frontmatter 的可选
  `--model-structure` 模式；该模式不提供独立的校验 API。非空工作空间的 `init` 不调用 `validate`，
  仅返回已运行过初始化并建议执行 `validate --model-structure` 的信息。
- 跨界 link 的结构化注释按每个 link 的精确源码结束位置提取其紧邻连续 HTML 注释块序列；序列中的普通
  注释不影响关联，读取方按源码顺序采用首个合规的 `doctidex` 映射。该规则支持相邻注释块及同一行多个
  link，且不要求 `doctidex` 注释块位于序列首位。
- `cross-boundary-point` 保持 link path 的相对或绝对形式。实现先验证其为 link 目标 path 的完整路径段
  前缀，再按源文档规范化后与实际第一个 BoundaryPoint 比较；相对 link 不得以语义相同但字面不为其前缀的
  绝对注释替代。

阶段 5 的重新实施记录：

- 先前的 phase 5 实现将 URL 来源固定到 bare repository 的 `HEAD`，默认路径使用
  `/.doctidex-git/worktrees/<uuid>`，且 Worktree 未持久化 base commit。这些行为与更新后的
  [需求 0002-06](06-worktree.md) 不一致，原实现及其测试结果不再构成阶段完成证据。
- 已保留 Installation 来源的既有 commit 语义，并为 URL 来源实现 branch、tag、commit selector 的
  解析、base commit 持久化及 URL 层级默认路径。自定义 `work-path` 的工具管理 Git ignore 成对规则
  保持不变并已重新验证。revision 解析与 Git URL 的位置解释抽取为共享仓库工具，以保证 import 与
  worktree 采用一致的来源解释。
- 未提供 `--tree-name` 时，随机默认末级目录在 RuntimeStore 写事务内确认其未被模型或物理路径占用；
  发生冲突即重新生成，直至可用。显式 `--work-path` 或 `--tree-name` 保持原有的冲突即报错语义。

阶段 2 的实现选择与延后事项：

- 状态文件直接使用需求 0002-02 所列集合的最小 JSON 表示：`boundary-set.json`、`imports.json`
  和 `import-refs.json` 为数组，`runtime.json` 使用已明确的 `imports` 与 `worktrees` 对象字段。
  未引入额外的版本包装、索引或领域关系校验；这些包装和校验没有已确认的需求依据。阶段 4 的
  命令工作流可复用该投影，阶段 6 负责工作模型的完整有效性诊断。
- `init` 对非空工作空间的已初始化提示、空工作空间继续初始化和不执行隐式校验的语义由当前
  `validate` 设计确定；非空工作空间的提示指向 `validate --model-structure`。
- CacheStore/GitCache 与 bare Git repository 的恢复、GitCache/RuntimeStore 的命令级锁协调，以及
  install/worktree 物理目录的补偿属于阶段 3 及之后命令工作流的责任。阶段 2 仅保证 RuntimeStore
  状态 JSON 的事务语义；旧 CacheStore 实现不作为新阶段的设计或验收依据。
- RuntimeStore 按需求 0002-08 使用工作空间内的 `.lock` 文件；该内部锁文件随其他运行时工件
  加入 Git ignore，不作为工作模型记录。普通只读/写事务在 `__enter__()` 仅检查残留 journal；发现残留
  时释放锁并报告 `repair-required`。阶段 6 的命令协调器负责 repair 与操作重试；无残留后，写事务才创建
  `.transactions/<transaction-id>/` 及初始 journal，使其自身中断时下一次命令能够感知遗留事务。后续阶段
  若统一工作空间保护规则，需复核其 ignore 表达，但不改变锁路径契约。
- 阶段 2 仅建立 journal 的持久化、目标 hash 观察和基础状态文件事务骨架；残留 journal 的状态分类、
  backup JSON 收敛、物理 repair、最终清理和普通事务报告 `repair-required` 后的协调重试明确留待阶段 6 实现。
  该留白不改变阶段 2 已验证的事务目录、暂存、备份和基础事务机制。
- Store 的并发控制只处理遵守锁和事务协议的 doctidex-git CLI 命令；不对外部直接修改增加
  snapshot hash 对比等不完整的 race 防御。该保证边界将在最终 Architecture 文档中继续保留。
- `init` 的新工作空间文件先在系统临时目录直接写入，完成后一次性同步到 Git root；不在 Git root
  创建初始化临时目录，也不把初始化过程纳入 RuntimeStore journal。该选择适用于不存在或为空的
  工作空间；非空工作空间由 `init` 返回已初始化提示，用户可另行执行 `validate`。

已作废的旧阶段 3 实施记录：

- 先前以 `boundary-set` 与 `import` 为范围的 phase 3 已被本计划明确作废；其代码、测试结果和
  实现选择不再构成需求 0002 的已完成实施成果，也不得作为后续阶段的依赖或验收证据。
- 作废原因是其 CacheStore/Git cache 实现不符合 [需求 0002-08](08-store-transactions.md) 现已确认的
  `preparing`/`published` 状态、CacheStore ReadOnly/Write 事务、立即 `replace_records`、事务进入时
  清理，以及 GitCache 对外事务封装要求。
- 新 phase 3 完成并通过审阅前，不得恢复或扩展旧 phase 3 的 boundary-set/import 实现；相关命令簇
  将在新的 phase 4 基于已完成的 GitCache 协议重新实现。

新阶段 3 的实施约束：

- 只实现 0002-08 第 4 节的 CacheStore/GitCache 协议及其直接测试；不新增或恢复任何 import、
  boundary-set、worktree、repair、validate 的业务工作流。
- `preparing` 记录的清理仅针对 CacheStore 内部生成、并且已验证位于 `cache-path` 下的 repository
  路径；不把外部输入或 RuntimeStore 数据作为缓存清理目标。
- 该阶段通过 GitCache 作为唯一缓存访问入口建立与 RuntimeStore 的固定锁顺序，但不提前确定
  Installation、Ref 或 Worktree 的物理目录补偿细节；这些细节仍由 phase 4 至 6 的命令工作流决定。

阶段 3 的实现选择与延后事项：

- CacheStore 在 ReadOnly/Write 事务进入时都会持有缓存锁、读取 `status.json` 并清理其中的
  `preparing` 记录及其受控 repository 路径。该恢复步骤会立即发布清理后的记录集合；ReadOnly
  不对调用方公开记录替换能力，Write 的 `replace_records` 每次调用即时原子发布。
- GitCache 是外部模块访问 bare repository 的唯一入口。ReadOnly 只能寻找已发布且可用的 repository；
  Write 的 `load` 在 clone 前立即登记 `preparing`，成功后改为 `published`。失败或中断时保留
  `preparing`，由下一次 CacheStore 事务清理并允许重新加载。
- `GitCache.with_repository` 统一先在 ReadOnly 事务中查询；查询未命中时退出 ReadOnly 事务，再重新
  打开 Write 事务调用 `load`，不得在只读事务内升级或嵌套写事务。调用方将依赖 repository 的
  工作流作为 callback 传入，使选定事务保持至 callback 结束。
- GitCache 的公开事务接口没有缓存 remove；phase 4 之后的命令只能删除自己的安装目录、引用或
  worktree，不能把命令移除扩展为 CacheStore 清理。
- GitCache 只管理缓存记录和 bare repository 的加载、获取；revision 解析、来源同步和安装 worktree
  由 phase 4 的 `import` 实现，用户 worktree 的创建与移除由 phase 5 实现。
- phase 3 不恢复已作废的 boundary-set/import 实现。RuntimeStore 与 GitCache 的命令级嵌套、
  Installation/Ref 的物理目录操作和跨 Store 补偿由 phase 4 重新实现时确定并验证。

## 9. 实施与状态

本记录目前为 `planned`。阶段 1 至 5 已完成并待审阅；阶段 4 已按重定位后的 revision selector
设计重新实现，阶段 5 已按更新后的 worktree revision 与默认路径设计重新实现并完成验证。阶段 6 至 7
尚未开始。作废记录、阶段 2 至 5 的实现选择与延后事项记录于第 8.1 节。未取得相应阶段的明确实现
授权前不得继续修改代码、测试或 Architecture 文档。
