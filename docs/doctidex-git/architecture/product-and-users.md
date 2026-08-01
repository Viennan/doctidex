# 用户界面

本篇是产品定位、使用者场景和共同心智模型的权威入口。具体任务分别见
[Validation](system/validation-workflow.md)、[External](system/external-workflows.md)与
[Worktree/cache](system/worktree-and-cache-workflows.md)，命令及字段见
[CLI](interfaces/cli.md) 与 [JSON Schema](interfaces/cli-schema.md)。

## 1. 产品定位

doctidex-git 是 agent 在 Git 管理的 doctidex 目录树中工作的辅助产品。它由三个
Published Skills、一个确定性 CLI 和原生文件/Git 工具共同组成。CLI 只提供 doctidex
协议与 Git source 交叉处的客观事实；普通阅读、搜索、编辑、diff 和交付仍使用成熟的
原生工具。

一个 Git working tree 可以包含一个或多个 doctidex 根，也可以完全不符合 doctidex。
Git identity、doctidex-git 管理记录、symlink、submodule 或 presentation 技术都不决定
协议符合性；validation 只依据所选根的最终可观察目录树，并明确报告结论覆盖整个根还是
调用方选择的根内目录集合。

受管 external/worktree 是可选产品工作流，不是读取或维护网关。agent 可以根据任务、现有
Git 现场和用户偏好选择原生 Git、手工 worktree、submodule、symlink 或其他方式；以下
位置、恢复和生命周期承诺只适用于明确调用 doctidex-git 对应命令的对象。

## 2. 使用者与稳定接口

| 使用者 | 入口 | 稳定承诺 |
|---|---|---|
| 用户 | 人读 CLI、原生文件/Git 工具 | 可观察路径、状态、失败和恢复动作。 |
| Agent | Overview 加 Read 或 Maintenance Skill、CLI `--json` | 足够且无环的工作流说明、确定性事实和原生工具自由。 |
| 程序 | CLI `--json` | 版本化 envelope、operation schema、稳定 code 与有界 collection。 |

Python import、内部 registry、Git object store、锁、worktree 布局和 presentation 技术不是
公共 API。程序不得读取内部状态来绕过 CLI。

## 3. 前置概念与预期使用画面

所有使用者先区分三件事：doctidex root 是协议解释边界，Git repository 是版本控制边界，
managed owner root 是可选 external/worktree 状态的所有权边界。三者可以重合，也可以嵌套；
任何一个都不能推导另外两个。

| 使用者 | 开始前必须理解 | 预期使用画面 |
|---|---|---|
| Human | exact root、dry-run/apply、固定 commit、Git tracking 与 managed/unmanaged 的区别 | 在 shell 中审阅 human/JSON 结果，决定 network、写入、冲突和 Git delivery；需要时仍可直接用 Git。 |
| Agent | Overview 的共同心智模型、所选 specialist 的命令契约、原生工具自由和 user-decision boundary | 从 Skill 路由到一个工作流，用 JSON 获得客观事实，用原生文件/Git 工具完成阅读、编辑、审阅和交付准备。 |
| Program | CLI invocation、JSON schema major、exit code、root selection 和 cursor identity | 以 subprocess 调用稳定 CLI，验证 schema，分页消费 collection，并按 stable code 选择下一步。 |

典型交互不是“进入 doctidex-git session”，而是短生命周期循环：调用方观察当前文件/Git
现场，选择原生工具或一个 CLI operation，读取完整结果，作出下一项决定。省略参数只使用
本次 cwd 或输入路径，不保存为后续默认；warning、managed state 或 previous dry-run 都不
构成下一次 apply 的隐式授权。

Agent 的正常画面是 Published Skill 与原生工具共同工作，不是阅读 repository Architecture
或 Python Impls。Human 可以使用 human output，但需要精确自动化时与 program 一样使用
`--json`。Program 的稳定边界是 CLI/JSON，不是当前 Python package 的 private imports。

