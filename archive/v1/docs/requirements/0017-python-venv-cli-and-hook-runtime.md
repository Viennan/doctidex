# 需求 0017：为 Python CLI 与 Git hook 选定 `.venv` 运行环境

| 属性 | 值 |
|---|---|
| ID | `DX-REQ-0017` |
| 状态 | `approved` |
| 日期 | 2026-08-04 |
| 来源 | 用户在确认已发布 Skill 仅调用裸 `doctidex-git`、却没有交付 Python 运行环境后，要求 agent 使用当前 Python 代码包的 `doctidex-git` 前选定一个 `.venv`，并使后续 CLI 命令及 Git hook 固定在该环境中运行；不规定 `.venv` 的选择或创建方式。 |
| 影响范围 | Python Impls 交付说明、三个 Published Skills、Python package/hook realization、对应测试，以及 Requirements 导航。 |
| 协议关系 | Python variant 的运行和交付约定；不改变 [`doctidex` 协议](../../spec/overview.md)的目录结构、元信息、读取关系或符合性要求。 |

## 1. 已确认的问题与意图

当前 Python package 要求 CPython `>=3.11`，并在安装后提供 `doctidex-git` console script。Python Impls
只在开发说明中给出根 `.venv` 的 editable install；已发布插件只包含 manifest 与三个 Skill。Published
Skills 和由 `hook --install` 写入的 `post-checkout` hook 都调用裸 `doctidex-git`，因此依赖调用环境已经把
该 console script 放入 `PATH`。

实际检查表明，仓库 shell 中裸 `doctidex-git` 不可用，而
`.venv/bin/doctidex-git --help` 可以运行。当前测试也大多以 `sys.executable -m` 启动模块；hook 测试另行把
解释器目录加入 `PATH`。这些证据不能证明新安装的 agent 或随后的 Git hook 能找到 console script。

本 Requirement 为当前 Python variant 建立显式的运行前提：agent 在首次使用 `doctidex-git` 前，选定一个
已安装当前代码包的兼容 `.venv`。该任务内所有 agent 主动调用的 CLI 都使用该环境的 console script；
`hook --install` 则将同一 executable 绑定到后续的 Git hook。agent 不能假设全局 `PATH` 已有
`doctidex-git`，也不应通过 `command not found`、`--help` 或私有 import 试探运行方式。

## 2. 目标运行契约

1. agent 在需要 `doctidex-git` 前选定一个使用兼容 CPython、且已安装当前 Python 代码包的 `.venv`。本
   Requirement 不规定该环境位于何处、如何选择、如何创建、以何种安装命令安装代码包，或是否修改 shell
   `PATH`；涉及网络或本地环境变更时仍须遵守当前用户授权。
2. 在同一任务中，agent 通过选定 `.venv` 中的 `doctidex-git` console script 调用所有 CLI command，
   包括 `validate`、`external`、`worktree`、`hook --install` 与显式 `hook --run`。该约定不依赖全局
   `doctidex-git`、shell activation 或之后变化的 `PATH`。
3. `hook --install` 写入的 `post-checkout` hook 必须使用安装时已选 `.venv` 的 exact executable，而不是
   裸 `doctidex-git`。因此 Git 在没有该 `.venv` 加入 `PATH` 的环境中执行 checkout 时，仍能在已选环境中
   运行 `hook --run`；已失去该 runtime 的 hook 必须以可诊断的失败保留现状，不能静默改用另一个全局版本。
4. Runtime selection 是当前 Python variant 的必要前提，而不是 doctidex protocol 规则；它不得改变 CLI
   command、JSON contract、doctidex root 选择或 external/worktree 生命周期语义。

## 3. 设计与实施影响

本 Requirement 不修改 Architecture。选定 runtime 是当前 Python variant 的实现前提，不要求 Published
Skills 引入 repository-local path、开发命令或安装教程。Python Impls 记录这一 variant 的 package/runtime
事实；Overview 负责共同 prerequisite 与所有命令的公共 invocation，Read 与 Maintenance 仅继承该约定，
不复制运行环境说明。

Published Skills 应使 agent 在需要 CLI 前确认已选 `.venv`，并在没有已选环境、兼容 Python、已安装代码包或
executable 时停止并报告，而不是错误试探。如何选择、创建或安装该 `.venv` 不属于 Published Skill 的内容。

