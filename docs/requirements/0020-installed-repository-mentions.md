# 需求 0020：installed repository 的可读提及与消歧

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0020` |
| 状态 | `approved` |
| 日期 | 2026-08-04 |
| 来源 | 用户提出优化用户与 agent 协作时对 installed repository 的“提及”策略：当前看起来只能以 `install-id` 指定，而该标识不适合记忆或在对话中引用。随后明确主要以 Git source URL 的 repository path（如 `Viennan/wiki`）加可选 tag、branch 或 commit hash，或以 external link path 提及；agent 结合上下文补全并报告多候选，必要时使用 `link-parse`；命令行提供基础查询，且 Skill 指引只处理 doctidex managed install。实现后用户进一步指出，提及本质是 agent/user 高频使用的只读共用能力，起初要求以独立章节说明并由 Read 和 Maintenance 共同使用，随后进一步决定应抽为专门的 Published Skill。 |
| 影响范围 | doctidex-git Architecture、CLI/JSON contract、Python Impls 与实现/测试、Published Skills，以及 Requirements navigation。 |
| 协议关系 | doctidex-git 产品的 installed repository 选择与协作体验；不改变 [doctidex 协议](../../spec/overview.md)。 |

## 1. 已核对的现状与意图

当前 `INSTALL_ID` 是 selected owner root 内稳定但不透明的 install 标识。`external remove` 只能以一个
`INSTALL_ID` 选择 direct 或 dependency install；`external restore --install` 也以它过滤。省略
`--install` 的 restore 会分页返回 recovery manifest 中的 direct install，但它是恢复操作的结果，不是为用户和
agent 提及仓库而设计的查询或消歧 surface。dependency-only install 不在该无 filter 集合中。

已知 presentation 或 payload path 时，`external link-parse PATH` 能返回相应 `install_id`、sanitized
`source_url`、selector、fixed commit 和 role；但调用方须先知道一个可用路径。提出此需求时，命令表没有 installed
repository 的专用发现/列举接口，也没有把用户可读名称解析为 selected owner root 内 install 的契约。因此 agent
在跨轮对话中难以可靠地根据“那个仓库”或可读的 repository 名称重新定位目标，用户也不应被要求记忆或手工输入
opaque ID。

本需求的目标是形成可审阅的“提及 -> 上下文补全/查询 -> 消歧 -> 精确目标”工作流。它不要求 CLI 解析任意自然
语言，也不把 `install_id` 改成用户可读的可变名称；它须让 agent 能将用户的可读提及转换为 selected owner root
内可验证的候选，再在唯一或经用户确认后进行后续操作。

## 2. 待设计的协作语义与边界

用户与 agent 的主要提及方式是自然语言中可识别的 `REPOSITORY_PATH`，即 Git source URL 中 repository 的路径部分。
例如 `git@github.com:Viennan/wiki.git` 通常提及为 `Viennan/wiki`，而不是完整 Git URL、host/domain、scheme、
credential 或 `.git` 后缀。用户可以在需要精确选择 fixed snapshot 时附加 tag、branch 或 commit hash；无需为这类
句子规定严格 token 格式、URL spelling 或引号规则。该形式表达 repository source 的人类线索，而非直接等同
`install_id`、payload path 或一个跨 root 的全局名称。由 agent 结合当前对话、用户指令、已回显的候选、最近操作与
可用 presentation path 补全其含义；无法从这些事实证明唯一对象时，必须查询并报告候选，不能把自然语言的模糊性
隐藏为自动选择。

产品需要定义 root-scoped 的 installed repository discovery/resolve workflow，以支撑上述自然语言提及。基础 CLI
查询须只读、只观察明确 selected owner root 的 doctidex managed install，并可让 agent 以 `REPOSITORY_PATH`、可选
host/domain 线索和 tag、branch、commit 等精确条件缩小候选。查询结果应提供足以让用户辨认和比较 fixed snapshots
的无 credential 事实：可读 source identity（包含必要时的 host/domain）、repository path、revision selector、
resolved commit、direct/dependency role、managed state 与可用 presentation path（若有），并回显精确执行所需的
opaque identity。同一 repository path 来自不同 host/domain 时必须作为不同候选呈现，不能假定其相同。查询不枚举或
猜测普通 filesystem repository、原生 Git worktree、submodule、未受管 clone 或 remote 上尚未安装的 repository。

agent 接到 `REPOSITORY_PATH`、附带 revision 的提及、presentation path 或上下文线索时，必须先在明确 selected
owner root 的 managed install 中补全和发现候选。零候选、多个候选、损坏状态或 reference 不能证明唯一对象时，结果
必须给出可读候选/诊断并要求澄清；不得按最近安装、模糊 URL、当前工作目录或不透明 ID 的局部匹配静默猜测。root
间相同 source 或 selector 仍是不同 install scope，不能跨 root 复用提及。

external link path 是另一种直接提及方式。用户给出完整的 presentation path、link 自身或其内部实际目录时，agent
可在需要 source、revision、install、target state 或 owner-root facts 的任务中直接运行既有的只读
`external link-parse PATH [--root ROOT] --json`；普通本地读取不必为了提及本身重复解析。`link-parse` 只接受实际存在
的可读目录或 symlink，broken symlink 也以 symlink 自身为输入；它不是不完整 path 的模糊搜索器。agent 仅在结果证明
`managed: true` 后将其作为 doctidex managed external mapping 处理，并依据 mapping origin 和 target state 区分 current
owner install、missing owner install 与尚未在 owner root 展开的 portable dependency，绝不把后者或 unmanaged path 伪装为
已选择的 managed install。

用户也可能只给出 external link 的不完整 spelling。agent 应先在已知任务上下文中补全候选，例如用户指向或当前正在
处理的文件中的 Markdown/link target、使用该 link 的相邻文件、负责该范围的附近 `index.md`，以及 `external list`
回显的 `presentation_paths`。它只可阅读完成当前任务所需的相关文件和已选择 owner root；不得为猜测 link 而对无关
目录作不受限扫描。补全后必须得到唯一的实际 path 才能调用 `link-parse`。没有候选、多个候选、文件/配置不一致、
`link-parse` 返回 unmanaged/damaged 或 portable dependency 未展开时，agent 报告可读 evidence 并向用户请求澄清或
下一步授权，不创造 path、mapping 或 install。

解析成功后的任何现有安全、授权与生命周期边界继续有效：agent 仍须核对 fixed commit、role、presentation/reference
protection 和操作所需的用户写入或网络授权。需要精确 install target 的内部或既有 CLI contract 可以继续使用
`install_id`，但 agent 不应要求用户记住它；它应由已定义的发现/resolve surface 取得，或在结果中作为可审阅的
machine identity 回显。新的提及机制不得暴露 source credential、cache/lock/runtime 私有细节，亦不得使 mutable
branch 名称在未重新确认的情况下改写固定 snapshot 的语义。

本 draft 不要求用户创建、保存或记忆 persistent alias。Architecture 应据此定义 `REPOSITORY_PATH` 从现有 source
identity 的可读呈现、宽松匹配和 host/domain 消歧边界、tag/branch/commit 附加条件、上下文可补全的事实范围、查询
过滤/排序/分页与候选呈现；并落实下述 CLI contract。无论采用何种 surface，都必须使 destructive/selective 操作的
唯一 target 与实际执行前审阅的对象一致。

## 3. CLI 接口设计

为满足基础查询需求，本 draft 提议新增只读查询命令：

```text
doctidex-git external list [--root ROOT]
  [--repository REPOSITORY_PATH] [--host HOST]
  [--commit COMMIT | --tag TAG | --branch BRANCH]
  [--role direct | --role dependency]
  [--limit N] [--cursor TOKEN] [--json]
