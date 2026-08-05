# 已发布 Skill 系统

本篇定义四个 Published Skills 的职责、阅读链、命令说明充分性和用户/内部信息边界，也是维护
`impls/agent-plugins/doctidex-git/skills/` 的当前设计约束。仓库维护者在创建、修改或删除该产品
的 Skill 或其 metadata 前，必须先读本篇及受影响 workflow 的 Architecture 和 public interface。

产品工作流以 [产品与 user surface](product-and-user-surfaces.md)、[树与 validation](tree-and-validation.md)、
[external snapshot](external-snapshots-and-presentations.md)、[worktree/cache](worktrees-and-cache.md) 和
[operation safety](operation-safety-and-recovery.md) 为准，精确 public command contract 由
[CLI](interfaces/cli.md) 和 [JSON Schema](interfaces/cli-schema.md) 负责。Skill 应使已安装产品中的
agent 能完成支持的工作流，却不成为另一份 Architecture authority，也不把维护过程带入产品。

## 1. 四 Skill 结构

| Skill | 负责 | 不负责 | CLI |
|---|---|---|---|
| `doctidex-git-overview` | 共同心智模型、术语、根选择、输出/失败约定、安全边界和任务路由。 | 重复专项步骤、把可读提及当跨 root identity，或要求每次重读。 | 说明共享语法；把专项调用路由至 Mentions、Read 或 Maintenance。 |
| `doctidex-git-mentions` | owner-root-scoped managed-install 的只读提及解析、上下文补全、候选回显、消歧与 external-link evidence。 | 自然语言 CLI parser、persistent alias、一般 Git repository discovery，或 install/restore/remove/link 等写入。 | `external list`、`external link-parse`。 |
| `doctidex-git-read` | index/link 渐进阅读、原生搜索、边界/unsafe/结构化注释，以及从 Mention result 继续读取。 | 强制阅读顺序、替代文件工具、重新解析提及、自动安装依赖或修改外部内容。 | 不直接调用提及解析命令；按需路由 Mentions。 |
| `doctidex-git-maintenance` | protocol/product 分层、validation、可选 external presentation 和 worktree 多根维护，以及从确认的 Mention result 继续维护。 | 强制使用受管工作流、替用户写语义正文、把提及结果当用户授权、重新解析提及，或判断权限与 Git 交付。 | `validate`、除只读提及查询外的 `external`、`worktree`。 |

旧 Setup、Mount、Workspace、Validate、Review 和 Maintain 的仍有效用户信息分别并入这
四个 Skill；mount/filter/projection 和旧 maintenance scope planning 的专属内容删除，
不作为兼容教程保留。新的 validation `--scope` 只表示本次关注目录集合，不建立持久维护
计划或写入边界。

`doctidex-git cache clean` 是面向 human/program operator 的已安装 CLI 管理接口，当前明确
排除在四个 Published Skills 之外。Overview 不把它列为共享命令或路由目标，任何 Skill
都不提及、推荐或调用它；Skill 也不因 close、restore 或 objects 缺失暗示隐式
cleanup。

## 2. 维护设计约束

### 2.1 范围、受众与 metadata

每次变更先确认所涉用户场景、公共命令、Architecture 和当前四个 Skill；改变产品行为时，先更新
相应 Architecture authority，而不是以 Skill 文本暗中定义新行为。Published Skill 只面向已安装
产品，不能要求 agent 阅读本仓库源码、Architecture、Impls、tests、repository-local path 或开发
命令，也不得先于对应命令实现写入发布目标 Skill。