完整模型和依赖从 [Architecture index](index.md#模型层)进入；组件协作见
[组件、责任与依赖](system/components-and-dependencies.md)。

## 4. 场景与问题

| 场景 | 具体问题 | 入口 | 操作后可观察状态 |
|---|---|---|---|
| 阅读本地树 | 不应先通过插件网关才能读文件。 | Read Skill + 原生工具 | 文件不变；agent 理解 root、负责 index、边界与 unsafe。 |
| 检查完整根或关注目录 | 结构缺陷和语义判断不能混在一个“失败”中，局部检查也不能冒充全根符合。 | `validate` + 可选的重复 `--scope` | 离线 coverage、scopes、findings、semantic candidates、扫描与分页事实。 |
| 引入外部 Git | 根外物理内容不能直接成为 doctidex link target，checkout 也不应被宿主 Git 追踪。 | `external install` | 固定 commit 的 `/.doctidex` 内稳定安装、精确 ignore 规则和可版本化恢复清单。 |
| 展开已安装来源的依赖 | 递归 checkout 会制造嵌套所有权，环状引用还可能无限展开。 | `external install --dependency-of` | 宿主根下扁平 dependency install 和有限关系边；不写恢复清单。 |
| 建立就近入口 | 同一 source 子目录需要用户选择且可由宿主 Git 追踪的根内入口。 | `external link` | 指向稳定安装路径的相对 symlink、独立 boundary/unsafe 声明和可追溯 mapping。 |
| 恢复外部安装 | clone 或 clean 后安装载荷缺失，但已提交 symlink 应继续使用。 | `external restore` | 按清单中的 exact commit 和原路径重建；既有 symlink 不变。 |
| 识别路径或 broken symlink | agent 在主仓库或 install 中需要 source、commit、repository 子路径或不可访问 link 的依赖事实。 | `external link-parse` | 区分 current-owner mapping、installed-repository portable mapping、可恢复缺失、合法未展开 dependency 和真实损坏。 |
| 维护当前仓库当前 commit | 当前 working tree 已是可写现场，不应强制再开 worktree。 | Maintenance Skill + 原生 Git | 直接保留当前路径与现有 changes；需要隔离时仍可选择 open。 |
| 修改其他 source/revision | 只读入口不能作为编辑现场，隔离现场也不能递归嵌套。 | `worktree open/list/close` | selected root 的 `/.doctidex` 下扁平、固定 base commit 的可写 worktree。 |
| 协调多个根 | 多 repository 结果没有跨 Git 事务。 | Maintenance Skill + 每根独立命令/原生 Git | 每根分别保留 diff、validation、交付或 blocked 状态。 |
| 回收共享来源缓存 | human/program operator 需要回收不再被任何有效 linked worktree 使用的 bare source cache，又不能误删仍被其他根使用的 objects。 | `cache clean`；不经 Published Skills 路由 | 单个 source 被报告为 planned、removed 或 preserved；任何 root-owned 状态不变。 |

## 5. 用户心智模型

1. **根是协议解释边界**：`/` 表示 doctidex 根，不是宿主文件系统根。
2. **安装与入口分开**：install path 由工具稳定分配且被宿主 Git 忽略；external link 是
   用户选择、可追踪的相对 symlink，二者都可由原生文件工具读取。
3. **source selector 与读取 commit 分开**：branch/tag 记录调用输入，install 始终固定
   到 resolved commit；省略 revision 时默认分支只作为首次解析来源。
4. **固定 selector 决定安装 identity**：owner root、canonical source 与 normalized fixed
   selector 形成稳定 key；省略 revision 的 default provenance 用于后续 lookup，具体 physical
   key 是否额外区分该 provenance 由 Impls 定义。
5. **依赖在宿主根扁平展开**：`--dependency-of` 只建立有限关系边，不在 install 内递归；
   dependency-only install 不恢复，direct install 才进入清单。
6. **safe/unsafe 不是信任或权限**：它们只描述协议严格规则是否获得例外。
7. **读取与写入现场分开**：受管 external path 是逻辑只读入口；当前仓库可直接维护，
   需要隔离时再进入 selected root 下的受管 worktree。
8. **CLI 状态不是协议事实**：未受管路径仍可有效，损坏 mapping 也不自动使目录树不符合。
9. **恢复依赖版本化清单**：restore 只重建 direct install 的 exact path/commit，不刷新 ref，
   也不修改既有 link。
10. **安装快照中的 link 可以尚未展开**：install 内版本化 external symlink 的物理 target
    可以不存在；link-parse 从 portable mapping 给出外层依赖路径或安装 facts，不在只读
    install 内递归恢复。
11. **跨根没有总事务**：每个根独立验证、审阅、保存和交付。
12. **共享 cache 不从 root 推断存活性**：清理只依据目标 bare repository 的 Git worktree
    metadata；任何有效或无法安全分类的 linked worktree 都令 source cache 保留。

## 6. 责任与非责任

doctidex-git 负责：

- 解释并确定性校验协议 `v1.0.0` 的可观察结构；
- 把一个 Git commit 安装到稳定的 `/.doctidex` 内逻辑只读路径，使载荷不被宿主 Git 追踪；
- 按 source selector 隔离 install，并把从 install 发现的依赖与环状关系扁平限制在 owner root；
- 保存可版本化恢复清单，并在载荷缺失时按 exact commit/path 重建；
- 创建可由宿主 Git 追踪、恢复后无需改动的相对 symlink 入口；
- 为主仓库受管路径和 install 内 portable link 提供 owner/content root、source、revision、
  commit、target state 和 repository-relative path；
- 为显式 revision 在 selected root 的 `/.doctidex` 下创建、列出和安全关闭扁平 maintenance worktree；
- 为 human/program operator 提供显式、离线且受 Git worktree metadata 保护的单 source
  shared bare cache 清理；
- 提供 bounded JSON、可行动失败和不泄漏 credentials 的输出。

doctidex-git 不负责：

- 生成 index/log prose、link label、内容摘要或语义结论；
- 替代 read、search、editor、`git status`、`git diff`、commit、push 或 merge；
- 把实现管理状态提升为协议要求、信任判断、访问控制或维护授权；
- 自动跟随 remote branch、自动创建交付 branch 或自动丢弃 dirty 结果；
- 由 close、restore、install 或普通读取隐式回收 shared source cache；
- 为跨 repository 工作制造原子提交或自动决定依赖顺序；
- 强制 agent 使用 doctidex-git 的 install/worktree，而排除原生或第三方工作流。

## 7. 设计来源与实现状态

本设计由 [DX-REQ-0008.1](../../requirements/0008-doctidex-git-v1-0-0-alignment/01-doctidex-git-alignment.md)
确定，依赖协议 [DX-REQ-0005](../../requirements/0005-protocol-v1-0-0.md)。Python 实现、
测试和 Published Skills 的切换由
[DX-REQ-0008.2](../../requirements/0008-doctidex-git-v1-0-0-alignment/02-python-details-and-implementation.md)
承接。
