# doctidex-git 0.1.0 Git Context、命令与 State

本篇说明 `git/context.py`、`git/runner.py` 和 `git/state.py` 如何为上层服务提供 Git
现场、持久状态、并发和诊断能力。它们支撑 Architecture 的
[命令上下文与失败模型](../../architecture/constraints-and-failures.md)，但不是公共 API。

## 1. 模块边界

| 模块 | 职责 | 不负责 |
|---|---|---|
| `git.runner` | 非交互执行 Git，保留 stdout/stderr/退出码，分类预期 Git 失败。 | 选择 doctidex 根、解析协议或决定业务重试。 |
| `git.context` | 查找 Git worktree、解析 porcelain status、检查和补充根 ignore。 | source 获取、mount 生命周期或内容语义。 |
| `git.state` | 计算内部路径、序列化宿主状态、加锁、反查维护根、写异常诊断。 | 成为用户配置或稳定程序接口。 |

上游调用者是 `git.setup`、`git.mounts`、`git.maintenance`、`git.repository`、
`git.projection` 和 `cli.main`。三者只依赖标准库，`context` 通过 `runner` 调用 Git。

## 2. `git.runner`

### 2.1 `GitResult`

| 属性 | 类型 | 含义 |
|---|---|---|
| `stdout` | `str` | Git 标准输出，保留尾随换行。 |
| `stderr` | `str` | Git 标准错误，保留原始文本。 |
| `returncode` | `int` | 子进程退出码。 |

### 2.2 `git(arguments, cwd=None, operation="git", check=True)`

- `arguments` 是不含可执行文件名的参数序列；不通过 shell。
- `cwd` 只设置子进程目录；多数调用仍显式使用 `-C` 或 `--git-dir`。
- `operation` 进入错误结果，必须使用上层公开 operation 名。
- `check=False` 让调用者自行解释非零退出码；默认由 `_git_error` 转成
  `DoctidexError`。
- 环境继承调用进程；未显式设置时补 `GIT_TERMINAL_PROMPT=0`，避免 agent 进程挂起。

错误分类根据 Git 英文输出区分认证、网络、revision 和通用失败。它会丢弃原始 stderr
的公开展示，仅保留用户层 message/actions；本地化输出可能落入 `git_failed`，见
[当前限制](known-limitations.md)。

```python
from pathlib import Path
from whero.doctidex.git.runner import git

result = git(
    ["-C", str(Path("/workspace/source")), "rev-parse", "HEAD"],
    operation="maintenance_scope",
    check=False,
)
head = result.stdout.strip() if result.returncode == 0 else None
```

## 3. `git.context`

### 3.1 函数

| 函数 | 输入与返回 | 副作用和错误 |
|---|---|---|
| `git_worktree(path)` | 返回 `git rev-parse --show-toplevel` 的 `Path`，非 Git 目录返回 `None`。 | 只读；Git 命令本身异常归为不可识别现场。 |
| `git_status(path)` | 返回 porcelain v1 `-z` 条目；每项有 `status/path`，rename/copy 有 `original_path`。 | 只读；Git 失败抛 `DoctidexError`。 |
| `root_gitignore_status(root)` | 返回 `status/ignored/tracked`，在 Git 中还含 `ignore_file`。 | 只读；执行 `check-ignore` 和 `ls-files`。 |
| `ensure_root_gitignore(root)` | 缺少精确规则时追加，发生写入返回 `True`。 | 写根 `.gitignore`；不修改 Git index。 |

`root_gitignore_status` 要求 ignore 来源恰好是 doctidex 根自己的 `.gitignore`，并检查
namespace 下没有 tracked path。父级或全局 ignore 不能令插件 readiness 成为 ready。

`git_status` 按 porcelain 的双字符状态原样保留；调用者不能把 `status[0]` 与
`status[1]` 合成一个抽象状态。rename/copy 的 `-z` 第二路径写入 `original_path`。

## 4. `git.state`

### 4.1 路径与 identity

`state_home()` 优先使用 `WHERO_DOCTIDEX_STATE_DIR`，否则使用 `XDG_CACHE_HOME`，再否则
为 `~/.cache/whero-doctidex`。`stable_key(value)` 是 UTF-8 文本的十六进制 SHA-256；
`source_directory(url)` 以原始 URL 文本计算 source 目录。因此语义等价但文本不同的
URL 当前不共享数据。

完整物理布局和 state schema 见 [Git Runtime](git-runtime.md)。这些路径只供实现与
测试使用，不得出现在 Skill 的正常使用前置中。

### 4.2 `StateStore`

| 属性 | 含义 |
|---|---|
| `root` | `absolute()` 后的宿主 doctidex 根；不解析 symlink。 |
| `directory` | `roots/<stable-key(root)>`。 |
| `path` | `<directory>/state.json`。 |
| `lock_path` | `<directory>/state.lock`。 |

| 方法 | 契约 |
|---|---|
| `read()` | 在 state lock 内返回 mapping；文件缺失、非法 JSON 或非 object 时退回空 v1 state。 |
| `update(callback)` | 锁内读取，补顶层 `root`，让 callback 原地修改，再原子写回并返回结果。 |
| `locked()` | 暴露同一 store 的互斥上下文，供需要组合多个操作的调用者使用。 |
| `_read_unlocked()` | 只允许已持锁调用；补 `version/mounts/maintenance` 默认值。 |
| `_write_unlocked(data)` | 同目录临时文件、flush、fsync、`os.replace` 发布，finally 清理临时文件。 |

callback 在持锁期间执行，不应包含网络、用户等待或再获取同一 state lock 的操作。

```python
from pathlib import Path
from whero.doctidex.git.state import StateStore

store = StateStore(Path("/workspace/docs"))

def remember(data: dict) -> None:
    data["mounts"]["/.doctidex/mounts/api"] = {"effective_commit": "a" * 40}

store.update(remember)
```

### 4.3 锁、反查与诊断

`file_lock(path)` 创建父目录和 lock file，用阻塞式 `fcntl.flock(LOCK_EX)` 串行化临界
区；无超时，因此当前实现要求 POSIX。锁层级及非原子边界见
[Git Runtime](git-runtime.md#10-锁与非原子边界)。

`maintenance_host(maintenance_root)` 扫描各宿主 state 的 maintenance records，按绝对
路径匹配并返回 `host_root`；损坏记录被跳过。这让 CLI 可以从任意 cwd 继续显式维护根。

`write_diagnostic(error)` 把完整 traceback 写到 `diagnostics/<12-char-id>.log` 并返回
ID。日志可能含内部路径，只供维护者排障；CLI 只公开 ID。

## 5. 失败与并发边界

- Git 子进程无 shell 注入面，但仍继承调用进程的凭据和 Git 配置。
- state 文件发布原子，不代表“文件系统呈现 + state”是跨资源事务。
- 损坏 state 当前静默视为空状态，可能留下未登记资源。
- `maintenance_host` 是线性扫描，不能作为高频公共查询接口。
- 锁无超时；进程崩溃后 OS 会释放 flock，但临时或未登记资源需另行处理。
