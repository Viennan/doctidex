# 总体架构

本篇说明 `doctidex-git` 当前代码如何分层、一次命令如何流经各层，以及哪些信息是
CLI 的公开结果、哪些只属于内部实现。

## 1. 分发与目录

Python distribution 名为 `whero-doctidex`，版本为 `0.1.0`，要求 Python 3.11 以上。
`whero` 使用 PEP 420 namespace package，因此源码中没有 `whero/__init__.py`。公共
import 根为 `whero.doctidex`，console script 为 `doctidex-git`。

```text
impls/
├── agent-plugins/doctidex-git/
│   ├── .codex-plugin/plugin.json
│   └── skills/                     # agent 可见工作流
├── libs/python/
│   ├── pyproject.toml
│   ├── whero/doctidex/
│   │   ├── protocol/               # 不依赖 Git 的解析与目录树判断
│   │   ├── git/                    # Git source、mount、projection、维护上下文
│   │   ├── cli/                    # 参数、命令编排、预算和渲染
│   │   └── errors.py               # 统一的可行动错误模型
│   └── tests/
└── docs/
    ├── agent-git-plugin.md         # agent surface 设计
    └── doctidex-git/               # 当前实现说明
```

依赖方向为 `cli -> git -> protocol`。`protocol` 不 import `git`；Git 实现可以复用协议
对象；CLI 只负责编排，不拥有第二套解析规则。

## 2. 一次 CLI 调用的控制流

```text
argv
  -> 提取全局 --json/--limit/--depth/--cursor
  -> argparse 解析命令
  -> 发现或要求一个 doctidex 根
  -> 调用 protocol 函数或 Git service
  -> 得到 Python dict/list 结果
  -> 对所有列表应用输出预算
  -> JSON 或人读渲染
  -> 根据 blocked/protocol_structure 选择退出码
```

`DoctidexError` 在主入口统一转为 `status: blocked` 的结果。未预期异常会写入内部诊断
文件，并只返回 `diagnostic_id`。参数解析发生在统一异常处理之前，因此 argparse
错误保持 argparse 自身的 stderr 和退出码；详见 [CLI 命令参考](cli-commands.md)。

## 3. 模块职责

### 3.1 顶层

| 模块 | 代码职责 |
|---|---|
| `whero.doctidex.__init__` | 暴露当前包版本 `0.1.0`。 |
| `errors.py` | 定义 `DoctidexError`，把失败原因、受影响对象、保留结果、动作和用户输入要求组合成统一结果。 |

### 3.2 `protocol`

| 模块 | 代码职责 |
|---|---|
| `constants.py` | 定义 `/.doctidex/mounts`、`.doctidex/mounts`、`index.md`、`log.md` 常量。 |
| `document.py` | UTF-8 Markdown/frontmatter 读取、round-trip YAML、CommonMark link 提取和原子写回。 |
| `paths.py` | 绝对内部路径规范化、mount namespace 折叠、内部路径与文件系统路径转换、mount 匹配。 |
| `mounts.py` | 读取基础 mount 字段，检查根级声明、字段类型和路径重叠。它不解释 Git revision。 |
| `regex.py` | 固定 `regex.VERSION1 | regex.UNICODE` 编译与 search。 |
| `tree.py` | 根发现、路径上下文、过滤匹配、负责索引和适用 log、受预算遍历所需的目录剪枝。 |
| `validation.py` | 汇总协议结构 findings、语义候选和 mount 数量。 |

### 3.3 `git`

| 模块 | 代码职责 |
|---|---|
| `runner.py` | 非交互执行 Git，把凭据、网络、revision 和其他 Git 失败转换为 `DoctidexError`。 |
| `context.py` | Git worktree 根发现、porcelain status 解析、根 `.gitignore`/tracked 状态检查和 ignore 写入。 |
| `state.py` | XDG cache 路径、稳定 hash、POSIX 文件锁、原子 JSON 状态和异常诊断文件。 |
| `repository.py` | 每个 source URL 的 bare repository、selector 解析、按 commit 复用的只读 revision view、可写 maintenance worktree。 |
| `projection.py` | 构建宿主相关只读 projection，并在逻辑 mount path 上呈现。 |
| `mounts.py` | Git mount 扩展校验以及 list/add/remove/prepare/sync 服务。 |
| `maintenance.py` | 多根 scope、独立维护根 open/status/handoff/close。 |
| `setup.py` | Git 目录中的 doctidex root dry-run 与最小初始化。 |

### 3.4 `cli`

| 模块 | 代码职责 |
|---|---|
| `main.py` | 参数模型、根选择、命令 dispatch、批量 mount、online check、输出预算、退出码和异常边界。 |
| `render.py` | JSON pretty print 与有序的人读 key/value 输出。 |

