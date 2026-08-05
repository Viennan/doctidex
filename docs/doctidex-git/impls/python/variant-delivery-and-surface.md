# Python 变体交付与用户界面

本页负责 Python package/platform/deployment 的事实，以及它如何装配共同 CLI、JSON subprocess 和 Published Skills。共同 command semantics、configuration/artifact 含义、failure/recovery 和 handoff 仍由 [Architecture](../../architecture/index.md) 定义。

<a id="1-package-runtime-and-dependencies"></a>
## 1. 软件包、运行时与依赖

Python distribution 位于 [`impls/libs/python`](../../../../impls/libs/python/)，其 package metadata、console entry 和 dependency constraints 由 [`pyproject.toml`](../../../../impls/libs/python/pyproject.toml)说明。当前 package 为 `whero-doctidex==1.0.0`，对应 `doctidex-git` `1.0.0`；用户创建并确认 `v1.0.0` Git tag 后，可通过该 tag 安装。该 tag 的 repository checkout 还提供 Published agent bundle；其中 `skills/` 是跨 host 的工作流内容，`.codex-plugin` 是 Codex 可选 metadata。agent 在使用本 variant 的 CLI 前，选定一个已安装该 distribution 的兼容 `.venv`；本页不规定该环境的位置、选择过程或创建过程。

| 选择 | Python 实现 | 用户影响 |
|---|---|---|
| 运行时 | CPython `>=3.11`。 | 缺少兼容 Python 时 console script 不可用；不通过 private import 规避。 |
| Git release 安装 | `python -m pip install --no-input "whero-doctidex @ git+https://github.com/Viennan/doctidex.git@v1.0.0#subdirectory=impls/libs/python"`。 | 当前 release 固定 source revision；README 的安装者输入 target version 后使用相同格式替换 tag，不选择 default branch。 |
| Published agent bundle | 同一 Git tag checkout 的 `impls/agent-plugins/doctidex-git/skills/`。 | agent host 用自身的 plugin/skill 机制导入该目录，或直接读取选定 `SKILL.md`；`.codex-plugin` 与 `agents/openai.yaml` 为 Codex 可选 metadata，不是其他 host 的前提。 |
| CLI runtime | 每个 agent task 选定一个含当前 package 的 `.venv`，并使用其中的 console script。 | 不依赖全局 `PATH`、shell activation 或另一个 Python environment；没有满足条件的 executable 时停止并报告。 |
| Git | subprocess argument array，`GIT_TERMINAL_PROMPT=0`。 | credential 交给 Git helper；CLI 不开启 interactive prompt。 |
| Markdown/YAML | `markdown-it-py` 与 `ruamel.yaml` round-trip。 | protocol observation 不依赖 ad-hoc string parsing；具体 AST/emitter 不属于 public contract。 |
| 路径 | `pathlib` 和 Git 输出的 absolute path。 | Linux/macOS/Windows 共用逻辑；doctidex root-absolute 与 filesystem absolute 明确分离。 |
| Symlink | native relative directory symlink。 | capability 缺失时 `external link` 被 blocked；不提供 copy/junction fallback。 |
| 插件交付 | `impls/agent-plugins/doctidex-git/` 的可移植四项 Skills 与 Codex 可选 manifest。 | installed user surface 只读取 bundle 内容，不读取 repository Impls 文档；不支持 plugin 注册的 host 仍可直接读取对应 `SKILL.md`。 |

<a id="2-human-agent-and-program-integration"></a>
## 2. 人、agent 与程序的集成

Human 使用其选定 runtime 的 console script；涉及 automation、精确审阅或 bug report 时选择 `--json`。agent 由 Published Overview 先选定 `.venv`，并在该 task 的全部 CLI command 中使用同一 executable；它不在 Published Skill 中获得环境选择、创建或完整安装教程。对 selected owner root 的 doctidex managed install，agent 以 `external list` 的 repository path/host/revision/role query 取得可读候选，再在唯一或经用户确认后将返回的 opaque ID 交给精确 command；不通过 private `runtime.json` 发现 repository。`hook --install` 将该 runtime 的 executable 写入 host hook，之后 Git checkout 不依赖 shell `PATH`。Python 只提供 subprocess boundary，不承诺 service/dataclass import。Program 必须验证 `schema_version`、`status`、`operation`、collection/cursor 与 stable codes，不能解析私有 `runtime.json`、cache 或 human message。

用户可在启动 CLI、automation 或 host Git process 前手动设置非空 `DOCTIDEX_GIT_CACHE`，以选择 shared user-cache root；该值由
[`cache_root()`](../../../../impls/libs/python/whero/doctidex/git/storage.py)在每个进程中读取。未设置时，Python 在 Linux 和其他
Unix 使用 `XDG_CACHE_HOME` 或 `~/.cache/doctidex-git`，macOS 使用 `~/Library/Caches/doctidex-git`，Windows 使用
`LOCALAPPDATA/doctidex-git`。为避免 cwd 影响，文档建议用户提供 absolute path。agent 可以说明该选择，但不写 profile、
project configuration 或任何 persistent environment setting；需要共享 cache 的 hook 也由用户确保继承同一值。

Overview、Mentions、Read、Maintenance Skills 与 console script 必须作为同一 product release 对齐。README 以同一 tag
安装 Python distribution，并 checkout repository 取得其中的 `skills/` bundle；host 再以自己的机制注册或直接读取它。Overview
对已安装 hook 只作自动行为提示；没有要求 agent 主动 install/diagnose hook。`cache clean` 是 human/program operator surface，
因此四项 Published Skills 不路由它。相关 audience/reading-chain constraint 见[Skill system](../../architecture/skill-system.md)。

Python 变体的 package entry/argument parsing/result rendering 见[CLI/结果 component](components/cli-results-and-rendering.md)；实际工作现场效果见[清单](worksite-inventory-and-construction.md)。

<a id="3-variant-specific-operating-boundary"></a>
## 3. 变体特有的运行边界

- logical read-only 是 payload access policy，不是 OS sandbox；
- remote failure 的分类依赖 Git 可观察 output，credential 不进入 JSON/public file；
- platform 不能创建 symlink 时，会在发生 persistent link/index/manifest change 前 blocked；
- unexpected error 会尝试在 user cache 写入 opaque diagnostic，正常 user action 只报告 diagnostic ID；
- `DOCTIDEX_GIT_CACHE` 的用户选择和未设置时的平台 fallback 是 user contract；cache 内部 path、hash、lock name、JSON key order、filesystem mode 和 subprocess command 仍属于内部实现事实，即使 maintainer 可由 Impls/source 检查，它们也不是 installed program contract。

Python 变体实际的私有机制、已知 evidence gap 和 tests 见[发布/恢复](publication-recovery-and-private-mechanics.md)与[覆盖/证据](architecture-coverage-evidence-and-worksite-validation.md)。