```

省略所有 filter 时，`external list` 分页返回 selected owner root 的全部 doctidex managed install，包含 direct 与
dependency 记录；它不是 `external restore` 的 dry-run 变体，也不读取 remote 或 filesystem 中未登记的 Git
repository。`--repository` 接收 source URL 的 repository path 线索，例如 `Viennan/wiki`；它不是完整 URL input，
不要求 host、scheme、credential 或 `.git` 后缀。`--host` 是可选的 source-host 消歧条件，而不是通常必填的提及
部分。具体的宽松 path/host normalization 由 Architecture 定义，但同一请求必须 deterministic，且不能把无关 path
误当作唯一 match。

`--tag` 和 `--branch` 以已记录的 `revision_selector` kind/value 过滤，不重新解析 moving ref；`--commit` 以已记录的
`resolved_commit` 过滤，沿用现有 CLI 对完整 commit object ID 的要求。`--role` 可重复，重复值去重并构成允许 role
集合；省略时两种 role 均包含。repository/host/revision filter 与该 role 集合相交。命令不接受 `--dry-run`、
`--apply`、`--install` 或自然语言句子，不执行 network、Git mutation、source resolution、
install/restore/remove/link/rebind/unlink，也不将 list result 隐式传给其他命令。

空匹配是 `status: ok` 的空 `items` collection，不是 selection failure；多个 matching item 同样是成功的查询结果。
agent 根据 items 结合对话选择唯一 install 或向用户报告候选，不能将多候选视为 CLI 已经替其完成消歧。root selection、
JSON syntax error 和无效 filter 继续遵守现有 common envelope/error contract。

`external_list` 的 JSON result 在公共 envelope 外提供 `query` 与 `items`：

| 字段 | 类型与含义 |
|---|---|
| `operation` | 固定 `external_list`。 |
| `query` | 回显规范化后的 `repository_path`、`source_host`、`revision_selector`、`resolved_commit` 和 `roles`；未指定 filter 使用 null 或空 array。 |
| `items` | 当前页 `InstallReference` 数组；`collection.lists.items` 给出完整匹配集合的分页事实。 |

每个 `InstallReference` 必须包含 `install_id`、sanitized `source_url`、可为 null 的 `source_host`、`repository_path`、
`revision_selector`、`resolved_commit`、`install_role`、`managed_state` 与 `presentation_paths`。`presentation_paths`
是该 owner root 中仍指向该 install 的 root-relative managed presentation target 的稳定排序数组；没有 presentation
时为空。结果不得暴露 credential、cache、lock、内部 payload path 或其他 private runtime details。它按
`(repository_path, source_host, revision_selector kind/value, resolved_commit, install_id)` 排序；cursor 绑定 operation、
selected root、规范化 filter、limit 和足以拒绝 stale continuation 的 observed managed-record state。相关记录变化时，
后页返回 `cursor_invalid`，不能静默重启或混入新旧候选。

`external list` 只负责发现和事实回显。现有 `external remove INSTALL_ID`、`external restore --install INSTALL_ID` 与
`external install --dependency-of INSTALL_ID` 继续维持其精确 ID input；agent 在使用它们前可先 list、向用户回显
`InstallReference` 并将已确认 item 的 `install_id` 传入。此 Requirement 不在 CLI 层接受自然语言提及，也不改变
现有 destructive/selective command 的参数语法。

现有 `external link-parse PATH [--root ROOT] [--json]` 不增加 fuzzy-path 参数、pagination、`--dry-run` 或 `--apply`。
它仍是单个已物化 path 的事实查询；本需求只规定 agent 何时用它解释 external link 提及，并要求 `external list` 的
`presentation_paths` 可以支撑不完整 path 的候选补全，而不把补全机制下沉为 CLI 的文件系统搜索。

## 4. 实施影响

获得实施授权后，先使用 Architecture authoring workflow 将上节 `external list` CLI/JSON contract 与
`REPOSITORY_PATH` 提及、可选 revision、host/domain 消歧、上下文补全、root 绑定、ambiguity/failure、授权和隐私边界
一并定义，并说明它如何与 direct/dependency install、restore、remove、link-parse 和 presentation 生命周期相互作用。
Architecture 还须定义 external link 完整/不完整 path 提及的 agent-side evidence boundary、`link-parse` invocation 和
portable dependency distinction。随后使用 Impls workflow 规定 Python 查询、source/revision normalization、候选排序/分页、
presentation-path materialization、状态读取、cursor identity、兼容迁移及 source/test evidence。

CLI/JSON、Python implementation 和测试必须实现该 read-only query/resolve contract。Published Skill system 必须以
专门的 `doctidex-git-mentions` Skill 拥有这项高频只读交互，而不是把它放在 Overview 或分散到 Maintenance 的附属步骤。
该 Skill 负责上下文补全、唯一性/消歧、root scope、无状态创建和 managed-only 边界，并持有 `external list` 与
`external link-parse` 的提及场景 command guidance。Overview 只路由；Read 与 Maintenance 在遇到提及时加载该 Skill，
取得结果后回到各自的阅读或维护工作流，不能复制或重新定义共同策略。

Published Overview、Maintenance 与 Read Skills 应说明：只对 doctidex managed install 使用这套提及与
`external list`；agent 在回答或执行前结合上下文发现并回显可读候选，以用户确认的唯一 target 继续。它们还应区分完整
external link path 的按需 `link-parse` 与不完整 path 的 context-first candidate completion；后者不允许无关目录扫描或
猜测。对普通 repository、原生 Git worktree、submodule 或未受管 clone 仍使用各自原生方式，不能伪称为该产品的
managed install。Skills 不得让用户提供或长期记忆 opaque `install_id`，也不得把 `external list` 或 `link-parse`
描述为自然语言解析器或非受管 repository discovery。
上述 CLI/Skill design 现已实现：`external list` 是当前 runtime-only、offline、read-only 查询接口；提及解析由
专门 Published Skill 承担，不改变既有 lifecycle command 的精确 ID 参数。

## 5. 验收标准

1. 用户和 agent 可主要以 Git source URL 的 `REPOSITORY_PATH` 提及 doctidex managed install；例如
   `git@github.com:Viennan/wiki.git` 可以提及为 `Viennan/wiki`，无需提供完整 URL 或 host/domain。在需要选择精确
   fixed snapshot 时，可附加 tag、branch 或 commit hash，且该对话语义不强制严格的文本格式。
2. 用户可直接以完整 external link path、link 自身或其内部实际目录提及 doctidex managed external mapping；需要其
   source/revision/install/target state facts 时，agent 使用既有只读 `external link-parse`，并依据 managed、mapping
   origin 和 target state 处理结果，不把 portable 未展开 dependency 或 unmanaged path 当作 current managed install。
3. 用户只给出不完整 external link path 时，agent 仅结合任务相关文件中的引用、附近 `index.md`、当前上下文与
   `external list` 的 `presentation_paths` 补全候选；得到唯一的实际 path 后才调用 `link-parse`。零/多候选、损坏或
   不一致必须报告 evidence 并请求澄清，不得扫描无关目录、猜测或创建 mapping/install。
4. 在明确 selected owner root 中，agent 可结合当前上下文和定义的 read-only query/resolve workflow 找到 direct
   与 dependency managed install，而不要求用户提供 `install_id` 或已知 presentation path。
5. query result 使用无 credential 的可读 source、revision/commit、role、managed state 和 presentation 等事实区分
   候选，并同时回显与精确执行兼容的 opaque identity。
6. 仅在唯一匹配时，agent 才可把用户或 agent 的提及解析为具体 install；零候选、多候选、损坏或跨 root 情形必须
   报告候选或诊断并要求澄清，绝不静默选择 install。
7. query/resolve 只观察 selected owner root 的 doctidex managed install；不将普通 repository、原生 Git worktree、
   submodule、未受管 clone 或 remote repository 纳入候选，也不泄露 credential 或私有 runtime/cache/lock 细节。
8. CLI 提供 `external list`，其 `--root`、repository path/host/revision/role filter、无 filter 全量分页、只读无网络
   边界、空/多候选结果、稳定排序、cursor invalidation 与 JSON envelope 均符合本记录的 CLI 接口设计。
9. `external_list` item 在不泄露私有路径或 credential 的前提下，回显 source/repository path、revision/commit、role、
   managed state、presentation paths 和 opaque `install_id`；direct/dependency、有/无 presentation、hidden、单/多/零
   候选与跨 host 同 path 都有测试证据。runtime 损坏按 common error contract 返回可诊断的 blocked，不伪造 item；该
   runtime-only query 不依赖 recovery manifest。
10. 在 remove、restore filter、dependency parent、link/rebind source 或其他需精确 installed repository 的流程中，
    agent 能先以该工作流获得并审阅 target；现有 `install_id` 输入和已保存的 manifest/runtime records 继续兼容。
11. Published Skill system 提供专门的 `doctidex-git-mentions` Skill，拥有 repository path 与 external link path 的
    高频只读提及、上下文补全、候选回显、消歧、root/managed-only 和无状态创建边界；Overview 路由，Read 与 Maintenance
    明确加载后返回各自工作流，不复制或重新定义共同策略。
12. Published Skills 明确这套提及仅适用于 doctidex managed install，并说明 repository path 与 external link path 的
    上下文补全、按需查询、候选回显和用户消歧责任；不把该工作流扩展为一般 Git repository 发现或操作指导。
13. Architecture、Impls、CLI/JSON、Python implementation、tests 和 Published Skills 一致说明并验证 repository path 与
    external link path 提及、optional revision、host/domain collision、context completion、link-parse、discovery、唯一解析、
    ambiguity、dependency、root isolation、损坏/中断、隐私和向后兼容情形。

## 6. 进展与依赖

本记录依赖已批准 [DX-REQ-0008](0008-doctidex-git-v1-0-0-alignment/overview.md) 的 fixed install、owner root 和
manifest/runtime 基础模型，并与已批准 [DX-REQ-0019](0019-nearby-external-link-rebinding.md) 的 presentation 和
`link-parse` 生命周期衔接。两份均为 `approved` 历史，尚未获得修改其内容以添加 reciprocal link 的授权；本
Requirement 暂保留上述单向关系。取得授权后，应分别在两份历史记录中加入指向本记录的后续需求链接，或由用户
选择其他历史关联方式。

已核对 current Architecture 的 CLI/JSON contract、Python `ExternalService` 与 `test_git_plugin.py`、Published
Overview/Maintenance/Read Skills。确认 `install_id` 是 root-scoped opaque identity；restore 可列举 direct recovery
records，但 remove/filtered restore/dependency parent 仍接收 ID，且 `link-parse` 需要已知 path。实施前，产品未定义以
Git source URL 的 repository path（例如 `Viennan/wiki`）和 optional revision 为主的用户/agent 提及、专用基础
query/resolve surface 或其上下文补全和消歧规则。用户已明确该提及只覆盖 doctidex managed install，不扩大为一般
repository naming/discovery。为满足用户所需的基础查询，本 draft 提议只读 `external list` 使用 repository path、
可选 host/revision/role filters 列举 selected owner root 的 direct/dependency managed install，以公开候选事实支撑
agent 消歧；现有 exact `INSTALL_ID` commands 不接受自然语言 input，且不在本次设计中改变。

用户进一步确认 external link path 也是直接提及方式：完整实际 path 在任务需要事实时由既有 `link-parse` 解释；
不完整 path 由 agent 在相关文件、附近 `index.md`、上下文和 returned presentation paths 中补全。该补全不改变
`link-parse` 的 exact-path contract，也不授权无关范围扫描、mapping/install 创建或将 portable 未展开 dependency 伪作
current managed install。

用户已明确授权实施本 Requirement。实现已先更新 doctidex-git Architecture 与 Python Impls，再交付
`external list` CLI/JSON、Python runtime-only 查询、direct/dependency/hidden/presentation/filter/pagination/stale cursor
与同路径跨 host 测试，以及 Published Overview/Maintenance/Read Skills 和 external command reference。实现对 URL
优先、SCP-like 后备解析 source host/path，避免 `ssh://...` 被误作 SCP spelling；既有 `link-parse` 仍保持 exact-path、
offline、read-only contract，且以 `INSTALL_ID` 为目标的 destructive/selective command 保持兼容。

