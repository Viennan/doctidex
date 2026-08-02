# 已发布 Skill 系统

本篇定义三个 Published Skills 的职责、阅读链、命令说明充分性和用户/内部信息边界，也是维护
`impls/agent-plugins/doctidex-git/skills/` 的当前设计约束。仓库维护者在创建、修改或删除该产品
的 Skill 或其 metadata 前，必须先读本篇及受影响 workflow 的 Architecture 和 public interface。

产品工作流以 [Architecture system](index.md#系统与-workflow)为准，精确 public command contract 由
[CLI](interfaces/cli.md) 和 [JSON Schema](interfaces/cli-schema.md) 负责。Skill 应使已安装产品中的
agent 能完成支持的工作流，却不成为另一份 Architecture authority，也不把维护过程带入产品。

## 1. 三 Skill 结构

| Skill | 负责 | 不负责 | CLI |
|---|---|---|---|
| `doctidex-git-overview` | 共同心智模型、术语、根选择、输出/失败约定、安全边界和任务路由。 | 重复专项步骤或要求每次重读。 | 说明共享语法，不独占命令。 |
| `doctidex-git-read` | index/link 渐进阅读、原生搜索、边界/unsafe/结构化注释，以及不可访问 symlink 的按需解析。 | 强制阅读顺序、替代文件工具、自动安装依赖或修改外部内容。 | 按需 `external link-parse`。 |
| `doctidex-git-maintenance` | protocol/product 分层、validation、可选 external presentation 和 worktree 多根维护。 | 强制使用受管工作流、替用户写语义正文、判断权限或执行 Git 交付。 | `validate`、`external`、`worktree`。 |

旧 Setup、Mount、Workspace、Validate、Review 和 Maintain 的仍有效用户信息分别并入这
三个 Skill；mount/filter/projection 和旧 maintenance scope planning 的专属内容删除，
不作为兼容教程保留。新的 validation `--scope` 只表示本次关注目录集合，不建立持久维护
计划或写入边界。

`doctidex-git cache clean` 是面向 human/program operator 的已安装 CLI 管理接口，当前明确
排除在三个 Published Skills 之外。Overview 不把它列为共享命令或路由目标，Read 与
Maintenance 不提及、推荐或调用它；Skill 也不因 close、restore 或 objects 缺失暗示隐式
cleanup。

## 2. 维护设计约束

### 2.1 范围、受众与 metadata

每次变更先确认所涉用户场景、公共命令、Architecture 和当前三个 Skill；改变产品行为时，先更新
相应 Architecture authority，而不是以 Skill 文本暗中定义新行为。Published Skill 只面向已安装
产品，不能要求 agent 阅读本仓库源码、Architecture、Impls、tests、repository-local path 或开发
命令，也不得先于对应命令实现写入发布目标 Skill。

每个 Skill 的 frontmatter 只含 `name` 和完整的 `description`。description 必须说明触发场景和
不会触发的相邻场景；目录名、frontmatter name、`agents/openai.yaml` 的显示 metadata 及
`$skill-name` prompt 必须一致。metadata 保持 quoted strings，`short_description` 为 25--64 个
字符。name 使用不超过 64 个字符的 lowercase hyphenated identifier，优先动词开头。新建 Skill
在获创建授权后使用 active Skill catalog 提供的初始化工作流；不要新增 README、changelog、安装教程
或没有明确读取条件的 reference 目录。

Skill 先定义工作流所用术语、调用方输入、默认 context、可观察结果和下一决策，再说明步骤。产品
概念足以让 agent 完成任务，但不公开 cache、key、lock、worktree 管理、内部 schema、repository
setup、测试或诊断实现；必要的用户路径、状态和操作不能因内部实现而被隐藏。

### 2.2 阅读链与内容归属

Overview 是共同心智模型、术语、共享 CLI grammar、结果与安全边界的唯一 owner；专项 Skill 只补充
自身工作流。运行时阅读关系以第 3 节为唯一约束；任何 "if not already read" 路由都必须说明返回
位置，且不得在一个任务中重新打开已经加载的 Skill。

不要把共同段落复制到每个 Skill。`SKILL.md` 保持简短、命令式且少于 500 行；详细 command contract
可置于紧邻的 reference，但每个 reference 必须由主 Skill 直接链接并声明读取条件。一个 Overview
加一个相关专项必须足以完成一个受支持场景。

### 2.3 工作流、命令与决定边界

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

Skill 必须转述其实际公开的当前命令事实，包括 fixed commit 与 selector provenance、direct/dependency
install 和 promotion、owner/content root、managed path、validation scope/coverage、link-parse target
state、worktree lifecycle 及 remove 的 reference protection；这些事实仍由模型、workflow、CLI 和 JSON
Schema authority 定义。`cache clean` 是仅供 human/program operator 使用的已安装 CLI 管理接口，三个
Published Skills 都不得路由、推荐或调用它，也不得暗示其他 lifecycle command 会触发 cleanup。

默认使用精确的 ROOT、PATH、SOURCE 或 WORKTREE；只在任务确实聚焦部分目录时使用 validation scope。
先读取 coverage、scope 和 collection 统计，再分页，不得以最大 limit 代替收窄。失败引导必须区分
未完成 operation、affected object、保留结果和下一动作；credentials、network、revision、link target、
manifest/Git tracking、dirty worktree 或 delivery 不能以无限重试代替用户决定。
不要把 stack trace 或内部 storage 当作正常决策界面；无法恢复时向用户报告 operation、affected
object、已保留结果和可用的 diagnostic fact。

### 2.4 发布前验证

每次变更都检查 trigger、frontmatter、metadata、直接 links、无环阅读链、命令契约、用户/内部信息
边界、bounded output 和 failure guidance。验证变更的 Skill 及其 containing plugin；从 active Skill
catalog 取得当前 validator 路径，不把这些仓库维护命令复制进 Published Skill。

复杂 workflow 的变更还需用 fresh independent agent 进行 forward test。测试只提供公开 artifacts，
不泄漏预期 finding 或修复，并覆盖正常、clean/no-op、歧义、failure 和授权边界。

## 3. 阅读链

```text
选择专项 Skill
  -> 尚未加载 Overview？只加载一次
  -> 返回已选择的专项 Skill
  -> 仅在任务确实跨越工作流边界时路由到另一个专项 Skill
```

Overview 只向专项 Skill 路由，不反向要求重读；专项之间不能互相形成强制循环。已加载的
Overview 在同一任务中不重复打开。Overview 加一个相关专项 Skill 必须足以完成单一受支持
场景。

## 4. Read 的不可访问 Symlink 引导

Read Skill 保持原生工具优先，但必须为无法访问的 symlink 提供确定的升级路径：

1. 在任一按 doctidex 规范阅读的主仓库或 install 内容中，原生读取遇到 symlink target 不存在
   或无法进入时，对 symlink 自身运行：

   ```text
   doctidex-git external link-parse PATH --json
   ```

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
   内递归创建依赖。依赖安装完成后重新 link-parse，并从外层 `working_path` 继续读取。

该引导是访问失败时的按需辅助，不把每个 symlink 或普通目录都变成 CLI 前置检查，也不把
产品 target state 当作 protocol validation 结论。

## 5. 维护决策顺序

Maintenance Skill 先帮助 agent 选择工作方式，再介绍命令：

1. 任务维护当前宿主 working tree 且 selector 等于当前 commit 时，优先直接使用当前路径和
   原生 Git；不要求 open。
2. 现有 changes 需要隔离、目标是其他 source/revision 或用户要求独立现场时，可以选择
   doctidex-git worktree，也可以选择手工/原生 Git 方案。
3. 在 install 内容中发现进一步依赖且决定继续使用 doctidex-git 时，使用当前 install ID
   作为 `--dependency-of`；不要在只读 install 内运行嵌套 checkout。
4. 只需临时阅读 dependency 时保留 dependency-only；需要提交 external link 或恢复时，
   以相同 source/selector 普通 install 将其提升为 direct。
5. 已不需要某个 managed install 且已获删除授权时，先从 link-parse 或之前的 result 取得 exact
   Install ID，dry-run remove 并阅读 reference evidence；出现 blocked reference 时回到用户决定，
   不让 Skill 自动删除文档、symlink、mapping 或 dependency edge。

“优先”表达默认建议，不是禁止隔离；“受管”表达产品承诺，不是协议符合性或工具排他性。
