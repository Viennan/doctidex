# 已发布 Skill 系统

本篇只设计三个 Published Skills 的职责、阅读链、命令说明充分性和用户/内部信息边界。
产品工作流以 [Architecture system](index.md#系统与-workflow)为准，精确 public command contract 由
[CLI](interfaces/cli.md) 和 [JSON Schema](interfaces/cli-schema.md) 负责；Skill 应完整转述 agent
完成任务所需的信息，但不能成为另一份 Architecture 权威。

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

## 2. 阅读链

```text
选择专项 Skill
  -> 尚未加载 Overview？只加载一次
  -> 返回已选择的专项 Skill
  -> 仅在任务确实跨越工作流边界时路由到另一个专项 Skill
```

Overview 只向专项 Skill 路由，不反向要求重读；专项之间不能互相形成强制循环。已加载的
Overview 在同一任务中不重复打开。Overview 加一个相关专项 Skill 必须足以完成单一受支持
场景。

## 3. 已安装产品措辞

Published Skills 面向已安装产品，不能要求 agent 阅读本仓库源码、Architecture、Impls、
tests、repository-local path 或开发命令。当前三个 Skills 只引用 `1.0.0` 安装后可用的命令
和用户路径；未来也不得先于对应命令实现发布目标 Skill 文本。

## 4. 命令充分性

每个被 Published Skill 引入的命令都必须写明：

- 精确 invocation、参数类型、必填/可选/互斥关系；
- 省略行为、cwd/ROOT 选择和嵌套根歧义；
- read/write/network、dry-run/apply 与生命周期效果；
- selector、default branch provenance 与固定 commit 的区别；
- install 无 target、稳定 `/.doctidex` 路径、payload Git ignore、可版本化 manifest、可追踪
  relative symlink，以及 restore 不改 link 的区别；
- install key 由 root/source/normalized fixed selector 组成；default provenance 供后续省略调用
  lookup，physical key 细节由 Impls 定义；`--dependency-of`
  表示从哪个 install 发现依赖，dependency 扁平、不递归、不进 manifest，环命中既有 key
  即停止，建立 durable link 前需提升为 direct；
- worktree open 对所有 source 选择 owner root，并把现场扁平放在其 `/.doctidex`；list 以
  root 为范围，close 只处理 exact managed path；
- agent 决策所需字段、默认 limit、cursor 和过滤方式；
- validate 的可重复根绝对 `--scope`、省略时全根、规范化/去重规则、必要支持闭包，以及
  scoped pass 不能作为全根符合结论；
- restore 的 filter、bounded collection、dry-run/apply、exact commit 与 cursor identity；
- remove 的单一 `INSTALL_ID`、dry-run/apply、reference block 与证据、reference-free 的有限
  payload/metadata effect、shared cache 不变，以及 ID 不明时先 link-parse；
- link-parse 的 PATH 输入、owner/content root 区别、current-owner/installed-repository mapping、
  target state，以及 broken symlink 不需要 target 存在；
- 常见 blocked code、保留结果、恢复动作和需要用户输入的边界。

Overview 与专项 Skill 合起来不得要求 agent 通过 `--help`、错误试探或实现文档补全语法。
该充分性要求覆盖 Skills 实际暴露的命令；已安装 CLI 可以另有未被 Skills 路由、但仍由
Architecture 和 CLI/JSON schema 稳定定义的 human/program 管理命令。当前唯一这种命令是
`cache clean`。

## 5. Read 的不可访问 Symlink 引导

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
5. 已不需要某个 managed install 且已获删除授权时，先从 link-parse 或之前的 result 取得 exact
   Install ID，dry-run remove 并阅读 reference evidence；出现 blocked reference 时回到用户决定，
   不让 Skill 自动删除文档、symlink、mapping 或 dependency edge。

“优先”表达默认建议，不是禁止隔离；“受管”表达产品承诺，不是协议符合性或工具排他性。

## 7. 用户界面与内部信息

Skill 应暴露：direct/dependency 区别、parent install ID 输入、selector 隔离、fixed commit、
root-internal install/worktree path、manifest inclusion、symlink 可恢复性、read/write/network
效果、mapping origin、owner/content root、target state 和下一步。Skill 不暴露：宿主
`.git` 快速路径、object store 共享、install key 编码、portable mapping 查找算法、
环检测数据结构、cache cleanup、record/lock/storage 布局。自依赖只需说明返回独立只读快照，不会折叠到
当前可写 working tree；实际 objects 来源由 CLI 的 network 与 source relation facts 表达。

## 8. 原生工具与客观性

Skills 保留 agent 的原生文件、搜索、shell、编辑和 Git 工具自由。CLI helper 只增加
doctidex/Git 交叉处无法可靠从普通工具直接得到的事实。CLI 确定性且不调用 AI；agent
负责语义内容、任务相关性、unsafe 范围是否合适、diff 质量和交付决定。

## 9. 输出与失败

Skill 默认使用精确 ROOT、PATH、SOURCE 或 WORKTREE；validation 只在任务确实聚焦
部分目录时使用 scope，并先读 coverage/scopes 与 collection 统计再分页，不得习惯性提高
limit。失败步骤必须说明 operation、affected、preserved result、下一动作
与 `requires_user`；credentials、network、revision、link target、manifest/Git tracking、
dirty worktree 和 Git
交付决定不能用无限重试代替用户输入。

## 10. 发布验证

每次 Skill 或 metadata 变化都验证 frontmatter、`agents/openai.yaml`、无环阅读链、命令
契约、用户/内部信息边界、bounded output 和 containing plugin。复杂工作流需用只含公开
artifacts 的独立 agent forward test，不能泄漏预期 finding 或修复。
