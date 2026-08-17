# doctidex

[English](README.md)

doctidex 是一种目录树结构标准，并提供面向 Git 的实现，用于读取、校验和维护 doctidex 内容。
它保持普通文件与 Markdown 的可读性，同时为人类、agent 和程序提供稳定导航与可观察结构。

## 起源与方向

doctidex 最初要解决的是跨 repository 的知识互联问题：开发者的知识常常散落在多个 Git repository 中，
但这些 repository 共同承载着一段连续的经验。项目的长期方向是让这些知识形成可互联、可追溯的网络，而不是让每个
repository 孤立存在。

这在 AI 辅助开发中尤为重要。工作进入新的 repository 时，agent 需要以可审阅的方式跟随对既有 repository 的提及，
理解当前工作相关的知识、最佳实践、设计模式和设计偏好。维护了明确导航和上下文的 Git repository 因而可以成为
自解释的知识库。

目前，doctidex 为这一方向提供可审阅的基础：在目录树中提供可读 index 和渐进导航，并以固定 revision 的 external
snapshot 与 presentation 连接 Git 内容。它不会自动发现、汇总或注入所有 repository 的知识；人和 agent 仍自行决定
记录和跟随哪些上下文。

## 设计灵感

本项目深受 Google 的 [Open Knowledge Format（OKF）](spec/refs/okf-v0.1.md) 启发，特别是其以普通目录、Markdown
和少量结构约定承载可供人类和 agent 读取的知识。doctidex 将这些思想延伸到自身面向 Git 的使用场景，但不声明严格的
OKF 格式兼容性。

## 提供的能力

- 用少量规则定义索引、链接、局部配置和可达性。
- 通过 `doctidex-git` 支持协议校验、固定 commit 的 external 内容、presentation、checkout 协调和可选隔离 worktree。
- 同时提供人类可读输出与有版本的 JSON 结果，供 agent 和程序集成。

## 适用场景

当 repository 需要可导航的知识或文档树，或 agent 需要维护 external Git snapshot 且不能隐藏周围普通文件时，
可以使用 doctidex。原生 Git、filesystem、搜索、Markdown 与交付流程仍可继续使用。

## 安装 `doctidex-git` 与 agent bundle

Python distribution 要求 CPython `>=3.11`。安装前由用户指定 target `doctidex-git` 版本，并将
`TARGET_DOCTIDEX_GIT_VERSION` 替换为该版本；对应的 repository tag 使用 `v` 前缀。

```text
python -m pip install --no-input \
  "whero-doctidex @ git+https://github.com/Viennan/doctidex.git@v<TARGET_DOCTIDEX_GIT_VERSION>#subdirectory=impls/libs/python"
```

### 取得 Published Skills

Python distribution 提供 `doctidex-git` console script。Published agent bundle 通过同一 tag 的独立 checkout
取得，因此代码与 Skills 始终来自用户选择的同一个 release：

```text
git clone --depth 1 --branch v<TARGET_DOCTIDEX_GIT_VERSION> \
  https://github.com/Viennan/doctidex.git doctidex-agent-bundle
```

使用 agent host 自身的 plugin 或 Skill 注册机制导入下列目录：

```text
doctidex-agent-bundle/impls/agent-plugins/doctidex-git/skills/
```

bundle 的可移植内容是四个 `SKILL.md` 工作流。没有 plugin 或 Skill 注册机制的 host 可以直接将与任务相关的
`SKILL.md` 提供给 agent，并从 `doctidex-git-overview` 开始。bundle 还含有供 Codex 使用的 `.codex-plugin` metadata，
但该 metadata 和任何 Codex 专有 command 都是可选的，不是其他 agent host 的前提。

安装后，在选定环境中确认 console script 可用：

```text
doctidex-git --help
```

### 选择 shared cache 位置

可选的 `DOCTIDEX_GIT_CACHE` 环境变量允许用户选择 absolute、可写的 shared cache 路径。需要共享 cache 的 CLI、
automation 或 host Git process 都应继承相同配置。该环境选择由用户负责；agent 不会为此写入 shell profile 或
project setting。

```text
export DOCTIDEX_GIT_CACHE=/absolute/path/to/doctidex-cache
```

未设置时，已安装的 variant 使用其平台默认 cache 位置。

## 继续阅读

从[仓库导航](index.md)开始，可以找到 protocol、设计文档、实现和已安装 agent surface。项目推荐在 agent 协助下
探索和开发。