验证已完成：`.venv/bin/python -m pytest impls/libs/python/tests` 为 `48 passed`，
`.venv/bin/python -m ruff check impls/libs/python` 通过，`git diff --check` 通过；并以
`.venv/bin/doctidex-git validate . --scope ... --json` 分别验证 Architecture、Python Impls、Requirements 和
doctidex-git Published plugin，全部无 finding 或 semantic candidate。本记录现为 `implemented`，等待用户明确
接受后方可更新为 `approved`。另行运行的全根 validation 仍报告 `.asserts`、`.github` 和 `.tmp` fixture 下既有的
非本记录范围结构 finding；本次未改动这些路径，受影响 scope 的 validation 结果保持通过。

用户反馈曾将本记录从 `implemented` 返回 `draft`：现有提及说明分散在 Overview 的术语和两个 specialist 的重复段落，
不利于作为 agent/user 高频只读能力复用。现已在 Published Skill system 与 Overview 新设独立 shared mention
capability 章节：Overview 拥有高频只读交互、上下文补全、root/managed-only、candidate/ambiguity 与授权边界；Read
仅处理 task-local external-link evidence 和 exact `link-parse`，Maintenance 仅处理 owner-root `external list`、
candidate 比较和向已获授权 command 交付 exact ID。两项 specialist 不再重新定义共同策略。