Python implementation 必须调整 `post-checkout` hook 的生成方式，使其绑定已安装 runtime 的 executable。
测试须覆盖 console script 的真实入口、未向 `PATH` 注入 `.venv` 的 shell，以及由 Git 实际触发的 hook。
实现不得把 `.venv`、site-packages 或运行时 cache 交由 Git 跟踪，也不得把该运行约定泛化为其他 variant
或发布包安装机制。

## 4. 验收标准

1. Python Impls 与 Published Skills 对“使用前选定已安装代码包的兼容 `.venv`”、该环境的 CLI executable
   和授权边界给出一致且中文可读的当前说明；本项不修改 Architecture。
2. 在全局 `doctidex-git` 不可用的环境中，agent 选定一个符合前提的 `.venv` 后，能以其中的 executable
   成功运行一个无副作用 CLI command，无需以失败命令发现路径。
3. 所有 Published Skill 所示 CLI command 都采用或明确继承同一 runtime invocation；`hook --install` 与
   agent 主动执行的 `hook --run` 也不例外。
4. 安装后的 `post-checkout` hook 在其执行环境不含已选 `.venv` 的 `PATH` 时仍能调用安装它的 Python
   runtime；测试验证实际 Git checkout 的结果，而不是仅检查生成字符串。
5. Published Skills 不规定 `.venv` 的位置、选择过程、创建过程、安装命令或 shell activation；它们只要求
   agent 选定满足前提的环境并始终使用其 executable。
6. package/runtime 缺失、Python 版本不兼容、安装失败或 runtime 已被移除时，agent 与 hook 的失败信息不会
   伪装成 doctidex protocol finding，也不会切换到未知全局 `doctidex-git` 版本。
7. 不修改 `spec/overview.md`、Architecture、CLI/JSON 语义或既有 external/worktree 生命周期；Python lint、tests、
   相关 doctidex validation、Published Skill/containing plugin validation，以及适用的独立 workflow forward
   test 均通过后，才可将本记录置为 `implemented`。

## 5. 进展与依赖

用户已明确批准当前实现可进入 PR/MR，本记录现为 `approved`。Architecture 与协议均未修改。

Published Overview 现在要求 agent 在首次 CLI 调用前选定一个含当前 package 的兼容 `.venv`，并把
`DOCTIDEX_GIT` 定义为该环境的 exact console script；Read、Maintenance 及其 command references 均继承或
使用这一记号。文本明确不规定 `.venv` 的位置、选择、创建、安装或 shell activation。

Python `HookService.install()` 现在从当前 Python runtime 的词法 executable 目录选择 `doctidex-git` console
script，写入 absolute launcher。重装会保留相同 launcher 为 unchanged，并将旧的受管 bare-command launcher
升级到当前 runtime；foreign hook 仍受保护。由 Git 触发时，launcher 不依赖 `PATH`，但 runtime 被移除后不会
回退到全局 `doctidex-git`。

验证完成：`git diff --check`、`.venv/bin/python -m ruff check impls/libs/python` 与
`.venv/bin/python -m pytest impls/libs/python/tests -q` 通过（45 passed）。测试现在通过已安装 console script
调用 CLI，并验证实际 `git checkout` 在移除 selected runtime 目录后的 `PATH` 中仍完成 hook reconciliation，
同时覆盖旧受管 launcher 的升级和 foreign hook 保留。`.venv/bin/doctidex-git validate` 对
`/docs/doctidex-git/impls/python`、`/impls/agent-plugins/doctidex-git` 与 `/docs/requirements` 的 scoped coverage
返回 `protocol_structure: pass`、`scan_complete: true` 与零 findings；plugin `plugin.json` 亦已由 JSON parser
读取。当前 active Skill catalog 未提供该本地插件的额外 Published-Skill validator；此次没有改变既有 CLI
workflow，故上述实际 Git fixture 测试作为适用的 forward evidence。

它以后续方式依赖已批准的 [DX-REQ-0014](0014-doctidex-git-checkout-hook.md)（现有 hook lifecycle）、
[DX-REQ-0015](0015-architecture-and-impls-document-principles.md)（当前文档分层）和
[DX-REQ-0016](0016-doctidex-git-hook-run-skill-guidance.md)（公开 `hook --run` 引导）。这些历史记录均为
`approved`，尚未取得修改其内容以添加 reciprocal link 的授权；本记录暂保留单向关系。