每个 Skill 的 frontmatter 只含 `name` 和完整的 `description`。description 必须说明触发场景和
不会触发的相邻场景；目录名、frontmatter name、`agents/openai.yaml` 的显示 metadata 及
`$skill-name` prompt 必须一致。metadata 保持 quoted strings，`short_description` 为 25--64 个
字符。name 使用不超过 64 个字符的 lowercase hyphenated identifier，优先动词开头。`SKILL.md` 与其直接
reference 构成跨 host 的可移植 bundle；Codex 可读取 `.codex-plugin` 和 `agents/openai.yaml`，其他 host 可以忽略
这些 metadata 并使用自身的注册机制或直接读取 Skill。新建 Skill 在获创建授权后使用 active Skill catalog 提供的
初始化工作流；不要新增 README、changelog 或没有明确读取条件的 reference 目录。Published Skill 一般不得包含
package/运行时安装或重装、开发、发布、tag 确认、测试或维护验证的描述；但 Overview 可以保留一个明确标注的 GitHub
distribution bootstrap，简洁说明当前 Skill/product metadata 与协议版本、匹配 tag、GitHub URL 和 package 子目录，并
说明命令在已选兼容 `.venv` 中执行。四个 Published Skills 的命令示例直接使用原始 `doctidex-git` 命令名，不使用
`DOCTIDEX_GIT` 占位符；`DOCTIDEX_GIT_CACHE` 仍是独立的用户环境变量。该受限段是
已安装产品的分发入口，不是 repository development setup；其余事实和维护流程仍由 README、Architecture、Impls、
Requirement 与后置验证负责。

Skill 先定义工作流所用术语、调用方输入、默认 context、可观察结果和下一决策，再说明步骤。产品
概念足以让 agent 完成任务，但不公开 cache、key、lock、worktree 管理、内部 schema、repository
setup、测试或诊断实现；必要的用户路径、状态和操作不能因内部实现而被隐藏。

### 2.2 阅读链与内容归属

Overview 是共同心智模型、术语、共享 CLI grammar、结果与安全边界的唯一 owner。Mentions 是提及
解析、命令调用与消歧边界的唯一 owner；Read 与 Maintenance 只说明获得 Mention result 后各自如何继续。
运行时阅读关系以第 3 节为唯一约束；任何 "if not already read" 路由都必须说明返回位置，且不得在
一个任务中重新打开已经加载的 Skill。

不要把共同段落复制到每个 Skill。`SKILL.md` 保持简短、命令式且少于 500 行；详细 command contract
可置于紧邻的 reference，但每个 reference 必须由主 Skill 直接链接并声明读取条件。Overview 加
Mentions 必须足以完成一个只读提及解析场景；无需解析提及的读取或维护场景则由 Overview 加相应专项完成。

### 2.3 用户 cache 配置与非开发边界

README 负责面向安装者的同 tag Git package 安装与 Published agent bundle 获取入口；Architecture、Impls、Requirement
与后置验证负责 release identity、metadata 关系和安装可用性的说明与核对。README 给出 bundle checkout 与其中
`skills/` 路径，但不假定所有 host 都使用 Codex 或存在统一 plugin command。Overview 可在其受限 distribution bootstrap
中重复当前 Skill/product metadata 与协议版本、GitHub tag、package 安装命令和 package 子目录，以便从已安装 Skill 追溯同一分发入口；其他
Published Skill 仍只描述已安装产品的用户工作流，不重复这些事实，也不要求 agent 执行开发、发布或验证动作。

只有 Overview 说明可选 `DOCTIDEX_GIT_CACHE` 的用户配置：用户在启动 CLI、automation 或会触发 hook 的 Git
进程前自行选择可写路径，agent 不持久化该选择。专项 Skill 继承这项前提而不重复环境设置步骤，仍不得路由、
推荐或调用 `cache clean`，也不得披露 cache 内部 layout。

### 2.4 工作流、命令与决定边界

每个 Skill 以用户场景说明 prerequisite、输入、默认值、所选 context、可观察结果、保留状态、
failure 和非责任。保留原生 file、search、shell、edit 和 Git 工具；CLI 只提供普通工具不能可靠
取得的 doctidex/Git 事实，必须 deterministic 且不调用 AI。agent 仍负责语义正文、任务相关性、
unsafe 范围、diff 质量、权限与 Git delivery 判断。

Skill 第一次引入某命令时，Overview 与该专项合起来必须让 agent 无须 `--help`、错误试探或实现文档
便能安全调用。契约至少说明：

- 精确 invocation、参数格式、必填/可选/互斥/重复关系与省略行为；
- cwd、ROOT、PATH、SOURCE 或 WORKTREE 的选择、嵌套根歧义和输入存在条件；
- read/write/network、dry-run/apply、batch/partial success/interruption 与持久效果；
- agent 下一步需要读取的 status、result、finding、affected、preserved state、`requires_user`，以及
  limit、filter、summary、truncation 和 opaque cursor；
- stable failure code 的用户原因、可安全恢复动作及何时必须停下取得用户输入。

