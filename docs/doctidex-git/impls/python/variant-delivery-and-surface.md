# Python 变体交付与用户界面

本页负责 Python package/platform/deployment 的事实，以及它如何装配共同 CLI、JSON subprocess 和 Published Skills。共同 command semantics、configuration/artifact 含义、failure/recovery 和 handoff 仍由 [Architecture](../../architecture/index.md) 定义。

<a id="1-package-runtime-and-dependencies"></a>
## 1. 软件包、运行时与依赖

Python distribution 位于 [`impls/libs/python`](../../../../impls/libs/python/)，其 package metadata、console entry 和 dependency constraints 由 [`pyproject.toml`](../../../../impls/libs/python/pyproject.toml)说明。当前开发环境使用 repository root `.venv`：

```text
.venv/bin/python -m pip install -e impls/libs/python
```

| 选择 | Python 实现 | 用户影响 |
|---|---|---|
| 运行时 | CPython `>=3.11`。 | 缺少兼容 Python 时 console script 不可用；不通过 private import 规避。 |
| Git | subprocess argument array，`GIT_TERMINAL_PROMPT=0`。 | credential 交给 Git helper；CLI 不开启 interactive prompt。 |
| Markdown/YAML | `markdown-it-py` 与 `ruamel.yaml` round-trip。 | protocol observation 不依赖 ad-hoc string parsing；具体 AST/emitter 不属于 public contract。 |
| 路径 | `pathlib` 和 Git 输出的 absolute path。 | Linux/macOS/Windows 共用逻辑；doctidex root-absolute 与 filesystem absolute 明确分离。 |
| Symlink | native relative directory symlink。 | capability 缺失时 `external link` 被 blocked；不提供 copy/junction fallback。 |
| 插件交付 | `impls/agent-plugins/doctidex-git/` 的 manifest 与三项 Skills。 | installed user surface 只读取其内容，不读取 repository Impls 文档。 |

<a id="2-human-agent-and-program-integration"></a>
## 2. 人、agent 与程序的集成

Human 使用 console script；涉及 automation、精确审阅或 bug report 时选择 `--json`。Python 只提供 subprocess boundary，不承诺 service/dataclass import。Program 必须验证 `schema_version`、`status`、`operation`、collection/cursor 与 stable codes，不能解析私有 `runtime.json`、cache 或 human message。

Overview、Read、Maintenance Skills 与 console script 必须作为同一 product release 对齐。Overview 对已安装 hook 只作自动行为提示；没有要求 agent 主动 install/diagnose hook。`cache clean` 是 human/program operator surface，因此三项 Published Skills 不路由它。相关 audience/reading-chain constraint 见[Skill system](../../architecture/skill-system.md)。

Python 变体的 package entry/argument parsing/result rendering 见[CLI/结果 component](components/cli-results-and-rendering.md)；实际工作现场效果见[清单](worksite-inventory-and-construction.md)。

<a id="3-variant-specific-operating-boundary"></a>
## 3. 变体特有的运行边界

- logical read-only 是 payload access policy，不是 OS sandbox；
- remote failure 的分类依赖 Git 可观察 output，credential 不进入 JSON/public file；
- platform 不能创建 symlink 时，会在发生 persistent link/index/manifest change 前 blocked；
- unexpected error 会尝试在 user cache 写入 opaque diagnostic，正常 user action 只报告 diagnostic ID；
- cache path、hash、lock name、JSON key order、filesystem mode 和 subprocess command 属于内部实现事实；即使 maintainer 可由 Impls/source 检查，它们也不是 installed program contract。

Python 变体实际的私有机制、已知 evidence gap 和 tests 见[发布/恢复](publication-recovery-and-private-mechanics.md)与[覆盖/证据](architecture-coverage-evidence-and-worksite-validation.md)。
