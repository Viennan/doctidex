# 需求 0022：优化 doctidex 安装、版本与缓存指引

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0022` |
| 状态 | `draft` |
| 日期 | 2026-08-05 |
| 来源 | 用户要求优化 doctidex 安装指引，随后明确版本治理、GitHub tag、Published Skills、双语 README、`DOCTIDEX_GIT_CACHE` 的 user surface、项目最初的跨仓库知识互联愿景，以及 agent 可同时获得代码与跨平台 Published Skill bundle 的安装入口；当前指定 Python 代码版本与 `doctidex-git` 版本均为 `1.0.0`。 |
| 实施授权 | 用户于 2026-08-05 明确授权按本记录实现 README、根导航、Architecture、Python Impls、Published Skills、版本一致性验证和 cache 配置说明；GitHub tag 的创建与发布仍由用户完成。 |
| 影响范围 | 根级中英文 README、根导航及其 `/.doctidex` unsafe 声明、版本/发布校验、doctidex-git Architecture、Python Impls、Python package metadata、doctidex-git plugin metadata、四个 Published Skills、跨平台 agent bundle 安装说明、cache 配置说明和相关测试。 |
| 协议关系 | 产品版本、安装和缓存配置指引；不改变 [`doctidex` 协议](../../spec/overview.md)的目录结构、元信息、读取关系或符合性要求。 |

## 1. 已确认的意图

根级 README 当前不存在。README 应提供面向使用者的 doctidex 安装入口，明确 Python package 从代码库安装，而
不是只给出本地开发环境的 editable 安装方式。安装来源当前为 GitHub：`https://github.com/Viennan/doctidex.git`；
Python package 位于 `impls/libs/python`，分发名为 `whero-doctidex`。

当前 [`spec/overview.md`](../../spec/overview.md) 的协议版本为 `v1.1.0`，plugin metadata 和 Python package
metadata 均为 `1.0.0`。本地可见最新 Git tag 是历史的 `v0.0.2`，不能证明 GitHub 已有可用于当前 `1.0.0`
产品的 release tag。用户现已指定 Python 代码与 `doctidex-git` 的当前版本均为 `1.0.0`；本需求据此实现 README 和
Python variant 文档的 `v1.0.0` 安装 selector，但不把尚未核实的 GitHub tag 写成既成事实。

Python 已实现非空 `DOCTIDEX_GIT_CACHE` 环境变量，用它选择 shared cache root；source cache、source lock 和
diagnostic 都随之使用该 root。初始调查时该变量尚未作为产品 user surface 说明；本轮已由 README、Architecture、
Python Impls 和 Overview 的用户配置指引补齐。

## 2. 版本与发布约定

doctidex 协议、`doctidex-git` 产品和 `whero-doctidex` Python distribution 各自维护完整的语义版本号。三者的
major 版本号必须一致；minor 与 patch 可以独立演进，不得据此推断三者完整版本相同。协议版本带 `v` 前缀，
产品与 Python distribution metadata 使用不带前缀的版本号。

用户确认每次发布的版本号；agent 可以根据兼容性变更提出建议，但不得自行确认发布版本、创建 GitHub tag 或发布
release。用户在 GitHub 创建 `vX.Y.Z` tag 时，`X.Y.Z` 必须等于同一 release 的 `doctidex-git` 产品版本。该 tag
固定代码库 revision，是从 Git 安装该产品版本的唯一 selector；它不要求等于同一 revision 中 Python distribution
或协议的 minor/patch 版本。

本次实现使用 `doctidex-git` `1.0.0`、`whero-doctidex` `1.0.0` 和预期 selector `v1.0.0`。README 仍保持用户
在安装时指定 target 版本的参数化形式；Published Skills 不承载 release 信息。

面向 target `doctidex-git` 版本的安装命令必须使用 GitHub HTTPS URL、对应 `vX.Y.Z` tag 和 package 子目录：

```text
python -m pip install --no-input "whero-doctidex @ git+https://github.com/Viennan/doctidex.git@vX.Y.Z#subdirectory=impls/libs/python"
```

README 将 `X.Y.Z` 明示为用户在安装时提供的 target `doctidex-git` 版本，而不固定为 README 自身所描述的
release；agent 必须使用该输入构造对应 tag，不能选择默认分支、猜测 tag 或从 package version 推断产品 tag。