Mentions 必须说明 managed-install 的 repository path/host/revision 提及、external link path、上下文补全、候选
回显和消歧边界，并在其自身及直接 reference 中提供 `external list` 和 `link-parse` 的完整提及场景契约。Read 与
Maintenance 只能路由到 Mentions，并消费返回的候选或诊断，不得复制其查询、补全或消歧策略。各 Skill 仍须说明
本工作流所需的 fixed commit 与 selector provenance、direct/dependency install 和 promotion、owner/content root、
managed path、validation scope/coverage、link-parse target state、worktree lifecycle 及 remove 的 reference protection；
这些事实仍由模型、workflow、CLI 和 JSON Schema authority 定义。`cache clean` 是仅供 human/program operator 使用的
已安装 CLI 管理接口，四个 Published Skills 都不得路由、推荐或调用它，也不得暗示其他 lifecycle command 会触发
cleanup。

默认使用精确的 ROOT、PATH、SOURCE 或 WORKTREE；只在任务确实聚焦部分目录时使用 validation scope。
先读取 coverage、scope 和 collection 统计，再分页，不得以最大 limit 代替收窄。失败引导必须区分
未完成 operation、affected object、保留结果和下一动作；credentials、network、revision、link target、
manifest/Git tracking、dirty worktree 或 delivery 不能以无限重试代替用户决定。
不要把 stack trace 或内部 storage 当作正常决策界面；无法恢复时向用户报告 operation、affected
object、已保留结果和可用的 diagnostic fact。

### 2.5 维护侧验证

每次变更都检查 trigger、frontmatter、metadata、直接 links、无环阅读链、命令契约、用户/内部信息
边界、bounded output 和 failure guidance。验证变更的 Skill 及其 containing plugin；从 active Skill
catalog 取得当前 validator 路径，不把这些仓库维护命令复制进 Published Skill。

涉及 release identity 或 cache 配置时，额外在 README、metadata、Architecture、Impls 与相应测试中验证协议、plugin
与 distribution 的 major 版本关系、同一 Git tag 的 package 安装和 bundle checkout、可移植 `skills/` 路径，以及
Overview 对当前版本、受限 distribution bootstrap、手动配置、process inheritance、无持久化和 `cache clean` 边界的说明；
同时检查非 Overview Published Skills 未引入 package/运行时安装、开发、发布、tag 确认、测试或维护验证描述，并检查
Overview 没有把分发入口扩展成开发、发布或验证教程。

复杂 workflow 的变更还需用 fresh independent agent 进行 forward test。测试只提供公开 artifacts，
不泄漏预期 finding 或修复，并覆盖正常、clean/no-op、歧义、failure 和授权边界。

## 3. 阅读链

```text
选择当前专项 Skill
  -> 尚未加载 Overview？只加载一次
  -> 返回已选择的专项 Skill
  -> 遇到人类可读提及且尚未加载 Mentions？加载一次并返回当前专项
  -> 仅在任务确实跨越工作流边界时路由到另一个专项 Skill
```

Overview 只向专项 Skill 路由，不反向要求重读。Mentions 可以把其结果交回 Read 或 Maintenance，
但不能要求任一专项重新加载自己；专项之间也不能形成强制循环。已加载的 Overview 或 Mentions
在同一任务中不重复打开。提及解析本身由 Overview 加 Mentions 完成；后续读取或维护从原专项继续。

## 4. 专用 Mention Skill

用户在协作中以 repository path、可选 host/revision、完整 external link path 或不完整 path spelling 指向内容时，
agent 使用 `doctidex-git-mentions`。这是一个高频但独立的只读对话能力：它把用户提供的线索、当前任务上下文和一个
明确 owner root 中可观察的 managed facts 组织为可审阅 candidate 或可解释的无法解析结果。它不是自然语言 CLI parser、
persistent alias、一般 Git repository discovery 或任何写入授权。

Mentions 必须要求 agent：

1. 先选择/回显 owner root；repository path、`install_id` 与同名 source 不能跨 root 复用。
2. 对 repository path（如 `Viennan/wiki`）与 optional host/tag/branch/full commit，在当前 managed install record
   中调用 `external list`。它只读，不能用最近安装、current directory 或模糊 URL 自动补齐
   target；同 path 的不同 host 保持多个 candidate。
