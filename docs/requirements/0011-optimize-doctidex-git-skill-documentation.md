# 需求 0011：优化 doctidex-git Skill 文档内容

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0011` |
| 状态 | `approved` |
| 日期 | 2026-08-02 |
| 来源 | 用户要求创建“优化 doctidex-git skill 文档内容”的新需求骨架，并确认 Maintenance Skill 的结构化注释引导与 external install 的环状依赖说明为本次重点；实施后又要求在主 Skill 增加少量启发性的环状引用决策提示。 |
| 影响范围 | doctidex-git Maintenance Skill、其 external command reference，以及相应 Published Skill 验证。 |
| 协议关系 | 非规范性 agent 文档改进；当前未授权修改 [`doctidex` 协议](../../spec/overview.md)、doctidex-git CLI/JSON contract 或实现行为。 |

## 1. 已记录意图

优化 doctidex-git 已发布 Skill 文档的内容，使目标 agent 能更准确、清楚地理解并执行当前产品
workflow。用户已确认以下两项内容改进：

1. Maintenance Skill 应在 agent 使用 native edit 创建或修改 Markdown link 时，主动提示检查
   doctidex 结构化 link 注释，而不是只在 validation 报错后才补救。安全文档的非 `index.md`
   跨界 link 需要标记首次 `cross-boundary-point`；安全文档指向 unsafe 路径的 link（包括
   `index.md`）需要显式 `unsafe: true`。两种条件同时成立时使用同一个相邻的 doctidex 注释。
2. Maintenance 的 external install 说明应突出：调用方可用 flat dependency relation 表达环状
   dependency，包含 owner/host repository 自引用；相同 install identity 命中时环路保持有界，
   自引用仍是独立的只读 snapshot。

这两项都是既有协议与产品能力的 agent 引导，不引入自动依赖发现、嵌套 managed state、可写
self snapshot 或新的 CLI 行为。

相关 current-artifact authority：

- [Published Skill system](../doctidex-git/architecture/skill-system.md)；
- [doctidex-git Overview Skill](../../impls/agent-plugins/doctidex-git/skills/doctidex-git-overview/SKILL.md)；
- [doctidex-git Read Skill](../../impls/agent-plugins/doctidex-git/skills/doctidex-git-read/SKILL.md)；
- [doctidex-git Maintenance Skill](../../impls/agent-plugins/doctidex-git/skills/doctidex-git-maintenance/SKILL.md)。

## 2. 已确认的设计范围

以 `doctidex-git-maintenance` 为主入口，并修订其
[external command reference](../../impls/agent-plugins/doctidex-git/skills/doctidex-git-maintenance/references/external.md)。
Maintenance 应把结构化注释视为 agent 在撰写 safe 文档 link 时应完成的协议写作动作，清楚区分：

- `external link` 会维护 responsible index 的 `boundary-set`/`unsafe` frontmatter，但不会生成
  Markdown navigation prose 或其相邻注释；
- `index.md` 可从有效 `boundary-set` 推导跨界点，故仅因跨界不需要
  `cross-boundary-point`；safe-to-unsafe 仍必须声明 `unsafe: true`；
- 不应为普通 safe 的非跨界 link 添加无意义注释，也不应重写现有注释只为阅读内容。

external reference 应将环状 dependency 与 self-reference 作为 explicit install workflow 的可用
能力说明，而非对其他工具作未定义的比较性承诺。它必须同时保留当前限制：CLI 不会递归发现或
安装 dependency；dependency 只在 outer owner root 中以 `--dependency-of` 建立，且若要创建
durable link，仍须先提升为 direct install。

## 3. 预期实施影响

1. 修改 `impls/agent-plugins/doctidex-git/skills/doctidex-git-maintenance/SKILL.md`，在不把
   Maintenance 变成通用写作教程的前提下，加入结构化注释的前置检查与正确边界，并以简短启发
   提示 agent 在已知 dependency 指回 owner/host repository 或形成环时考虑 external install 的
   flat、independent snapshot 模型。
2. 修改其 `references/external.md`，使读者在选择 install/dependency workflow 时能发现
   cycle/self-reference 的有界、独立 snapshot 行为和 direct-promotion 限制。
3. 使用现有 Published Skill、Architecture、Python Impls、实现和测试作为事实依据。现有
   Architecture 已说明 link 不生成通用 Markdown prose，且 Published Skill/human workflow 负责
   该语义导航编辑；本次仅使已发布文档表述与该边界一致，不改变 current Architecture 或
   Python Impls 的事实。
4. 使用 Published Skill authoring authority 检查 trigger、reading chain、命令契约、失败引导、
   metadata、交叉链接和 containing plugin；按其要求运行公开 artifacts 的 forward test。

## 4. 验收标准

1. Maintenance 在 agent 撰写 safe 文档 link 的场景中，能在 validation 之前说明何时需要
   `cross-boundary-point`、`unsafe: true`、两者组合或无需注释，并保留 index 与既有注释的
   正确例外。
2. `external link` 更新 index frontmatter、agent 负责 Markdown navigation 与相邻注释的责任边界
   清楚且不冲突；修订内容不暗示 CLI 会自动撰写或修复任意文档 link。
3. external install guidance 明确说明环状 dependency 和 owner/host self-reference 的有界
   independent snapshot 语义，以及 flat outer-owner relation、无自动递归、dependency-to-direct
   promotion 的限制。
4. Maintenance 主阅读路径以简短、非比较性的方式提示上述场景可考虑 external install，并保留
   native Git 或不需要受管 presentation 时无需采用该 workflow 的边界。
5. 修订后的阅读链、command contract、metadata 和内部链接有效，并通过 Published Skill 所需的
   frontmatter、无环阅读链、公开 artifact forward test 和 containing plugin 验证。
6. 未经后续明确授权，不修改协议、CLI/JSON contract、Python implementation、测试或独立的
   current Architecture/Impls 事实。

## 5. 进展与依赖

用户已于 2026-08-02 确认第 1 节和第 2 节的范围。协议第 8 节、Published Skill system、external
Architecture/Impls、`ExternalService` 和现有 protocol/Git tests 均支持所记录的前提：validate
可检测缺失注释，但不代替写作；`external link` 只维护 index 配置；环状 key reuse 与 self-reference
独立 snapshot 均为当前行为。

用户已于 2026-08-02 明确要求完成本 Requirement，授权范围为第 3 节所列的 Maintenance Skill 与
external reference 文档修订及其验证。不授权协议、CLI/JSON contract、Python implementation、测试或
独立 Architecture/Impls 事实变更。

实施结果：

1. `doctidex-git-maintenance` 现在在创作 safe 文档 link 时，明确说明非 `index.md` 跨界、
   safe-to-unsafe、两者叠加及普通 safe link 的注释规则，并给出完整双字段注释示例。它也明确
   `external link` 只维护 responsible index 配置，不会代写 navigation prose 或注释。
2. external reference 增加了环状 dependency 与 owner/host self-reference 的独立章节，说明 outer
   owner 的 flat relation、existing-key reuse、independent read-only snapshot、无自动递归和
   dependency promotion 后才能 durable link 的边界。
3. 未修改协议、CLI/JSON contract、Python implementation、测试或独立 Architecture/Impls；metadata
   与现有 reading chain 保持一致。

验证结果：

| 检查 | 结果 |
|---|---|
| Maintenance Skill quick validation | 通过。 |
| doctidex-git containing plugin validation | 通过。 |
| `test_protocol.py` | 9 passed。 |
| `test_git_plugin.py -k self_dependency_is_bounded` | 1 passed。 |
| 两次 fresh independent Published Skill forward test | 通过 safe/non-`index.md` 双字段注释、普通 safe link 无注释、`index.md` unsafe 例外、环状 owner/host self-reference 及 dependency promotion 场景。 |
| `git diff --check` | 通过。 |
| scoped `doctidex-git validate`（`/impls`、`/docs/requirements`） | 本次改动没有 finding；仍报告根 `index.md` 的 5 个既有 `link_annotation_invalid`，不属于授权范围。 |

没有已确认的 Requirement 依赖、细化、取代或后续关系。授权范围与验收标准均已完成，状态更新为
`implemented`；尚待用户明确接受后才可更新为 `approved`。

用户随后要求在 Maintenance 主 Skill 增加少量启发性的描述，使 agent 在 dependency 指回
owner/host repository 或形成环时能及早考虑 external install。该反馈改变已交付的 agent guidance，
故本 Requirement 于 2026-08-02 回到 `draft`。现已在主阅读路径补充简短决策提示：需要 fixed、
independent snapshot 或 durable presentation 时可考虑该 workflow；native 当前 working tree 已满足
任务或无需受管 presentation 时继续使用 native Git。

补充后的验证结果：Maintenance Skill quick validation、doctidex-git containing plugin validation、
`test_git_plugin.py -k self_dependency_is_bounded` 和 `git diff --check` 均通过；scoped
`doctidex-git validate` 仍仅报告根 `index.md` 的 5 个既有 `link_annotation_invalid`。没有新的
Requirement 依赖或未解决决定。用户已于 2026-08-02 明确接受当前实现为 PR/MR-ready，状态更新为
`approved`。