## 3. README 与 Published Skill 指引

根级新增 `README.md`（English）和 `README.zh-CN.md`（中文），两者互相链接，并说明相同的当前产品事实。它们以
简洁的使用者视角介绍 doctidex 的能力、解决的问题、适用场景和安装方式；不重述源码目录、测试、editable 开发
安装或完整开发流程，只向希望继续开发的读者提供简短的 agent-first 引导。

README 必须让一个已获得 README URL 和用户指定的 target `doctidex-git` 版本的 agent，无需人工补充 source URL、
分支或本地 repository layout，即可将该版本代入 GitHub tag 安装 package 并定位 `doctidex-git` console script。
README 不固定或推荐一个默认安装版本；它应说明兼容的 Python 前提、按 tag 安装的参数化命令和最小安装后验证，但不
把环境创建和开发工作流展开为长篇教程。根 `index.md` 必须提供到两个 README 的可达入口。

README 的安装入口同时覆盖两个独立交付物：Python distribution 提供 `doctidex-git` console script，Published
agent bundle 提供四个使用工作流。安装者选择 `TARGET_DOCTIDEX_GIT_VERSION` 后，README 应以该 GitHub tag 通过 VCS
安装 `impls/libs/python` 中的 distribution，并以相同 tag checkout repository 取得
`impls/agent-plugins/doctidex-git/skills/` 下的 bundle。由此 agent 无需另行推断 source URL、tag 或 plugin 路径。

bundle 的可移植核心是各目录的 `SKILL.md`：任意支持该 agent-skill 文件形式的 host 都可用自己的注册机制导入整个
`skills/` 目录；不具备 plugin/skill 注册机制的 agent 仍可直接读取与当前任务相符的 `SKILL.md`。`.codex-plugin`
metadata 只为 Codex 提供可选包装，README 不将其或任何 Codex 专有命令作为通用前置条件，也不虚构非 Codex agent 的
固定安装目录或 command。host-specific 注册后，agent 读取 Overview 和所选专项 Skill；Python distribution 则必须
安装在该 agent 执行 CLI 所用的兼容环境中。

README 还应以中英文整理项目最初的方向：开发者知识散落于不同 Git repository 时，应能形成可互联、可追溯的网络；
在 AI 辅助开发中，agent 需要可携带、可审阅的 repository context，以理解已提及 repository 的知识、实践和设计偏好。
Git repository 在维护明确导航和上下文后，可以成为自解释的知识库。此处是项目愿景，不承诺自动发现、汇总或注入所有
repository 的知识；当前 doctidex 以可读 index、渐进导航和固定 revision 的 external snapshot/presentation 提供可审阅
基础。README 应说明项目受 Google 的 Open Knowledge Format（OKF）启发，并链接本仓库的 OKF 参考资料；doctidex
不声明严格 OKF 格式兼容性。

Published Skill 只描述已安装产品的使用工作流。其正文不得包含协议/产品版本、Git tag、package 或运行时安装/重装、
开发、发布、tag 确认、测试或维护验证描述。版本关系、release identity、安装可用性及其后置核对由 README、
Architecture、Impls、Requirement 和相应测试负责；Skill 内容仍须随产品工作流变更保持一致。

此项细化已批准的 [DX-REQ-0017](0017-python-venv-cli-and-hook-runtime.md)：Published Skills 继续不规定 `.venv`
的位置、选择过程、创建过程、shell activation 或开发教程，也不提供 package 安装入口。`0017` 是已批准历史，
尚未取得修改它以添加 reciprocal link 的授权；本记录保留 outbound relationship，并在获授权后应在 `0017` 记录本需求
对 Published-Skill 非开发边界的细化。

## 4. Cache 配置指引

`DOCTIDEX_GIT_CACHE` 成为 Python variant 的公开可选环境变量。用户可以在调用 CLI 前将它设置为期望的可写 cache
根目录；未设置时仍使用当前平台默认路径。为避免工作目录变化造成歧义，文档应建议用户设置 absolute path。一个
需要共享相同 cache 的 CLI、自动化或 Git hook 执行环境必须继承相同的用户配置；产品不保存、同步或猜测该环境变量。