3. 对完整、实际存在的 external link path、link 自身或其内部目录，先原生读取；只在需要 mapping/source/revision/
   install/target-state facts 时调用 exact `external link-parse`。`link-parse` 不是 path 搜索器。
4. 对不完整 external link spelling，只从当前任务相关文件与 link target、附近负责的 `index.md`、已回显的
   `presentation_paths` 和对话事实补全候选；只有得到唯一的实际 path 后才可 parse，不得扫描无关目录、猜测 suffix 或
   创建 mapping/install。
5. 对零 candidate、多个 candidate、root/runtime/mapping damage、unmanaged path 或未展开 portable dependency，
   回显可读 evidence 与保留状态并请求澄清或必要授权。只有唯一或用户明确确认的 InstallReference 才能把其 opaque
   `install_id` 交给后续 exact command；list/parse result 本身不是执行授权。

Mentions 只返回 candidate、唯一已确认的 opaque `install_id` 或诊断；result 本身不是执行授权。Read 用 available
`working_path` 继续原生读取，Maintenance 只在得到唯一或用户确认的 InstallReference 后才把 exact ID 传给已获授权的
维护命令。普通 repository、native worktree、submodule 和 unmanaged clone 继续使用原生工具；不因用户提及名称而
进入此 Skill。

## 5. 读取不可访问 symlink 时的引导

Read Skill 保持原生工具优先，但必须为无法访问的 symlink 提供确定的升级路径：

1. 在任一按 doctidex 规范阅读的主仓库或 install 内容中，原生读取遇到 symlink target 不存在
   或无法进入时，带 symlink 自身路由到 Mentions，并取得其 `external link-parse` result。

2. 先读取 `mapping_origin`、`target_state`、`root` 和 `content_root`：
   - `available`：使用 `working_path` 继续原生读取；
   - `owner_install_missing`：路由到 Maintenance Skill，按返回 install ID 执行 restore；
   - `dependency_not_installed`：说明这是 install 仓库 portable link 的合法未展开状态，展示
     source、selector、fixed commit 和 `dependency_parent_install_id`，由 agent 决定是否
     路由到 Maintenance；若安装，使用 `--commit resolved_commit`，不得重新解析作为
     provenance 返回的 branch/tag；
   - `not_applicable`：回到普通文件系统/Git 诊断，不把未受管状态当作产品失败；
   - `unavailable`：按 finding 修复真实 manifest/mapping damage。
3. Read Skill 不自动调用 install/restore，不改写 broken symlink，也不要求在只读 install
   内递归创建依赖。依赖安装完成后重新路由 Mentions，并从外层 `working_path` 继续读取。

该引导是访问失败时的按需辅助，不把每个 symlink 或普通目录都变成 CLI 前置检查，也不把
产品 target state 当作 protocol validation 结论。

## 6. 维护决策顺序

Maintenance Skill 先帮助 agent 选择工作方式，再介绍命令：

1. 任务维护当前宿主 working tree 且 selector 等于当前 commit 时，优先直接使用当前路径和
   原生 Git；不要求 open。
2. 现有 changes 需要隔离、目标是其他 source/revision 或用户要求独立现场时，可以选择
   doctidex-git worktree，也可以选择手工/原生 Git 方案。
3. 在 install 内容中发现进一步依赖且决定继续使用 doctidex-git 时，使用当前 install ID
   作为 `--dependency-of`；不要在只读 install 内运行嵌套 checkout。
4. 只需临时阅读 dependency 时保留 dependency-only；需要提交 external link 或恢复时，
   以相同 source/selector 普通 install 将其提升为 direct。
5. 用户以 repository path、可选 host/revision 或 external link path 提及时，路由 Mentions 获得 owner-root-scoped
   candidate 或 path evidence。不存在 presentation 的 list item 仍可作为 managed install candidate，但不把它编造成
   external link path。
6. 已不需要某个 managed install 且已获删除授权时，先从确认过的 Mention result、已读取的 link-parse result 或之前的
   lifecycle result 取得 exact Install ID，dry-run remove 并阅读 reference evidence；出现 blocked reference 时回到用户决定，
   不让 Skill 自动删除文档、symlink、mapping 或 dependency edge。

“优先”表达默认建议，不是禁止隔离；“受管”表达产品承诺，不是协议符合性或工具排他性。