这项重组已重新通过 Architecture、Requirements 和 doctidex-git Published plugin 的 scoped validation，以及
`git diff --check`；CLI/Python 行为和先前完整 Python test suite evidence 未变化。本记录恢复为 `implemented`，
仍等待用户明确接受后方可更新为 `approved`。

用户再次反馈使本记录重回 `draft`：共享章节仍使 Overview 承担了跨读/维护的实际提及工作流，Skill 架构不够自然。
已据此新增 `doctidex-git-mentions` Published Skill，使它成为 read-only mention 的唯一 owner，并将 `external list` 和
`external link-parse` 的提及场景 command guidance 迁入其直接 reference。Overview 只保留路由；Read 与 Maintenance
在遇到 repository path 或完整/不完整 external-link path 时加载 Mentions，接收 candidate、exact path 或诊断后回到原
阅读或维护流程。Maintenance 的 remove guidance 也不再直接调用 `link-parse`；ID 未知时先路由 Mentions。列表候选只有
返回的 presentation path 被验证为实际存在时，才可作为后续 link-parse 或原生阅读的输入，禁止推测 private payload path。

当前 Architecture 已将 Published Skill 系统改为四个稳定入口，并在 product user surface 中将 repository/external-link
提及显式路由至 Mentions。Python/CLI/JSON、Impls 与测试维持此前已实现的 `external list` contract；本次专门 Skill
重组未改变其运行时行为。最终验证结果如下：

- `.venv/bin/python -m pytest impls/libs/python/tests`：`48 passed`；
- `.venv/bin/python -m ruff check impls/libs/python`：通过；
- `quick_validate.py` 验证 `doctidex-git-mentions`：通过；
- `validate_plugin.py` 验证 doctidex-git plugin：通过；
- 对 Architecture、Requirements 与 Published plugin 的 scoped `doctidex-git validate`：均无 finding 或 semantic candidate；
- `git diff --check`：通过。

用户已明确接受当前实现，本记录现为 `approved`。