用户自行决定是否设置、设置何处以及如何让其执行环境继承该值。Published Skills 可以说明变量的作用和这一边界，
并建议由用户手动配置；agent 不得自行写 shell profile、project configuration 或其他持久环境设置。该指引不把
`cache clean` 变为 Skill 工作流，也不公开 cache 内部目录、key、lock 或诊断文件布局。

## 5. 实施影响

获得明确实施授权后，先以 Architecture authoring workflow 定义版本三元关系、Git tag identity、README 与 Published
Skill 的信息边界，以及 `DOCTIDEX_GIT_CACHE` 的用户配置、inheritance、fallback 和 privacy contract。随后以 Impls
authoring workflow 更新 Python package/platform evidence、metadata 对应关系和 source/test evidence。

实现层需要创建双语根 README 并更新根导航；使 plugin metadata、Python package metadata 与 README 的 release facts
可被一致维护，并通过后置校验检查 Published Skills 的非开发边界。cache 行为已存在，但仍需通过 user-surface 测试或
验证证明 override、默认 fallback、CLI/automation inheritance 和文档描述一致。README 保持版本参数化；只有用户创建
并确认 target GitHub tag 后，才可运行 release-specific package 安装验证。

本需求不要求发布 PyPI distribution、修改 doctidex protocol 或将当前 package、plugin、protocol 的 minor/patch
版本绑定为相同值。除 cache public contract 的必要实现/测试对齐外，不预设修改 CLI command 或现有
external/worktree lifecycle。

## 6. 验收标准

1. 协议、`doctidex-git` 和 `whero-doctidex` 的 major 版本一致，minor/patch 独立；校验能从各自权威来源验证此
   规则，而不以当前数值相等替代版本关系。
2. 用户确认发布版本并在 GitHub 创建 `vX.Y.Z` tag 后，tag 与 plugin metadata 中的 `doctidex-git` 版本一致；README
   保持由用户指定 `X.Y.Z` 的参数化安装方式。校验不得把历史 `v0.0.2` 当作当前产品 release 的证据。
3. `README.md` 与 `README.zh-CN.md` 相互可达，以各自语言清楚说明能力、问题、场景、项目最初的跨仓库知识互联
   愿景、当前可审阅基础、OKF 启发、Python 前提和简洁的 GitHub tag 安装方式；该入口能让 agent 获得同一 tag 的
   Python distribution 与四个 Published Skills，且不把 Codex metadata/command 设为非 Codex agent 的前提。它们不
   退化为开发教程，根 `index.md` 也能到达二者。
4. 在没有本地 checkout、默认分支信息或人工补充 source selector 的环境中，agent 仅凭 README URL 和目标
   `doctidex-git` 版本即可构造并运行 Git URL + matching tag 的 Python package 安装命令；命令使用
   `whero-doctidex`、`--no-input` 和 `#subdirectory=impls/libs/python`。同一 README 还给出 matching tag 的
   repository checkout 与精确 `skills/` 路径，使 agent 可用 host-native 注册或直接读取取得 Published bundle。
5. 四个 Published Skills 保持既有阅读链、前置运行时、command sufficiency 与用户/内部信息边界；不得含协议/产品
   版本、Git tag、package 或运行时安装/重装、开发、发布、tag 确认、测试或维护验证描述。
6. `DOCTIDEX_GIT_CACHE` 作为可选 user configuration 被 Architecture、Python Impls、README 和适用 Skill 一致说明：
   用户手动设置，未设置时使用平台默认值，进程继承决定其生效范围，agent 不持久化该设置；不公开内部 cache layout，
   也不改变 `cache clean` 的 Skill 路由边界。
7. 相关 Architecture、Impls、README、plugin/Skill metadata、Python tests 与版本校验完成后，执行适用的 package
   installation forward test、Published Skill/containing plugin validation、文档可达性检查、Python lint/tests 和
   `git diff --check`；全部授权工作完成前，本记录保持 `draft`。

## 7. 进展与边界

本轮已核对现有版本、Git tag、Python package、Published Skills 和 cache implementation，并将用户评论吸收至上述
设计。用户随后授权实施，并指定 Python 代码与 `doctidex-git` 均为 `1.0.0`；已完成本地 Architecture、Python Impls、
README、根导航、Published Skill 和测试对齐。`DOCTIDEX_GIT_CACHE` 已实现并现已成为 user surface。

