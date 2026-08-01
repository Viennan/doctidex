# 子需求 0008.2：doctidex-git Python Details 与实现

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0008.2` |
| 状态 | `approved` |
| 日期 | 2026-07-30 |
| 批准日期 | 2026-08-01；用户明确批准大型 Requirement 0008 及其全部子需求 |
| 修订日期 | 2026-07-31 |
| 来源 | 用户要求将 doctidex-git 的 Architecture 设计与 Details 实现拆分；Architecture 完成后，结合其最终契约补全 Python 实现需求，只保留仍需讨论的实现边界；后续要求实现严格遵循 Architecture，不得产生偏离，并确认 package version、目标平台与 bare object cache 方向 |
| 所属大型 Requirement | [DX-REQ-0008](overview.md) |
| 设计依赖 | [DX-REQ-0008.1：Architecture 设计](01-doctidex-git-alignment.md) |
| 协议基线 | [`doctidex` `v1.0.0`](../../../spec/overview.md) |
| 设计输入 | [doctidex-git `v1.0.0` Architecture](../../doctidex-git/architecture/index.md) |
| 实现起点 | doctidex-git `0.1.0` Python package、旧 CLI、测试与[归档 Python Details](../../doctidex-git/archive/v0.1.0/details/python/index.md) |
| 实现说明 | [doctidex-git `v1.0.0` Details](../../doctidex-git/details/index.md) |
| 影响范围 | `impls/libs/python/`、doctidex-git plugin packaging、Published Skills、Python Details、测试和发布验证 |
| 兼容性 | 不兼容重构；不实现 `0.1.0` 状态迁移、旧命令兼容或双版本模式 |

本文把已经完成的语言无关设计转化为 Python 实现需求。它保存实现边界、代码影响、实施
顺序、完成证据和验收门槛，不替代当前 Details，也不重复 Architecture 的 public CLI/JSON
契约。Python 代码、测试、Details、Published Skills 与 CI 已完成一致性切换，本记录据此
进入 `implemented`；是否可提交 PR/MR 仍待用户明确批准。

## 1. 实现意图与起点差异

Python 参考实现必须实现协议 `v1.0.0` validation、可选的 external install/link/restore/
link-parse 工作流，以及可选的受管 worktree 生命周期，同时删除旧 mount、filter、projection
和 maintenance scope surface。CLI `--json` 是唯一稳定的程序集成面；Python import、内部
records、storage path、锁和 Git plumbing 不承诺公共兼容性。

实施开始时的 `0.1.0` 代码不是可逐项保留的半成品：

- `cli.main` 发布 `context`、`inspect`、`resolve`、`init`、`changes`、`check`、`mount`
  与 `maintenance`，尚无目标命令；
- `protocol` 解释 mount 与旧 filter 字段，尚无最近负责制、三个局部配置、结构化 link 注释、
  完整可达性和 scoped validation；
- Git 层围绕 source cache、revision projection、mount presentation 与旧 maintenance root
  组织；这些职责不能直接成为新 external/worktree 的模块边界；
- 当时的测试主要证明 `0.1.0` 行为，不能作为新 surface 的兼容要求。

可以复用经过重新验证的 Markdown/YAML round-trip、Git subprocess、bare object reuse 和
Git worktree 基础能力，但不能仅因已有类型或模块存在而保留其 API。external/worktree
仍只是 agent 可主动选择的受管方案；实现不得把管理记录变成阅读、维护或协议 validation
的前置条件，也不得限制原生 Git、手工 worktree、submodule、symlink 或其他工具。

## 2. Architecture 已确定的实现输入

以下问题已由 [DX-REQ-0008.1](01-doctidex-git-alignment.md) 和对应 Architecture 确定，
不再留给 Python Details 改写。

### 2.1 严格符合 Architecture

[doctidex-git `v1.0.0` Architecture](../../doctidex-git/architecture/index.md) 是本次 Python
实现的完整目标产品契约。实现必须逐项落实其中的用户界面、工作流、CLI、JSON schema、
领域模型、子系统生命周期、跨工作流约束、Skill 系统和程序集成要求；Requirement 只保存
来源、实现影响与完成门槛，不能被用来降低或替换 Architecture 中更精确的规定。

“严格实现”至少包含以下约束：

1. 不得新增、删除、重命名或兼容性保留 Architecture 未授权的 public command、subcommand、
   argument、field、enum、failure code、exit code 或 Skill workflow。
2. 不得改变输入约束、省略/default、root/path/source 选择、network/read/write、
   dry-run/apply、pagination、幂等、部分成功、恢复、close 或人工升级语义；更严格或更宽松
   的实现同样属于偏离。
3. 不得以“实现简化”“沿用旧代码”“平台方便”或内部 storage 限制为由，添加 fallback、
   自动推断、隐式迁移、隐式 replace、递归安装、自动 Git 交付或其他 Architecture 已排除的
   行为。
4. Python 可以选择的只有 Architecture 明确留给 Details 的模块/类型划分、内部子路径、
   serialization、canonicalization algorithm、lock primitive、atomic publication 和 cleanup
   机制；这些选择不得改变任何可观察字段、路径语义、状态、顺序保证或下一步决定。
5. 本文的 ownership、状态和算法要求若与 Architecture 存在文字或语义冲突，以
   Architecture 为准，并必须先修正本文；不得选择较易实现的一侧继续编码。
6. 第 6 节决定与未决问题只能处理 Architecture 留白的 packaging、platform 和内部 object
   store 边界。若用户决定需要改变 public surface 或可观察生命周期，必须先重新打开
   DX-REQ-0008.1、更新并验证 Architecture，再同步本文，不能直接在 Python 中实现例外。

各 Architecture 页面与实现证据的对应关系如下；实现完成时不得有空白项：

| Architecture 权威 | Python/Details 必须提供的证据 |
|---|---|
| [用户接口](../../doctidex-git/architecture/user-surface.md) | 支持与不支持场景、受管工作流可选性和 public/internal 边界测试。 |
| [用户工作流](../../doctidex-git/architecture/workflows.md) | 每个步骤、可观察结果、失败后的下一决定及端到端场景测试。 |
| [CLI](../../doctidex-git/architecture/interfaces/cli.md) | parser invocation、参数/default、root selection、副作用与 network matrix 测试。 |
| [CLI JSON Schema](../../doctidex-git/architecture/interfaces/cli-schema.md) | required/null 字段、枚举、Finding、Collection、failure 和 exit code 契约测试。 |
| [领域模型](../../doctidex-git/architecture/domain-model.md) | 对应 Python types/records 的全部属性、不变量和可见性映射。 |
| [子系统与生命周期](../../doctidex-git/architecture/subsystems-and-lifecycles.md) | ownership、依赖方向、状态迁移、锁顺序、部分成功和中断恢复测试。 |
| [约束与失败](../../doctidex-git/architecture/constraints-and-failures.md) | 禁止行为、凭据清理、逻辑只读、有界输出、保留结果和人工升级测试。 |
| [Skill 系统](../../doctidex-git/architecture/skill-system.md) | 三 Skill 分工、无环阅读链、installed-product wording 和公开 artifact forward test。 |
| [程序集成](../../doctidex-git/architecture/interfaces/programmatic-integration.md) | JSON consumer、分页、幂等、兼容失败和无稳定 Python API 的集成测试。 |

若 Architecture 出现歧义、页面间矛盾、无法实现的要求，或实现需要一个未定义的用户可观察
决定，当前 implementation slice 必须停止：把差异定位到具体 Architecture 段落，在本
Requirement 中记录影响并取得用户决定，必要时先修订 DX-REQ-0008.1 与 Architecture。
禁止用代码、测试期望、Details 或 Published Skill 静默选择一种解释，再把该结果反写为
设计事实。

### 2.2 公共 surface 与兼容边界

- 目标命令仅为 `validate`、`external install/link/restore/link-parse` 和
  `worktree open/list/close`，以及不进入 Published Skills 的 `cache clean`；旧命令、参数、
  schema 与状态不保留兼容入口。
- parser 必须实现精确参数、互斥关系、省略行为、root/source/path 分类、dry-run/apply、
  bounded collection 和 exit code；renderer 必须输出单一 versioned JSON envelope。
- required 字段、null/default、枚举、Finding、Collection、failure code 与
  `requires_user` 以 [CLI JSON Schema](../../doctidex-git/architecture/interfaces/cli-schema.md)
  为唯一权威，Python 类型不得改变其语义。
- 受管 external/worktree 的位置与生命周期只约束 CLI 创建或登记的对象；未受管对象不会
  因缺少 registry 而成为 protocol finding 或普通 maintenance 失败。

### 2.3 协议解释与 validation

- parser、tree 和 validation 实现协议 `v1.0.0` 的 UTF-8/frontmatter、index/log 连续性、
  最近负责制、`boundary-set`、`atomic-indexing`、`unsafe`、可达性、根内 link、跨界判断、
  结构化 link 注释与保留名称。
- 删除 `doctidex.mounts`、`atomic_entries`、`excludes`、`protected`、旧 regex filter 和
  plugin-readiness 语义；validation 不读取 Git remote 或 doctidex-git registry。
- `--scope` 先词法规范化、排序、去重和移除祖先已覆盖的后代，再建立必要 support closure；
  scope 过滤发生在完整领域结果形成后，不能把 scoped pass 提升为全根结论。
- protocol findings 与 semantic candidates 分离；扫描、排序和 total 先完成，再应用输出
  budget。cursor 不能把不同 root 状态或 scope 集合的结果混合。

### 2.4 External 安装、链接与恢复

- install key 由 selected root、canonical source identity 与 normalized selector 组成；
  每个 key 有稳定 install ID/path，同 source 不同 selector 即使落到同 commit 也不能共用
  install path。
- install 与 CLI-created worktree 在 owner root 的 `/.doctidex` 下扁平发布，payload 由
  宿主 Git 精确 ignore；恢复清单和 external link 相对 symlink 保持可追踪，CLI 不 stage、
  commit 或运行 `git rm --cached`。
- source 省略 revision 时只在首次创建该 key 时发现 default branch；清单和 records 保存
  default branch provenance、commit selector 与 exact resolved commit，后续重试和 restore
  不重新解析 moving ref。
- direct install 进入版本化恢复清单；带 `--dependency-of` 的 dependency install 只保存
  root-owned runtime edge。命中既有 key 即截止环，dependency 可原地提升为 direct，direct
  不降级，宿主 repository 自依赖仍得到独立 fixed-commit install。
- link 从 direct install 或其 link 的任意 repository 子目录建立相对 symlink，保存
  repository-relative base，独立判断 boundary/unsafe；同 target/同 mapping 幂等，其他占用
  blocked，不提供 replace 或目录复制 fallback。
- restore 只消费 manifest 中 direct install 的 exact source/commit/path，重建载荷及必要
  mapping，不改写既有 symlink、frontmatter、manifest 或 Git index。

### 2.5 路径映射

- link-parse 接受可读目录或 symlink 自身，包括 broken symlink；命令离线、只读，不运行
  validation、不自动 install/restore，也不跟随 remote default branch。
- owner root 由最外层受管 presentation 决定；install 内容中的 doctidex root 只是
  content root，不能成为递归创建状态的 owner。
- current-owner mapping 优先于 installed-repository portable mapping。主仓库 durable link
  缺少 install 是 `owner_install_missing`；install 快照中的 portable dependency 尚未在
  owner root 展开是合法 `dependency_not_installed`；只有 records、manifest、symlink 和
  repository-relative facts 不能自洽时才是 `mapping_damaged`。
- 已存在匹配的外层 dependency install 时，解析器忽略 install 内仍 broken 的物理 target，
  从外层 install 组合 `working_path`。未受管路径返回 ok/unmanaged，不伪装成损坏。

### 2.6 Worktree 与维护现场

- source 分类顺序固定为 managed path、working tree/bare gitdir、gitfile、URL；submodule
  `.git` 文件必须按 gitfile 处理。
- open 要求显式 selector，每次创建新的 detached 可写 worktree；现场位于 selected root
  的 `/.doctidex`，不能嵌套到 install 或其他 worktree，不进入 external manifest。
- 当前宿主 working tree/current commit 可以直接维护。open 不自动复用，相同 source/base
  commit 只产生 warning 和 `reuse_candidate_count`。
- list 从 Git facts 重新判断 clean/changed/unavailable；close 只接受 exact managed path，
  只有归属可证明且 Git-clean 时才移除。dirty、unavailable、孤立或归属不明现场全部保留。
- worktree create 与 record publish 间中断留下可发现的孤立证据，不能靠猜测自动删除。

### 2.7 状态、并发和部分成功

- shared source store 位于专门的用户级 cache 中，按 canonical source identity 跨 doctidex
  root 复用，且只承载 bare Git repository/object database；不建立 revision checkout cache
  或 projection mirror。install checkout 由该 bare repository 直接以 Git worktree 物化到
  owner root 的目标 install path，不通过 hard link、symlink 或递归 projection 从 cache
  发布。install/worktree payload、portable manifest 与 runtime records 分层存放，不能混成
  一个不透明 cache。
- `cache clean` 只按调用方提供的 source URL 处理一个 bare source cache。它在 source lock
  内使用 Git worktree metadata 重新分类 linked worktrees：存在任何有效 worktree 时完整保留；
  没有有效 worktree 且其余登记全部被 Git 判为 prunable 时，dry-run 报告可清理，apply 才
  删除该 bare cache。命令不得删除 install/worktree path、manifest、runtime record 或其他
  source cache，也不得把文件系统路径缺失单独当作归属证明。
- 优先从 Git metadata、worktree list、manifest 和文件系统推导状态，只持久化无法可靠
  重建的 source/selector/commit、mapping、parent edge 和 managed ownership。
- 同一 canonical source 的 object/worktree mutation、同一 install key 的 role/parent
  mutation、同一 root 的 frontmatter/manifest/ignore/presentation mutation分别串行；取得
  source objects 后再进入 root mutation boundary，等待网络时不得持有 root 锁。
- dry-run 不写 root、持久 object store 或 registry；apply 重新验证计划。Git objects、
  frontmatter、ignore、manifest、payload、symlink 和 record 不构成总事务，失败结果必须
  报告已完成效果、保留状态和最小安全重试动作。

## 3. Python ownership 与依赖方向

最终文件名可在实现时按内聚性调整，但 Details 必须覆盖下列 ownership units；不得把两个
相反依赖方向合并为循环 service。

| Ownership unit | 目标责任 | 明确不负责 |
|---|---|---|
| 公共错误与结果模型 | 结构化 operation result、Finding、Collection、stable code、sanitization。 | CLI 文案决定领域事实，或携带 traceback/credentials。 |
| 文档与 Markdown 解析 | UTF-8、duplicate-key-safe YAML round-trip、CommonMark link 与连续 HTML 注释关联。 | Git、root 选择和 validation policy。 |
| 协议路径与树模型 | 根内词法路径、root/index/log 发现、最近负责配置、接管边界、可达图与 support closure。 | 解析 symlink 物理身份或 doctidex-git registry。 |
| Validation engine | 产生完整领域结果、scope 过滤、稳定排序、protocol/semantic 分域。 | 分页截断、Git readiness 或内容语义结论。 |
| Git runner 与 source provider | 非交互 Git 调用、locator 分类、credential sanitization、canonical identity、selector 解析、bare objects。 | doctidex frontmatter、presentation path 或用户 branch。 |
| Root/host Git coordinator | 唯一 host repository、精确 ignore、tracked-state 检查和 root mutation boundary。 | stage、commit、清理用户 tracked 内容。 |
| External coordinator | install identity、direct/dependency role、固定 commit、扁平 publication、幂等 install/restore。 | 递归读取依赖文档、自动 refresh 或 link prose。 |
| Manifest 与 runtime records | versioned portable direct/link facts，以及最小 install/link/worktree ownership records。 | 把 runtime state 当作协议事实，或在 manifest 保存主机绝对路径、凭据、lock。 |
| Mapping resolver | current-owner/portable mapping、owner/content root、suffix 与 target state 判定。 | network、validation、写入、自动依赖安装。 |
| Worktree coordinator | open/list/close、Git status、孤立证据发现和 exact ownership 检查。 | Git 交付、dirty cleanup、手工 worktree 生命周期。 |
| CLI parser/orchestrator/budgeter/renderer | argv、root selection、operation dispatch、cursor、JSON/human 输出和退出码。 | 重复实现协议、source、mapping 或 worktree 规则。 |

总体依赖保持 `cli -> protocol/git -> errors/results`，`protocol` 不依赖 Git，Git domain 不
依赖 CLI rendering。shared object provider 不依赖 doctidex root；external coordinator 才组合
source、root/host Git、manifest 和 protocol frontmatter。Published Skills 只能依赖已安装
CLI 的公开契约，不能读取这些内部模块或 records。

### 3.1 Package 与平台边界

- distribution 继续使用 `whero-doctidex`，本次不兼容重构完成时 package version 升级为
  `1.0.0`。package version、doctidex protocol `v1.0.0` 与 JSON `schema_version: "1.0"`
  分别表达，不因数值相近而互相替代。
- Python 参考实现必须支持 Linux、macOS 与 Windows。所有目标命令都属于该平台承诺；
  平台差异只能通过 Architecture 已定义的能力检查和 failure contract 表达，不能静默删减
  命令、字段或生命周期。
- 路径、临时文件、原子替换、进程调用、权限处理与跨进程锁优先使用 Python 标准库。确需
  平台专用能力时，在统一 abstraction 下分别使用标准库提供的 POSIX/Windows 实现，不能让
  `fcntl` 成为 import-time 或 distribution-wide 前提。
- Git 仍是外部运行时依赖；成熟的 Markdown/YAML parser 可以继续作为必要第三方依赖。
  “优先标准库”不授权手写不完整 parser，也不改变 Architecture 的解析语义。
- `external link` 在三个目标平台都必须正确执行 capability detection。Windows 环境若因
  filesystem、权限或系统策略不能创建 symlink，仍返回 Architecture 已定义的
  `symlink_unsupported`，完整保留现场且不回退为复制、junction 或其他不同语义的入口。
- 逻辑只读 install 在各平台采用可用的普通权限机制尽量阻止误写；该措施仍不是 sandbox。
  权限模型差异不能改变 fixed commit、mapping、Git tracking 或维护入口语义。

## 4. 状态与序列化要求

### 4.1 Portable manifest

manifest 是可由宿主 Git 追踪、clone 后用于 restore 和 install 内 portable link-parse 的
版本化产品文件。其 schema 至少表达 Architecture
[恢复清单](../../doctidex-git/architecture/domain-model.md#7-恢复清单与恢复项)定义的全部
install/link facts；序列化必须稳定、可 round-trip、拒绝重复 identity，并在写入前完成
schema 与路径自洽校验。未知 major schema blocked；同 major 的向后兼容字段按实现 Details
定义。manifest 可审阅但不是稳定的手工编辑 API，CLI 必须把无效或并发修改报告为冲突，
不能静默重写。

### 4.2 Runtime records

runtime records 只保存以下无法从 manifest/Git/filesystem 可靠重建的最小事实：

- install 的 owner root、key/ID/path、source/selector/commit、direct/dependency role、parents
  与 publication 完整性；
- link 的 owner、target、install、repository-relative base、safe state 与 current mapping；
- worktree 的 managed identity、owner、source/base、exact path 和创建完整性；
- bounded diagnostic identity 与不进入正常输出的故障上下文。

records 必须带 schema/version 与不可猜测 ownership identity，使用原子文件替换或等价机制
发布。缺失 record 不自动删除 payload；无法证明归属时返回 unavailable/damaged 并保留现场。
restore 可以从 portable manifest 重建 direct install/link records，但不能虚构 dependency
edges 或 worktree ownership。

### 4.3 Stable identity 与路径

- source identity 只规范化可客观证明等价的 locator；不能把相同 commit、相似 URL、mirror
  或 fork 推断为同 source。公开输出始终使用 sanitized locator。
- install ID/path 对 root/source/normalized selector 稳定且抗碰撞；worktree path 每次 open
  唯一。ID 编码不得包含 credentials 或可导致 path traversal 的输入片段。
- public result 返回 Architecture 要求的 root-internal 与 filesystem paths；internal object
  path、lock path 和 registry location 不得泄漏到正常 result。
- symlink 与 repository-relative path 使用 POSIX 词法语义；filesystem 边界使用平台路径
  API，并在发布前验证不会越过 owner root 或 target repository。

## 5. 关键实现顺序与失败边界

### 5.1 External dry-run/apply

1. 选择 root/host Git，清理 source 中的凭据，规范化 selector，分配或复用 install identity。
2. 在 root mutation boundary 外解析 fixed commit；dry-run 只能使用可丢弃的调用期 Git 数据。
3. 形成包含 expected index/manifest/mapping/Git tracking state 的 mutation plan。
4. apply 取得 root mutation ownership 后重新验证 plan；不一致即 conflict。
5. 先保证 boundary/unsafe、ignore 与 direct manifest/parent edge，再发布 install path 和完整
   record；每一步使用临时路径与原子 rename 或等价的可恢复发布方式。
6. 返回实际 network、changed、tracking state、部分完成 facts 和重试动作。

同 key 重试核对 fixed commit 和 mapping 后只补齐缺失步骤。路径被其他 identity 占用、
tracked payload、冲突 ignore 或无法解释的部分状态均不得 replace。

### 5.2 Link 与 mapping

link apply 先解析最内层完整 source mapping，再验证 repository suffix、safe/unsafe、负责
index、target overlap 与 Git tracking；重新验证后依次发布 frontmatter、相对 symlink、
current mapping 和 manifest link record。失败不得留下指向其他 identity 的可用假象。

link-parse 的判定顺序固定为：按路径自身分类 -> 恢复外层 owner -> 识别 content root ->
current-owner mapping -> portable manifest/link record -> 外层 matching dependency ->
repository suffix -> target/integrity state。该顺序及每个分支的可靠字段、Finding 和 tests
必须在 Python Details 中逐项记录。

### 5.3 Validation 与分页

validation 先构造未分页领域结果，检测环时以规范化词法路径为 visited identity，再按
coverage 过滤、稳定排序并交给 budgeter。cursor 可以编码签名后的查询 identity 或引用
内部稳定快照，但必须是不透明、受 operation/root/scopes/filter/limit/mode 约束，状态变化
无法保持同一结果时返回 `cursor_invalid`。

### 5.4 Worktree 与中断恢复

open 先解析 owner/source/commit 并分配唯一 path，再调用 Git 创建 detached worktree，最后
发布 record。中断留下的 path 必须能通过 Git worktree metadata 与受管 namespace 扫描被
识别为 orphan candidate；在缺少 managed identity 时只报告和保留，不自动 adopt 或 remove。
list 逐项容错并从原生 Git status 产生 state；close 在删除前再次验证 exact identity 与 clean，
删除 Git worktree 成功后才移除 record。共享 objects 不随 close 回收。

## 6. 用户决定与仍需讨论的问题

用户已经确认以下 Python 实现决定：

| 决定 | 已确认结果 | Architecture 边界 |
|---|---|---|
| Package version | `whero-doctidex` 升级为 `1.0.0`。 | 与 protocol version、JSON schema version 分别表达。 |
| 目标平台 | 支持 Linux、macOS 与 Windows，并优先使用 Python 标准库处理平台机制。 | 不改变命令契约；symlink capability 不足仍 blocked，禁止复制 fallback。 |
| Git object cache | 延续 `0.x` 的专用用户级共享 cache 思路，但只 cache bare Git objects。 | install checkout 直接在目标 install path 创建 Git worktree，不 cache materialized checkout，不使用 hard link/symlink projection。 |
| Cache cleanup | 提供 `doctidex-git cache clean --url URL [--dry-run \| --apply] [--json]`。 | 不进入 Published Skills；只删除没有有效 linked worktree 且其余登记全部 prunable 的单个 bare source cache。 |

这些决定只收敛 Architecture 留给 Python Details 的实现空间，不改变 Architecture 已规定的
public path、fixed commit、网络、副作用、失败与恢复语义。

cleanup 是独立显式生命周期，不能由 `worktree close`、external remove/restore 或普通读取
顺带触发。命令以 URL 解析 canonical source identity，保持离线；未命中 cache、metadata
损坏、worktree 状态无法分类或 source lock 下复查发生冲突时不删除。有效 linked worktree
无论 clean、dirty 或是否属于当前 doctidex root 都会阻止清理；prunable 只采用 Git 的客观
判定，不能由 runtime record 或路径猜测替代。apply 删除 bare cache 后，未来 install/restore/
worktree open 可以按既有网络契约重新取得 objects，但本次操作不改动这些对象的 records、
manifest 或固定 commit。

## 7. 实施与文档顺序

1. 先把 distribution version 设为 `1.0.0`，建立 Linux/macOS/Windows CI 与统一平台
   abstraction；随后建立 v1 result/error、document/path/tree 和 validation vertical slice，
   删除旧协议字段，以纯目录 fixture 覆盖 protocol findings、semantic candidates、scope
   与 cursor。
2. 重建 CLI parser/orchestrator/renderer，使目标命令、通用 envelope、错误和 bounded output
   可独立测试；此阶段不发布新的 Skills。
3. 实现专用用户级 shared bare object store、source/host Git、manifest/records 与 external
   install/restore，再实现 link/mapping；install 直接在目标路径创建 worktree，覆盖 default
   branch 固定、Git tracking、环状 dependency、portable broken symlink、跨平台 symlink
   capability 和部分成功。
4. 实现 worktree open/list/close、source kinds、orphan discovery、dirty preservation，再
   实现不进入 Skills 的单 source `cache clean`；覆盖 active/prunable/malformed worktree
   metadata、source lock 复查、dry-run/apply 和跨平台删除失败。
5. 代码存在后建立当前 Python Details：每个 ownership unit 记录职责/非职责、callers、
   dependencies、types/functions 及全部 attributes、effects、failures、concurrency、usage、
   tests 和已知限制。
6. 建立 Architecture-to-code/test/Details traceability matrix，逐页证明第 2.1 节没有空白、
   冲突、额外行为或仅由人读 renderer 掩盖的 schema 差异。
7. 最后把 8 个旧 Skills 切换为 Overview、Read、Maintenance，验证每个 Skill metadata、
   无环阅读链和 containing plugin；在代码与命令可用前不得发布目标 Skill 文本。
8. 运行完整 tests、Ruff、文档链接/状态检查、Skill/plugin validator 与公开 artifact forward
   test，确认后把本子需求标为 `implemented`；overview 仅按聚合门槛同步。

阶段允许在 feature branch 中逐步落地，但默认分支上的 current Details、CLI 与 Published
Skills 必须保持同一可用版本，不能把目标 Skill 指向尚未存在的命令。

## 8. 实现与文档影响

| 层面 | 本子需求完成时的要求 |
|---|---|
| Python package | `whero-doctidex` `1.0.0` 支持 Linux/macOS/Windows，平台机制优先使用标准库；移除无职责的 v0 模块、依赖和 public code paths。 |
| Protocol | 完整实现协议 `v1.0.0` 与 scoped validation，不保留 mount/old-filter/plugin-readiness。 |
| Git domain | 使用专用用户级 cache 跨 root 复用 bare objects；不 cache checkout/projection，在目标 install/worktree path 直接物化 Git worktree；提供由 Git worktree facts 保护的单 source cleanup。 |
| CLI integration | parser、JSON/human rendering、pagination、exit code、diagnostics 与 Architecture 一致。 |
| Python Details | 当前文档只描述实际 v1 code，并形成可从每项 Architecture 契约与 Requirement 双向导航的代码设计地图。 |
| Tests | 单元、CLI 集成、本地 Git fixture、并发、中断与失败恢复覆盖全部 Architecture 验收场景及明确禁止的偏离行为。 |
| Published plugin | distribution 发布 `cache clean`，但三个 Skills 不提及或路由该管理命令；其余受支持 agent 工作流使用同一命令 surface，旧 8 Skill 不再作为兼容 surface 发布。 |
| Archive/navigation | `0.1.0` Archive 保持只读历史入口；当前导航不把旧 Details 表述为 v1 实现。 |

## 9. 实现结果与验证证据

本次不兼容切换已按 Architecture 完成，当前结果如下：

| 层面 | 实现结果与证据 |
|---|---|
| Python package 与 CLI | `whero-doctidex` 已升级到 `1.0.0`；仅发布 `validate`、`external install/link/restore/link-parse`、`worktree open/list/close` 与内部维护用 `cache clean`，统一输出 `schema_version: "1.0"` 的 JSON envelope。 |
| Protocol validation | 已实现协议 `v1.0.0`、最近负责制、局部配置、可达性、CommonMark inline/reference link 注释关联，以及由实际 scope 与 support closure 驱动的 scoped validation。 |
| External 与状态 | 已实现 fixed-commit install、default branch provenance、direct/dependency/self/cycle 截止、shared bare source cache、portable manifest、runtime records、相对 symlink、restore 与跨 owner 的 portable broken-link mapping；manifest 拒绝重复 key、重复 identity 及不自洽路径。 |
| Worktree 与 cache | 已实现 managed path、working tree、bare gitdir、gitfile、submodule 与 URL source 分类，扁平 detached worktree 的 open/list/close、dirty/orphan 保留、common gitdir 归一化，以及按 Git worktree facts 保护的单 source cache cleanup。 |
| Details 与追踪 | 当前 [Python Details](../../doctidex-git/details/python/index.md) 已按 ownership unit 记录模块、类型、属性、效果、失败、并发和测试；[Architecture 追踪矩阵](../../doctidex-git/details/python/traceability.md)逐页连接 producer、consumer 与测试，并列出禁止偏离行为的证据。 |
| Published plugin | 已用 Overview、Read、Maintenance 三个 installed-product Skills 替换旧八 Skill；阅读链无环，`cache clean` 与内部 storage/debug 信息不进入用户 surface。三个 Skill validator 与 containing plugin validator 均通过。 |
| 自动验证 | Ruff format/check 与 `31` 个 pytest 用例通过；CI 在 Linux、macOS、Windows 和 Python 3.11/3.12 上执行 editable install、Ruff 与 pytest，并保留 symlink capability 的成功/不支持分支。 |
| 独立 forward test | 独立 agent 仅凭公开 artifacts 完成 scoped validation、install 仓库内 broken portable symlink 解析，以及 dirty managed worktree 的检查、交付权限停点与安全 close；发现的问题已在实现或 Skill 中修正后复验。 |

测试还覆盖 root lock 冲突的有界失败、worktree 已创建但 record 尚未发布时的中断证据、
moving selector 重试稳定性、symlink preflight、manifest damage、nested root、bounded cursor 和
Windows symlink 不可用时无持久变更。真实托管远端的凭据与网络故障不由 CI 制造；实现通过
非交互 Git、credential sanitization 和结构化失败保持 Architecture 规定的边界。

## 10. Requirement 关系

- 本记录是 [DX-REQ-0008.1](01-doctidex-git-alignment.md) 的后续实现需求；0008.1 定义
  语言无关 user surface 和公共契约，本记录不得用 Python 机制反向覆盖其决策。
- 两个子需求共同属于 [DX-REQ-0008](overview.md)；本文已无 live questions，代码、Details、
  Skills 与验证均已完成。0008.1 与 0008.2 均为 `implemented`，overview 因而满足
  `implemented` 聚合门槛。

## 11. 验收标准

1. 第 6 节全部用户决定已纳入 package、platform、Git state、cache cleanup、实施顺序和
   测试要求，且所有 question/answer blocks 已移除；新增 public cleanup 生命周期已经先同步
   DX-REQ-0008.1 与 Architecture。
2. 第 2.1 节 traceability matrix 已逐项落到 Python Details、producer、consumer 和 tests；
   Architecture 的每个 command、field、default、状态、生命周期、失败及禁止行为都有证据，
   且不存在额外、缺失、重命名、放宽、收紧或旧版兼容行为。
3. 目标 CLI 完整实现 Architecture 的命令、schema、失败、网络、dry-run/apply、pagination
   与 exit code；旧 public surface 不再作为兼容入口。
4. protocol validation 覆盖 `v1.0.0`，包括最近负责制、局部配置、可达性、结构化 link 注释
   和 scoped support closure，且不依赖 Git/registry。
5. 专用用户级 shared source store 只包含按 canonical source identity 复用的 bare Git
   objects；没有 revision checkout/projection cache。install checkout 直接物化到目标路径，
   portable manifest、runtime records、install 与 worktree payload 各自满足分层职责。
6. install/link/restore 正确处理 selector identity、默认分支 commit 固定、Git tracking、
   direct/dependency 提升、self/cycle、safe/unsafe、并发、部分成功和幂等重试。
7. link-parse 对 install/link 任意子目录及 symlink 自身正确区分 owner/content root、
   current-owner/portable mapping、available、owner missing、合法 dependency missing、
   unmanaged 与 damage；命令离线、只读，moving default branch 不改变既有结果。
8. worktree 支持 managed path、URL、working tree、bare gitdir 和 gitfile；open 始终扁平隔离，
   list 从 Git facts 判断状态，dirty/unavailable/orphan/unmanaged 现场不会被 close 删除。
9. `cache clean` 对单个 URL 默认 dry-run、显式 apply、离线且不进入 Skills；任何有效 linked
   worktree 都阻止删除，只有无有效 worktree 且其余登记全部由 Git 判为 prunable 时才能删除
   bare cache，且不触碰 worktree path、records、manifest 或其他 source。
10. 所有写入和中断场景都报告实际 changed、preserved state、affected 和可行动下一步；锁顺序
   符合 Architecture，不在等待 network 时持有 root mutation lock。
11. 最终 Details 完整覆盖每个 Python ownership unit 的职责、非职责、callers、dependencies、
   types/functions、全部 attributes、effects、failures、concurrency、usage、tests 与限制，
   并与实际代码一致。
12. Linux、macOS 与 Windows 测试共同覆盖 path、lock、atomic replace、permission、Git
    subprocess、symlink capability 和 interruption；平台差异不得改变 JSON 契约或保留结果。
13. 测试至少覆盖 safe/unsafe external source、install/link 子路径、主仓库与 install 内 broken
    symlink、portable dependency absent/available、损坏 mapping、URL/本地/submodule source、
    revision failure、default branch 移动、offline/online、环状依赖、并发、partial success、
    orphan/dirty close、nested roots、scoped validation 和 bounded output。
14. 三个 Published Skills 只使用已实现命令，且不暴露 `cache clean`；完成 Skill metadata、
    无环阅读链和 containing
    plugin 验证；独立 agent 只凭 installed-product artifacts 能完成核心工作流。
15. 完整 pytest、Ruff、文档链接与状态检查、Skill/plugin validators 全部通过后，本记录才
    可进入 `implemented`；`approved` 仍需用户明确确认。