## 4. 主要数据对象

| 对象 | 所在模块 | 用途 |
|---|---|---|
| `DoctidexError` | `errors.py` | 可恢复或需用户决定的操作失败；既是异常，也是结果 schema 来源。 |
| `RegexCompileError` | `protocol.regex` | 保存 regex 编译消息和可选字符位置，再由 validation 转为 finding。 |
| `MarkdownLink` | `protocol.document` | `label`、`target`、文档内零基 `order`。 |
| `DoctidexDocument` | `protocol.document` | 文件路径、YAML mapping、正文和换行风格。 |
| `MountDeclaration` | `protocol.mounts` | 基础 `type/url/mount_path` 与可 round-trip 的原始 mapping。 |
| `RootContext` | `protocol.tree` | 已选择根路径和已解析根索引。 |
| `PathContext` | `protocol.tree` | 某个路径相对于宿主根的来源、范围、属性和负责文档。 |
| `RevisionSelector` | `git.repository` | `kind` 为 commit/tag/branch，`value` 为用户声明值。 |
| `GitResult` | `git.runner` | 一次 Git 子进程的 `stdout`、`stderr` 和整数 `returncode`。 |
| `GitMount` | `git.mounts` | 基础 mount 声明与 Git selector 的组合。 |
| `StateStore` | `git.state` | 单个宿主根的 mount/maintenance 状态。 |
| `GitMountService` | `git.mounts` | 对一个 `RootContext` 执行 mount 生命周期操作。 |
| `MaintenanceService` | `git.maintenance` | 对一个宿主根规划和管理独立可写源根。 |

这些 dataclass 不是稳定的公共 Python API。稳定程度更高的使用面是 CLI 字段；所有
字段见 [CLI 输出字段参考](cli-output.md)。

## 5. Mount 数据流

### 5.1 Add

`mount add` 校验路径、URL、selector 和根 Git 就绪状态。dry-run 只返回计划；apply
使用 round-trip YAML 把 Git mount mapping 追加到根 `index.md`。此时不 clone、不
解析 revision，也不创建 mount path。

### 5.2 Prepare

```text
根 index 声明
  -> 根 .gitignore/tracked 检查
  -> 读取与声明相匹配的 effective commit
  -> 缺失时确保 bare repository 并解析 selector
  -> 创建或复用 commit revision view
  -> 确认 revision view 根 index.md 是 doctidex root
  -> 构建 host-specific projection
  -> 在逻辑 mount path 呈现
  -> 原子保存 effective commit
```

状态只有在声明的 URL 和 selector 都与 state record 相同时才复用。声明变更会令旧
记录失配，但不会立即删除旧 object、view 或 projection。

### 5.3 Sync

sync 首先刷新并解析 selector。dry-run 也可能访问网络和更新内部 bare repository 的
refs，但不会切换宿主 presentation 或保存新 effective commit。apply 在新旧 commit
不同且 Git 就绪时构建新 projection、替换当前 mount presentation，再保存新 commit。

## 6. Maintenance 数据流

`maintenance open` 要求 mount 已有有效 commit。它从同一 bare repository 创建新的
detached worktree，不复用只读 revision view。maintenance record 写入宿主根的
state store，返回路径是本次任务允许写入的 `maintenance_root`。

`status` 读取 Git porcelain 状态；`handoff` 加载维护根自己的 `index.md`、执行协议
校验并加入 Git change 语义候选；`close` 只移除 Git 状态完全 clean 的 worktree。

## 7. 写入和并发边界

- 文档写回使用同目录临时文件、`fsync` 和 `os.replace`，并保留原文件 mode。
- state 写回使用 state lock、临时文件、`fsync` 和 `os.replace`。
- 同一 source 的 clone/fetch/worktree 操作用 `source.lock` 串行化。
- 同一宿主根的 mount 变更用 `mount-operation.lock` 串行化。
- 同一 projection key 的构建单独加锁并通过 rename 发布。
- 多 mount 批量操作和多根维护不是事务；已成功的结果会保留。

当前锁实现依赖 `fcntl.flock`，所以代码实际上要求 POSIX 环境。文件 mode 的“只读”
是防误写机制，不是针对同一 OS 用户的安全隔离。

## 8. 公开信息与内部信息

CLI 公开根、逻辑路径、清理后的 source URL、声明 revision、有效 commit、可读状态、
维护根和下一步。以下内容只属于实现维护：state hash、bare repository 路径、revision
view 路径、projection key、锁文件、诊断日志和具体 presentation 技术。

内部文档会解释这些对象，是为了维护代码；agent 正常决策不应依赖它们。唯一需要
向用户转交的内部排障标识是未预期失败时返回的 `diagnostic_id`。