用户进一步指定删除 Published Skill 中的产品版本与 package 安装描述（包括各 Skill 第 10--11 行的对应表述），并严禁
在 Skill 正文添加开发相关描述。release identity、版本一致性与发布后安装检查继续由 README、Requirement、Architecture、
Impls 和后置验证负责，不进入 Skill 正文。

用户补充项目最初愿景：不同 Git repository 中的开发知识应能互联；AI 时代应能在新的 repository 中向 agent 提及已有
repository 的知识、最佳实践和设计模式，使其获得可审阅的开发历程、知识积累和设计偏好。中英文 README 已将这一方向
与当前可读 index、渐进导航、fixed revision external snapshot/presentation 的现实能力区分，并说明 Google OKF 是重要
灵感而非严格兼容目标。

用户进一步指出 README 的安装步骤不能只安装 Python 代码；agent 还应获得 Published plugin 及其 Skills，且不能只兼容
Codex。实现据此以同一 tag 通过 VCS 安装 package，并以独立 repository checkout 取得可移植 `SKILL.md` bundle，保留
`.codex-plugin` 作为可选 metadata；agent host 的原生注册机制负责将 bundle 变为可调用 surface，不在 README 虚构通用的
host command。

用户发现根 `index.md` 未预先将 `/.doctidex` 声明为 unsafe。该目录当前不存在，但 `doctidex-git` 会在使用 repository
时在其中保存运行时状态；根索引现将该最小目录范围预先声明为 unsafe，避免生成后的内部状态承担协议的严格内容与 link
要求。当前不链接尚不存在的目录，以避免校验器报告 `link_path_invalid`；`RootStorage.ensure_host_layout()` 在首次物化
目录时负责加入带 `unsafe: true` 注释的可达入口。

本地验证已完成：`.venv/bin/python -m pytest impls/libs/python/tests -q` 通过（66 passed），
`.venv/bin/python -m ruff check impls/libs/python` 通过，`.venv/bin/doctidex-git validate . --scope
/impls/agent-plugins/doctidex-git --json` 返回 `protocol_structure: pass`、零 findings、零 semantic candidates；
plugin metadata JSON 解析和 `git diff --check` 也通过。更新后的 release-surface 测试覆盖协议/package/plugin major
关系、当前 `1.0.0` package/plugin、四个 Skill 的非开发边界、双语 README 参数化命令和 cache override。
本次 README 定位补充后，release-surface 测试的 4 项检查通过，`git diff --check` 通过；全仓 `validate . --json`
返回 `protocol_structure: pass`、零 findings，并保留既有五项 `unsafe_scope_review` semantic candidates。
本次跨 host bundle 安装说明更新后，`.venv/bin/python -m pytest impls/libs/python/tests -q` 再次通过（66 passed），
`.venv/bin/python -m ruff check impls/libs/python` 通过，`.venv/bin/doctidex-git validate . --scope
/docs/doctidex-git --scope /docs/requirements --scope /impls/agent-plugins/doctidex-git --json` 返回
`protocol_structure: pass`、零 findings、零 semantic candidates，`git diff --check` 通过。

根 `index.md` 的 `/.doctidex` unsafe 声明补齐后，全仓 `.venv/bin/doctidex-git validate . --json` 返回
`protocol_structure: pass`、零 findings；六项 `unsafe_scope_review` semantic candidates 分别对应既有五个声明和新增的
最小 `/.doctidex` 运行时状态范围，均已作出范围判断。新增的 release-surface 回归检查通过；
`.venv/bin/python -m pytest impls/libs/python/tests -q` 通过（67 passed），`.venv/bin/python -m ruff check
impls/libs/python` 通过。

2026-08-05 只读核验 GitHub `refs/tags/v1.0.0` 返回不存在，因此无法运行真实 GitHub package installation forward
test，也不能将 `v1.0.0` 表述为已发布 release。用户仍需创建并确认该 tag；agent 不创建或推送 tag。在该外部发布前置
条件满足并完成网络安装验证前，本 Requirement 保持 `draft`。
